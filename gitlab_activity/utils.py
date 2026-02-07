"""Utility functions for gitlab-activity"""
import datetime
import json
import os
import re
import subprocess
import sys
from datetime import timezone
from pathlib import Path

import click
import dateutil.parser
import jsonschema
import requests
import toml
from importlib_resources import files

PYPROJECT = Path('pyproject.toml')
PACKAGE_JSON = Path('package.json')

SCHEMA = files('gitlab_activity').joinpath('schema.json').read_text()
SCHEMA = json.loads(SCHEMA)


class CustomParamType(click.ParamType):
    """
    Custom Parameter Type used in click for casting labels_metadata, bot_users
    and exclude_labels
    """

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


ActivityParamType = CustomParamType()


class BearerAuth(requests.auth.AuthBase):
    """Custom Auth class for GitLab authentication"""

    def __init__(self, token) -> None:
        self.token = token

    def __call__(self, r):  # noqa: ANN204
        r.headers['Authorization'] = f'Bearer {self.token}'
        return r


def log(*outputs, **kwargs):
    """Log an output to stderr"""
    kwargs.setdefault('file', sys.stderr)
    print(*outputs, **kwargs)  # noqa: T201


def convert_snake_case_to_camel_case(input):
    """Converts snake_case input str to camelCase"""
    # saving first and rest using split()
    init, *temp = input.split('_')

    # using map() to get all words other than 1st
    # and titlecasing them
    return ''.join([init.lower(), *map(str.title, temp)])


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
        print_config(config)
        msg = f'Failed to validate the config file data. Validation error is \n\n{err}'
        raise RuntimeError(msg) from None
    return config


def print_config(config):
    """Print gitlab-activity config data when there is an error in CLI

    Parameters
    ----------
    config : dict
        Config data
    """
    log('Current gitlab-activty config: \n')
    # Redact auth token
    config['auth'] = '*****'
    log(json.dumps(config, indent=2))


def get_next_version_specifier():
    """Return next version specifier by checking environment variables

    The following environment variables will be checked in order and version
    is returned

    - NEXT_VERSION_SPECIFIER
    - CI_COMMIT_TAG

    Returns
    -------
    version : str | None
        Version string
    """
    for env_var in ['NEXT_VERSION_SPECIFIER', 'CI_COMMIT_TAG']:
        if os.environ.get(env_var):
            return os.environ.get(env_var)

    # If not found return None
    return None


def get_auth_token():
    """Returns auth token.

    The auth token retrieval process is as follows:

    - First env var `GITLAB_ACCESS_TOKEN` is check.
    - If there is no token yet, we look into `CI_JOB_TOKEN` that is available in CI jobs
    - If it fails in previous two attempts, we try to get it from
     `glab auth status -t` cmd

    Returns
    -------

    token : str
        Auth token
    """
    token = None
    if os.environ.get('GITLAB_ACCESS_TOKEN') is not None:
        # Access token is stored in a local environment variable so just use this
        log('Using GitLab access token stored in GITLAB_ACCESS_TOKEN.')
        token = os.environ.get('GITLAB_ACCESS_TOKEN')
    elif os.environ.get('CI_JOB_TOKEN') is not None:
        # Attempt to use CI_JOB_TOKEN which is available in CI jobs
        log('Using GitLab access token stored in CI_JOB_TOKEN.')
        token = os.environ.get('CI_JOB_TOKEN')
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


def check_auth_token(target, token):
    """Checks if auth token is valid.

    Returns
    -------

    valid : bool
        If Auth token is valid or not
    """
    # Get domain from target
    domain, _ = sanitize_target(target)

    # Query that returns username
    query = 'query {currentUser {name}}'

    try:
        _make_gql_request(domain, query, token)
    except requests.exceptions.HTTPError as e:
        log(f'Invalid auth token {e}')
        return False
    except requests.exceptions.ConnectionError:
        log(f'Failed to connect to domain {domain}')
        return False
    except Exception as e:
        log(f'Failed to make request to domain {domain} due to {e}')
        return False
    else:
        return True


