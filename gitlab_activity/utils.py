"""Utility functions for gitlab-activity"""
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import click
import dateutil.parser
import jsonschema
import pytz
import requests
import toml
from importlib_resources import files

PYPROJECT = Path('pyproject.toml')
GITLAB_ACTIVITY = Path('.gitlab-activity.toml')
PACKAGE_JSON = Path('package.json')

SCHEMA = files('gitlab_activity').joinpath('schema.json').read_text()
SCHEMA = json.loads(SCHEMA)


class CustomParamType(click.ParamType):
    """Custom Parameter Type used in click for casting labels_metadata and bot_users"""

    name = "config_data"

    def convert(self, value, param, ctx):
        try:
            if isinstance(value, (dict, list)):
                return value

            # First convert to list
            return json.loads(value.replace("'", '"'))
        except json.decoder.JSONDecodeError:
            self.fail(
                'Failed to cast into list using json.loads for'
                f'{value!r} of type {type(value).__name__}',
                param,
                ctx,
            )
        except Exception as err:
            self.fail(
                f'Failed to convert {value!r} into a valid list due to {err!r}',
                param,
                ctx,
            )


ActivityParamType = CustomParamType()


def log(*outputs, **kwargs):
    """Log an output to stderr"""
    kwargs.setdefault('file', sys.stderr)
    print(*outputs, **kwargs)  # noqa: T201


def read_config(path):
    """Read the gitlab-activity config data

    Parameters
    ----------
    path : str
        Path to the config file

    Returns
    -------
    dict
        Config data
    """
    config = None

    if Path(path).exists():
        config = toml.loads(Path(path).read_text(encoding='utf-8'))
        log(f'gitlab-activity configuration loaded from {Path(path)}.')

    if GITLAB_ACTIVITY.exists() and not config:
        config = toml.loads(GITLAB_ACTIVITY.read_text(encoding='utf-8'))
        log(f'gitlab-activity configuration loaded from {GITLAB_ACTIVITY}.')

    if PYPROJECT.exists():
        data = toml.loads(PYPROJECT.read_text(encoding='utf-8'))
        pyproject_config = data.get('tool', {}).get('gitlab-activity')
        if pyproject_config:
            if not config:
                config = pyproject_config
                log(f'gitlab-activity configuration loaded from {PYPROJECT}.')
            else:
                log(f'Ignoring gitlab-activity configuration from {PYPROJECT}.')

    if PACKAGE_JSON.exists():
        data = json.loads(PACKAGE_JSON.read_text(encoding='utf-8'))
        if 'gitlab-activity' in data:
            if not config:
                config = data['gitlab-activity']
                log(f'gitlab-activity configuration loaded from {PACKAGE_JSON}.')
            else:
                log(f'Ignoring gitlab-activity configuration from {PACKAGE_JSON}.')

    config = config or {}
    try:
        jsonschema.validate(config, schema=SCHEMA)
    except jsonschema.exceptions.ValidationError as err:
        log(f'Failed to validate the config file data. Validation error is \n\n{err}')
        print_config(config)
    return config


def print_config(config):
    """Print gitlab-activity config data when there is an error in CLI

    Parameters
    ----------
    config : dict
        Config data
    """
    log('Current gitlab-activty config: \n')
    log(json.dumps(config, indent=2))


def get_auth_token():
    """Returns auth token from GITLAB_ACCESS_TOKEN env var or glab auth status -t cmd"""
    token = None
    if 'GITLAB_ACCESS_TOKEN' in os.environ:
        # Access token is stored in a local environment variable so just use this
        log(
            'Using GLAB access token stored in `GITLAB_ACCESS_TOKEN`.',
            file=sys.stderr,
        )
        token = os.environ.get('GITLAB_ACCESS_TOKEN')
    else:
        # Attempt to use the gh cli if installed
        try:
            p = subprocess.run(
                ['glab', 'auth', 'status', '-t'], check=True, capture_output=True
            )
            token = re.search(
                r'(.*)Token: (.*)$', p.stderr.decode().strip(), re.M
            ).groups()[1]
        except subprocess.CalledProcessError:
            log('glab cli has no token. Login with `glab auth login`')
        except FileNotFoundError:
            log(
                'glab cli not found, so will not use it for auth. To download, '
                'see https://gitlab.com/gitlab-org/cli/-/releases'
            )
    return token


