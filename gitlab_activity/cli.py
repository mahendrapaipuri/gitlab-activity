import sys
from pathlib import Path

import click

from gitlab_activity import DEFAULT_BOT_USERS
from gitlab_activity import DEFAULT_LABELS_METADATA
from gitlab_activity import START_MARKER
from gitlab_activity.git import get_remote_ref
from gitlab_activity.git import git_installed_check
from gitlab_activity.lib import generate_activity_md
from gitlab_activity.lib import generate_all_activity_md
from gitlab_activity.lib import generate_changelog
from gitlab_activity.utils import get_auth_token
from gitlab_activity.utils import log
from gitlab_activity.utils import parse_target
from gitlab_activity.utils import read_config
from gitlab_activity.utils import RepoDataParamType

# Default config file location
DEFAULT_CFG = Path(Path.cwd()) / '.gitlab-activity.toml'


def configure(ctx, _, filename):
    """Callback when invoked main command"""
    # Read the config file
    config = read_config(filename)
    # Update the default ctx with values from config options section
    ctx.default_map = config.get('options', {})
    # Populate "hidden" options from repository section
    ctx.default_map.update(config.get('repository', {}))


@click.group(invoke_without_command=True)
@click.option(
    '-c',
    '--config',
    type=click.Path(dir_okay=False),
    default=DEFAULT_CFG,
    callback=configure,
    is_eager=True,
    expose_value=False,
    help="""A TOML file that can be used to configure gitlab-activity. All CLI
    flags can be passed using the config file. In addition this file can be used
    to define the labels and bot users that repo/org uses.

    The labels on MRs will be used to separate them the generated Changelog.
    List of bot users defined in the config file will be excluded in contributors list

    By default, config file .gitlab-activity.yaml in current directory will be
    used if it exists. The configuration also supports

    - pyproject.toml within section [tool.gitlab-activity]

    - package.json within gitlab-activity section

    The order of priority of loading configuration file is as follows:

    - .gitlab-activity.yaml

    - pyproject.toml

    - package.json

    Configuration **will not** be merged from different files. All configuration
    will be loaded from the first file that is found in the current directory.
    """,
    show_default=True,
    metavar='<str>',
)
@click.option(
    '-t',
    '--target',
    type=str,
    help="""The GitLab organization/repo for which you want to grab recent
    issues/mergeRequests. Can either be *just* an organization (e.g., `gitlab-org`),
    or a combination organization and repo (e.g., `gitlab-org/gitlab-docs`).
    If the former, all repositories for that org will be used. If the latter,
    only the specified repository will be used.

    Can also be a GitLab URL to an organization or repo e.g.,
    https://gitlab.com/gitlab-org/gitlab-docs.

    Self hosted gitlab instances are also supported. Ensure that full URL of
    the organization or repository is provided when using self hosted instances.
    In absence of domain in the URL, gitlab.com will be used.

    If None, the org/repo will attempt to be inferred from `git remote -v`.""",
    default=None,
    show_default=True,
    metavar='<str>',
)
@click.option(
    '-b',
    '--branch',
    type=str,
    help="""The branch or reference name to filter pull requests by""",
    default='main',
    show_default=True,
    metavar='<str>',
)
@click.option(
    '-s',
    '--since',
    type=str,
    help="""Return issues/mergeRequests with activity since this date or git reference.
    Can be any string that is parsed with dateutil.parser.parse.""",
    default=None,
    show_default=True,
    metavar='<str>',
)
@click.option(
    '-u',
    '--until',
    type=str,
    help="""Return issues/mergeRequests with activity until this date or git reference.
    Can be any string that is parsed with dateutil.parser.parse. If none, today's
    date will be used.""",
    default=None,
    show_default=True,
    metavar='<str>',
)
@click.option(
    '-o',
    '--output',
    type=str,
    help="""Write the markdown to a file if desired.""",
    default=None,
    show_default=True,
    metavar='<str>',
)
@click.option(
    '--append',
    is_flag=True,
    help="""Whether to append to the existing output file. If this flag is active
    there should be a marker

    <!-- <START NEW CHANGELOG ENTRY> -->

    in the existing changelog file. In the absence of this marker an error will be
    raised.
    """,
    default=False,
    show_default=True,
)
@click.option(
    '--kind',
    type=str,
    help="""Return only issues or mergeRequests. If None, both will be returned.""",
    default=None,
    show_default=True,
    metavar='<str>',
)
@click.option(
    '--auth',
    type=str,
    help="""An authentication token for GitLab. If None, then the environment
    variable `GITLAB_ACCESS_TOKEN` will be tried. If it does not exist
    then attempt to infer the token from `glab auth status -t`.""",
    default=None,
    show_default=True,
    metavar='<str>',
)
@click.option(
    '--heading-level',
    type=int,
    help="""Base heading level to add when generating markdown.
    Useful when including changelog output in an existing document.
    By default, changelog is emitted with one h1 and an h2 heading for each section.
    --heading-level=2 starts at h2, etc.""",
    default=1,
    show_default=True,
    metavar='<int>',
)
@click.option(
    '--include-issues',
    is_flag=True,
    help="""Include Issues in the markdown output""",
    default=False,
    show_default=True,
)
@click.option(
    '--include-opened',
    is_flag=True,
    help="""Include a list of opened items in the markdown output""",
    default=False,
    show_default=True,
)
@click.option(
    '--include-contributors-list',
    is_flag=True,
    help="""Include a list of contributors at the end of each release log""",
    default=False,
    show_default=True,
)
@click.option(
    '--strip-brackets',
    is_flag=True,
    help="""If True, strip any text between brackets at the beginning of the issue/PR
    title. E.g., [MRG], [DOC], etc.""",
    default=False,
    show_default=True,
)
@click.option(
    '--all',
    is_flag=True,
    help="""Whether to include all the GitLab tags""",
    default=False,
    show_default=True,
)
@click.option(
    '--cache',
    is_flag=True,
    help="""Whether to cache activity data in CSV files. The data files can be
    found at ~/.cache/gitlab-activity-cache folder organized based on org/repo.""",
    default=False,
    show_default=True,
)
# Following options are hidden and can only configured by config file
@click.option(
    '--labels-metadata',
    help="""Metadata of labels""",
    type=RepoDataParamType,
    hidden=True,
)
@click.option(
    '--bot-users',
    help="""List of bot users""",
    type=RepoDataParamType,
    hidden=True,
)
def main(**kwargs):
    """Generate a markdown changelog of GitLab activity within a date window"""
    if not git_installed_check():
        log('git is required to run gitlab-activity. Exiting...')
        sys.exit(1)

    # Automatically detect the target from remotes if we haven't had one passed.
    kwargs['local'] = False
    if not kwargs['target']:
        try:
            ref = get_remote_ref()
            kwargs['target'] = ref
            kwargs['local'] = True
        except Exception:
            log('Could not automatically detect target and none was given. Exiting...')
            sys.exit(1)

    # Check if auth token is available
    if not kwargs['auth']:
        kwargs['auth'] = get_auth_token()
        # We can't use this without auth because we hit rate limits immediately
        if not kwargs['auth']:
            log(
                'Either the environment variable GITLAB_ACCESS_TOKEN or the '
                '--auth flag or must be used to pass a Personal Access Token '
                'needed by the GitLab API. You can generate a token at '
                'https://gitlab.com/-/profile/personal_access_tokens. Note that while '
                'working with a public repository, you dont need to set any '
                'scopes on the token you create. Alternatively, you may log-in '
                'via the GitLab CLI (`glab auth login`). Exiting...'
            )
            sys.exit(1)

    # Check if output file is specified if --append flag exists
    if kwargs['append'] and not kwargs['output']:
        log(
            '--append flag is used but no output file specified. '
            'Please use -o/--output to specify an output file. Exting...'
        )
        sys.exit(1)
    elif kwargs['append'] and kwargs['output']:
        changelog_path = Path(kwargs['output']).resolve()
        # If specified file does not exist, exit
        if not Path(changelog_path).exists():
            log(f'Output file {changelog_path} does not exist. Exiting...')
            sys.exit(1)

        # Get the existing changelog and run some validation
        changelog = Path(changelog_path).read_text(encoding='utf-8')
        if START_MARKER not in changelog:
            log(
                f'Missing insert marker in changelog at {changelog_path}. '
                f'Please insert a marker {START_MARKER}. Exiting...'
            )
            sys.exit(1)

        if changelog.find(START_MARKER) != changelog.rfind(START_MARKER):
            log(
                f'More than one insert markers are found in changelog at '
                f'{changelog_path}. Please remove duplicates. Exiting...'
            )
            sys.exit(1)

    # Ensure since is provided if group is set as target
    _, _, target_type, _ = parse_target(kwargs['target'], kwargs['auth'])
    if target_type in ['group', 'namespace'] and not kwargs['since']:
        log(
            '--since option is required when a group and/or namespace activity is '
            'requested. Exiting...'
        )
        sys.exit(1)

    # Check if labels_metadata and bot_users are provided, If not use a basic one
    if kwargs['labels_metadata'] is None:
        kwargs['labels_metadata'] = DEFAULT_LABELS_METADATA
    if kwargs['bot_users'] is None:
        kwargs['bot_users'] = DEFAULT_BOT_USERS

    common_kwargs = {
        'kind': kwargs['kind'],
        'auth': kwargs['auth'],
        'include_issues': bool(kwargs['include_issues']),
        'include_opened': bool(kwargs['include_opened']),
        'strip_brackets': bool(kwargs['strip_brackets']),
        'include_contributors_list': bool(kwargs['include_contributors_list']),
        'branch': kwargs['branch'],
        'local': kwargs['local'],
        'labels_metadata': kwargs['labels_metadata'],
        'bot_users': kwargs['bot_users'],
        'cached': kwargs['cache'],
    }

    if kwargs['all']:
        md = generate_all_activity_md(
            kwargs['target'], since=kwargs['since'], **common_kwargs
        )
    else:
        md = generate_activity_md(
            kwargs['target'],
            since=kwargs['since'],
            until=kwargs['until'],
            heading_level=kwargs['heading_level'],
            **common_kwargs,
        )

    if not md:
        return

    if kwargs['output']:
        generate_changelog(kwargs['output'], md, kwargs['append'])
    else:
        print(md)  # noqa: T201


if __name__ == "__main__":
    main()