def sanitize_target(target):
    """Sanitize target and returns domain and target"""
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

    # If domain has @ and/or : strip them too
    if '@' in domain:
        domain = domain.split('@')[-1]

    # Strip .git if exists
    if target.endswith('.git'):
        target = target.rsplit('.git', 1)[0]
    return domain, target


def parse_target(target, token):
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
    token : str
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
    domain, target = sanitize_target(target)

    # Split by group and project
    #
    # target can be a path to group or subgroup or project or namespace.
    # We need to find the target type (project or group or namespace) first
    #
    # Try to guess the type of target in order group, project and namespace
    ttype = None
    for ttype in ('group', 'project', 'namespace'):
        targetid = _get_project_or_group_id(domain, target, ttype, token)
        if targetid is not None:
            break

    # Raise an error if targetid is still None
    if targetid is None:
        msg = f'Cannot identify if the target {target} is group/project/namespace'
        raise RuntimeError(msg)
    return domain, target, ttype, targetid


def get_commits(domain, target, targetid, token, since_dt=None, until_dt=None):
    """Return commits between since and until

    Parameters
    ----------
    domain : str
        Domain of the target repository
    target : str
        Sanitized target after stripping elements like 'http(s)', '.git'
    targetid : str
        Target numeric ID used by GitLab
    token : str
        An authentication token for GitLab.
    since_dt : str | default = None
        Return commits since this datetime.
    until_dt : str | default = None
        Return commits until this datetime

    Returns
    -------
    list of str | None
        List of tags or None
    """
    url = f'https://{domain}/api/v4/projects/{targetid}/repository/commits'

    # Make query params
    query_params = {}
    if since_dt is not None:
        query_params.update({'since': since_dt, 'page': 1, 'per_page': 50})
    if until_dt is not None:
        query_params.update({'until': until_dt, 'page': 1, 'per_page': 50})
    all_data = []
    while True:
        try:
            response = requests.get(url, params=query_params, auth=_get_auth(token))
            response.raise_for_status()
        except requests.exceptions.HTTPError:  # noqa: PERF203
            # Ignore all errors
            log(f'Failed to get commits for the target {target}')
            return None
        else:
            all_data.extend(response.json())
            if response.headers.get('x-next-page'):
                query_params['page'] += 1
            else:
                break
    if len(all_data) < 1:
        log(
            f'No commits found between {since_dt} and {until_dt} '
            f'for the target {target}'
        )
        return None
    return all_data


def get_all_tags(domain, target, targetid, token):
    """Return all tags of the repository

    Parameters
    ----------
    domain : str
        Domain of the target repository
    target : str
        Sanitized target after stripping elements like 'http(s)', '.git'
    targetid : str
        Target numeric ID used by GitLab
    token : str
        An authentication token for GitLab.

    Returns
    -------
    list of str
        List of tags
    """
    # Could not find GraphQL query to get list of tags of project
    url = f'https://{domain}/api/v4/projects/{targetid}/repository/tags'
    try:
        response = requests.get(url, auth=_get_auth(token))
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        msg = f'Failed to get tags for target {target}'
        raise RuntimeError(msg) from None

    # Return [] if there are no tags
    if len(response.json()) == 0:
        until_dt = str(datetime.datetime.now(timezone.utc))
        all_tags = [['Untagged release', '', until_dt]]
    else:
        all_tags = [
            [t['name'], t['target'], t['commit']['created_at']] for t in response.json()
        ]

    # We make a query for commits only until first tag commit which
    # should give us all commits from start
    commits = get_commits(domain, target, targetid, token, until_dt=all_tags[-1][-1])

    # Finally add a dummy tag 0.0.0 from start of the repository to get
    # first tag's activity in the report
    if commits is not None:
        all_tags += [['0.0.0', commits[-1]['id'], commits[-1]['committed_date']]]
        # Use first commit as pseudo tag so we get activity since begining until first
        # tag
        if all_tags[0][0] == 'Untagged release':
            all_tags[0][1] = commits[-1]['id']
            all_tags[0][2] = commits[-1]['committed_date']
    return all_tags