def parse_target(target, auth):
    """Parses target based on input such as:

    - gitlab-org
    - gitlab-org/gitlab-docs
    - gitlab.com/gitlab-org
    - http(s)://gitlab.com/gitlab-org
    - http(s)://gitlab.com/gitlab-org/gitlab-docs(.git)
    - git@gitlab.com:gitlab-org/gitlab-docs(.git)

    If there is no domain in target, default domain gitlab.com will be returned

    Parameters
    ----------
    target : str
        The GitLab organization/repo for which you want to grab recent issues/MRs.
        Can either be *just* and organization (e.g., `gitlab-org`) or a combination
        organization and repo (e.g., `gitlab-org/gitlab-doc`). If the former, all
        repositories for that org will be used. If the latter, only the specified
        repository will be used.
    auth : str
        An authentication token for GitLab.

    Returns
    -------
    domain : str
        Domain of the target repository
    target : str
        Sanitized target after stripping elements like 'http(s)', '.git'
    ttype : str
        Target type ie., project/group/namespace
    targetid : str
        Target numeric ID used by GitLab
    """
    # Always use default domain as gitlab.com
    domain = 'gitlab.com'

    # Get group/project
    if target.startswith('http'):
        domain = target.split('//')[-1].split('/')[0]
        target = '/'.join(target.split('//')[-1].split('/')[1:])
    elif '@' in target:
        domain = target.split('@')[-1].split(':')[0]
        target = '/'.join(target.split('@')[-1].split(':')[1:])
    elif '.' in target:
        # split target by /
        parts = target.split('/')
        for p in parts:
            if '.' in p:
                domain = p
                break
        target = target.split(domain)[-1].strip('/')

    # Strip .git if exists
    if target.endswith('.git'):
        target = target.rsplit('.git', 1)[0]

    # Split by group and project
    #
    # target can be a path to group or subgroup or project or namespace.
    # We need to find the target type (project or group or namespace) first
    #
    # Try to guess the type of target in order group, project and namespace
    ttype = None
    for ttype in ('group', 'project', 'namespace'):
        targetid = _get_project_or_group_id(domain, target, ttype, auth)
        if targetid is not None:
            break

    # Raise an error if targetid is still None
    if targetid is None:
        msg = f'Cannot identify if the target {target} is group/project/namespace'
        raise RuntimeError(msg)
    return domain, target, ttype, targetid


def get_all_tags(domain, target, targetid, auth):
    """Return all tags of the repository

    Parameters
    ----------
    domain : str
        Domain of the target repository
    target : str
        Sanitized target after stripping elements like 'http(s)', '.git'
    targetid : str
        Target numeric ID used by GitLab
    auth : str
        An authentication token for GitLab.

    Returns
    -------
    list of str | None
        List of tags or None
    """
    headers = _get_headers(auth)
    # Could not find GraphQL query to get list of tags of project
    url = f'https://{domain}/api/v4/projects/{targetid}/repository/tags'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        msg = f'Failed to get tags for target {target}'
        raise RuntimeError(msg) from None

    # Check if there is atleast one tag
    if len(response.json()) >= 1:
        return [
            (t['name'], t['target'], t['commit']['created_at']) for t in response.json()
        ]
    return None


def get_latest_tag_remote(domain, target, targetid, auth):
    """Return latest tag of a remote target via API call

    Parameters
    ----------
    domain : str
        Domain of the target repository
    target : str
        Sanitized target after stripping elements like 'http(s)', '.git'
    targetid : str
        Target numeric ID used by GitLab
    auth : str
        An authentication token for GitLab.

    Returns
    -------
    str | None
        Latest tag or None
    """
    tags = get_all_tags(domain, target, targetid, auth)
    if tags is not None:
        return tags[0][0]
    log(f'No tags found for the target {target}')
    return None


def get_namespace_projects(domain, namespace, auth):
    """Return a list of project paths in a given domain/namespace

    Parameters
    ----------
    domain : str
        Domain of the target repository
    namespace : str
        Namespace in the GitLab
    auth : str
        An authentication token for GitLab.

    Returns
    -------
    list of str | None
        List of projects in the namespace

    Raises
    ------
    RuntimeError
        If there is an error raised in the API request
    """
    # Get all projects from graphql query
    query = f"""{{
  namespace (fullPath: "{namespace}") {{
    projects {{
      edges {{
        node {{
          fullPath
        }}
      }}
    }}
  }}
}}"""

    try:
        data = _make_gql_request(domain, query, auth)
        # Get project nodes
        projects = [
            p['node']['fullPath'] for p in data['namespace']['projects']['edges']
        ]
    except requests.exceptions.HTTPError:
        projects = []
    finally:
        if not projects:
            msg = f'Failed to retrieve projects for namespace {namespace}'
            raise RuntimeError(msg)
    return projects


def _get_headers(auth):
    """Returns headers for making API request"""
    return {
        'Authorization': f'Bearer {auth}',
        'Content-Type': 'application/json',
    }


def _get_project_or_group_id(domain, target, target_type, auth):
    """Returns numeric project or group id from target

    Parameters
    ----------
    domain : str
        Domain of the target repository
    target : str
        Sanitized target after stripping elements like 'http(s)', '.git'
    target_type : str
        Target type ie., project/group/namespace
    auth : str
        An authentication token for GitLab.

    Returns
    -------
    str | None
        ID of the target or None if not found
    """
    # Get project id from graphql query
    query = f"""{{
  {target_type} (fullPath: "{target}") {{
    name
    id
  }}
}}"""

    try:
        data = _make_gql_request(domain, query, auth)
    except requests.exceptions.HTTPError:
        return None
    else:
        # Get id
        if data[target_type] is not None:
            return data[target_type]['id'].split('/')[-1]
        return None


def _make_gql_request(domain, query, auth):
    """Returns response data of the GraphQL request

    Parameters
    ----------
    domain : str
        Domain of the target repository
    query : str
        GraphQL query string

    Returns
    -------
    str | None
        ID of the target or None if not found
    """
    # Get headers
    headers = _get_headers(auth)

    # Get API URL
    url = f'https://{domain}/api/graphql'

    # Make request
    response = requests.post(url, json={'query': query}, headers=headers)
    response.raise_for_status()
    # Return data
    return response.json()['data']


def get_datetime_and_type(domain, targetid, datetime_or_git_ref, auth):
    """Return a datetime object and bool indicating if it is a git reference or
    not.

    Parameters
    ----------
    domain : str
        Domain of the target repository
    targetid : str
        Target numeric ID used by GitLab
    datetime_or_git_ref : str
        Either a datetime string or a git reference
    auth : str | None, default: None
        An authentication token for GitLab.

    Returns
    -------
    dt : str
        A datetime object
    bool
        Boolean to indicate if it is a git ref or not

    Raises
    ------
    RuntimeError
        If datetime_or_git_ref is not a valid
    """

    # Default a blank datetime_or_git_ref to current UTC time, which makes sense
    # to set the until flags default value.
    if datetime_or_git_ref is None:
        dt = datetime.datetime.now().astimezone(pytz.utc)
        return (dt, False)

    try:
        dt = _get_datetime_from_git_ref(domain, targetid, datetime_or_git_ref, auth)
    except Exception:
        try:
            dt = dateutil.parser.parse(datetime_or_git_ref)
        except Exception:
            msg = f'{datetime_or_git_ref} not found as a ref or valid date format'
            raise RuntimeError(msg) from None
        else:
            return (dt, False)
    else:
        return (dt, True)


def _get_datetime_from_git_ref(domain, repoid, ref, auth):
    """Return a datetime from a git reference"""
    headers = _get_headers(auth)
    url = f'https://{domain}/api/v4/projects/{repoid}/repository/commits/{ref}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return dateutil.parser.parse(response.json()['committed_date'])