def get_latest_tag(domain, target, targetid, token):
    """Return latest tag of a target via API call

    Parameters
    ----------
    domain : str
        Domain of the target repository
    target : str
        Sanitized target after stripping elements like 'http(s)', '.git'
    targetid : str
        Target numeric ID used by GitLab
    token : str
        An authentication token for GitLab.

    Returns
    -------
    str | None
        Latest tag or None
    """
    try:
        tags = get_all_tags(domain, target, targetid, token)
    except RuntimeError:
        log(f'No tags found for the target {target}')
        return None
    else:
        return tags[0][1]


def get_latest_mr(domain, target, token):
    """Return latest MR of a target via API call

    Parameters
    ----------
    domain : str
        Domain of the target repository
    target : str
        Sanitized target after stripping elements like 'http(s)', '.git'
    token : str
        An authentication token for GitLab.

    Returns
    -------
    str | None
        Latest MR or None
    """
    # Get all projects from graphql query
    query = f"""{{
  project (fullPath: "{target}") {{
    mergeRequests(first: 5, state: merged, sort: MERGED_AT_DESC) {{
      nodes {{
        iid
        mergeCommitSha
        mergedAt
      }}
    }}
  }}
}}"""

    try:
        data = _make_gql_request(domain, query, token)
        # Get project nodes
        merge_requests = [
            (p['mergeCommitSha'], p['mergedAt'])
            for p in data['project']['mergeRequests']['nodes']
        ]
    except (requests.exceptions.HTTPError, KeyError):
        merge_requests = []
    finally:
        if not merge_requests:
            msg = f'Failed to MRs for target {target}'
            raise RuntimeError(msg)
    return merge_requests[0][0]


def get_namespace_projects(domain, namespace, token):
    """Return a list of project paths in a given domain/namespace

    Parameters
    ----------
    domain : str
        Domain of the target repository
    namespace : str
        Namespace in the GitLab
    token : str
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
        data = _make_gql_request(domain, query, token)
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


def _get_auth(token):
    """Returns custom auth class for making API request"""
    return BearerAuth(token)


def _encode(value):
    """Returns URL safe encoded value"""
    return requests.utils.quote(value, safe="")


def _get_project_or_group_id(domain, target, target_type, token):
    """Returns numeric project or group id from target

    Parameters
    ----------
    domain : str
        Domain of the target repository
    target : str
        Sanitized target after stripping elements like 'http(s)', '.git'
    target_type : str
        Target type ie., project/group/namespace
    token : str
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
        data = _make_gql_request(domain, query, token)
    except requests.exceptions.HTTPError:
        return None
    else:
        # Get id
        if data[target_type] is not None:
            return data[target_type]['id'].split('/')[-1]
        return None


def _make_gql_request(domain, query, token):
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
    # Get API URL
    url = f'https://{domain}/api/graphql'

    # Make request
    response = requests.post(url, json={'query': query}, auth=_get_auth(token))
    response.raise_for_status()

    # Check if data key exists
    if 'data' not in response.json():
        return {}
    # Return data
    return response.json()['data']


def get_datetime_and_type(domain, targetid, datetime_or_git_ref, token):
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
    token : str | None, default: None
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
        dt = datetime.datetime.now(timezone.utc)
        return (dt, False)

    try:
        dt = _get_datetime_from_git_ref(domain, targetid, datetime_or_git_ref, token)
    except Exception:
        try:
            dt = dateutil.parser.parse(datetime_or_git_ref)
        except Exception:
            msg = f'{datetime_or_git_ref} not found as a ref or valid date format'
            raise RuntimeError(msg) from None
        else:
            return (dt.astimezone(timezone.utc), False)
    else:
        return (dt.astimezone(timezone.utc), True)


def _get_datetime_from_git_ref(domain, repoid, ref, token):
    """Return a datetime from a git reference"""
    url = f'https://{domain}/api/v4/projects/{repoid}/repository/commits/{_encode(ref)}'
    response = requests.get(url, auth=_get_auth(token))
    response.raise_for_status()
    return dateutil.parser.parse(response.json()['committed_date'])
