"""Use the GraphQL api to grab issues/MRs that match a query."""
import datetime
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytz

from gitlab_activity import ALLOWED_KINDS
from gitlab_activity import END_MARKER
from gitlab_activity import START_MARKER
from gitlab_activity.cache import cache_data
from gitlab_activity.git import get_latest_tag
from gitlab_activity.graphql import GitLabGraphQlQuery
from gitlab_activity.utils import get_all_tags
from gitlab_activity.utils import get_datetime_and_type
from gitlab_activity.utils import log
from gitlab_activity.utils import parse_target


def get_activity(target, since, until=None, kind=None, auth=None, cached=False):
    """Return issues/MRs within a date window.

    Parameters
    ----------
    target : str
        The GitLab organization/repo for which you want to grab recent issues/MRs.
        Can either be *just* and organization (e.g., `gitlab-org`) or a combination
        organization and repo (e.g., `gitlab-org/gitlab-doc`). If the former, all
        repositories for that org will be used. If the latter, only the specified
        repository will be used.
    since : str | None
        Return issues/MRs with activity since this date or git reference. Can be
        any str that is parsed with dateutil.parser.parse.
    until : str | None, default: None
        Return issues/MRs with activity until this date or git reference. Can be
        any str that is parsed with dateutil.parser.parse. If none, today's
        date will be used.
    kind : ["issue", "pr"] | None, default: None
        Return only issues or MRs. If None, both will be returned.
    auth : str | None, default: None
        An authentication token for GitLab. If None, then the environment
        variable `GITLAB_ACCESS_TOKEN` will be tried. If it does not exist,
        then attempt to infer a token from `glab auth status -t`.
    cached : bool | str, default: False
        Whether to cache the returned results. If None, no caching is
        performed. If True, the cache is located at
        ~/.cache/gitlab-activity-data. It is organized as orgname/reponame folders
        with CSV files inside that contain the latest data. If a str it
        is treated as the path to a cache folder.

    Returns
    -------
    query_data : pandas DataFrame
        A munged collection of data returned from your query. This
        will be a combination of issues and MRs.
    """
    # Parse GitLab domain, org and repo
    domain, target, target_type, target_id = parse_target(target, auth)

    # Figure out dates for our query
    since_dt, since_is_git_ref = get_datetime_and_type(domain, target_id, since, auth)
    until_dt, until_is_git_ref = get_datetime_and_type(domain, target_id, until, auth)
    since_dt_str = f'{since_dt:%Y-%m-%dT%H:%M:%SZ}'
    until_dt_str = f'{until_dt:%Y-%m-%dT%H:%M:%SZ}'

    if kind and kind not in ALLOWED_KINDS:
        msg = f'Kind must be one of {ALLOWED_KINDS}'
        raise RuntimeError(msg)
    requested_kind = [kind] if kind else ALLOWED_KINDS

    # Query for both opened and closed issues/mergeRequests in this window
    query_data = []
    for kind in requested_kind:
        log(
            f'Running search query on {target} for {kind} '
            f'from {since_dt_str} until {until_dt_str}',
        )
        qql = GitLabGraphQlQuery(
            domain, target, target_type, kind, since_dt_str, until_dt_str, auth=auth
        )
        data = qql.get_data()
        query_data.append(data)

    query_data = (
        pd.concat(query_data).drop_duplicates(subset=['id']).reset_index(drop=True)
    )
    query_data.since_dt = since_dt
    query_data.until_dt = until_dt
    query_data.since_dt_str = since_dt_str
    query_data.until_dt_str = until_dt_str
    query_data.since_is_git_ref = since_is_git_ref
    query_data.until_is_git_ref = until_is_git_ref

    if cached:
        # Only pass copy of the data
        cache_data(query_data.copy(), cached)
    return query_data


def generate_all_activity_md(
    target,
    since,
    kind=None,
    auth=None,
    include_issues=False,
    include_opened=False,
    strip_brackets=False,
    include_contributors_list=False,
    branch=None,
    local=False,
    labels_metadata=None,
    bot_users=None,
    cached=False,
):
    """Generate a full markdown changelog of GitLab activity of a repo based on
    release tags.

    Parameters
    ----------
    target : str
        The GitLab organization/repo for which you want to grab recent issues/MRs.
        Can either be *just* and organization (e.g., `gitlab-org`) or a combination
        organization and repo (e.g., `gitlab-org/gitlab-doc`). If the former, all
        repositories for that org will be used. If the latter, only the specified
        repository will be used. Can also be a URL to a GitLab org or repo.
    since : str | None
        Return issues/MRs with activity since this date. Can be
        any str that is parsed with dateutil.parser.parse.
    kind : ["issues", "mergeRequests"] | None, default: None
        Return only issues or MRs. If None, both will be returned.
    auth : str | None, default: None
        An authentication token for GitLab. If None, then the environment
        variable `GITLAB_ACCESS_TOKEN` will be tried.
    include_issues : bool, default: False
        Include Issues in the markdown output. Default is False.
    include_opened : bool, default: False
        Include a list of opened items in the markdown output. Default is False.
    strip_brackets : bool, default: False
        If True, strip any text between brackets at the beginning of the issue/PR title.
        E.g., [MRG], [DOC], etc.
    include_contributors_list : bool, default: False
        If True, a list of contributors for a given release/tag will be added at the
        changelog entries
    branch : str | None, default: None
        The branch or reference name to filter pull requests by.
    local : bool, default: False
        If target is a local repository.
    labels_metadata : list of dict | None, default: None
        A list of the dict of labels with their metadata to use in generating
        subsets of MRs for the markdown report.

        Must be one of form:

            [
                {"labels": [ "feature", "feat", "new" ],
                 "pre": [ "NEW", "FEAT", "FEATURE" ],
                 "description": "New features added" },
            ]

        If None, all of the MRs will be placed as one subset.
    bot_users: list of str | None, default: None
        A list of bot users to be excluded from contributors list. By default usernames
        that contain 'bot' will be treated as bot users.
    cached: bool, default: False
        If True activity data will be cached in ~/.cache/gitlab-activity-cache folder
        in form of CSV files

    Returns
    -------
    entry: str
        The markdown changelog entry for all of the release tags in the repo.
    """
    # Parse GitLab domain, org and repo
    domain, target, target_type, targetid = parse_target(target, auth)

    # Get all tags and sha for each tag
    if target_type == 'project':
        tags = get_all_tags(domain, target, targetid, auth)
    else:
        until = f'{datetime.datetime.now().astimezone(pytz.utc):%Y-%m-%dT%H:%M:%SZ}'
        tags = [(f'Activity since {since}', until), (f'Activity since {since}', since)]

    # Generate a changelog entry for each version and sha range
    output = ''

    for i in range(len(tags) - 1):
        curr_tag = tags[i]
        prev_tag = tags[i + 1]

        since_ref = prev_tag[1]
        until_ref = curr_tag[1]

        tag = curr_tag[0]

        log(f'Tag {i + 1} of {len(tags)} being processed')
        md = generate_activity_md(
            target,
            since=since_ref,
            heading_level=2,
            until=until_ref,
            auth=auth,
            kind=kind,
            include_issues=include_issues,
            include_opened=include_opened,
            strip_brackets=strip_brackets,
            include_contributors_list=include_contributors_list,
            branch=branch,
            local=local,
            labels_metadata=labels_metadata,
            bot_users=bot_users,
            cached=cached,
        )

        if not md:
            continue

        # Replace the header line with our version tag
        md = '\n'.join(md.splitlines()[1:])

        output += f"""
## {tag}
{md}
"""
    return output


def generate_activity_md(
    target,
    since=None,
    until=None,
    kind=None,
    auth=None,
    include_issues=False,
    include_opened=False,
    strip_brackets=False,
    include_contributors_list=False,
    heading_level=1,
    branch=None,
    local=False,
    labels_metadata=None,
    bot_users=None,
    cached=False,
):
    """Generate a markdown changelog of GitLab activity within a date window.

    Parameters
    ----------
    target : str
        The GitLab organization/repo for which you want to grab recent issues/MRs.
        Can either be *just* and organization (e.g., `gitlab-org`) or a combination
        organization and repo (e.g., `gitlab-org/gitlab-doc`). If the former, all
        repositories for that org will be used. If the latter, only the specified
        repository will be used. Can also be a URL to a GitLab org or repo.
    since : str | None, default: None
        Return issues/MRs with activity since this date or git reference. Can be
        any str that is parsed with dateutil.parser.parse. If None, the date
        of the latest release will be used.
    until : str | None, default: None
        Return issues/MRs with activity until this date or git reference. Can be
        any str that is parsed with dateutil.parser.parse. If none, today's
        date will be used.
    kind : ["issues", "mergeRequests"] | None, default: None
        Return only issues or MRs. If None, both will be returned.
    auth : str | None, default: None
        An authentication token for GitLab. If None, then the environment
        variable `GITLAB_ACCESS_TOKEN` will be tried.
    include_issues : bool, default: False
        Include Issues in the markdown output. Default is False.
    include_opened : bool, default: False
        Include a list of opened items in the markdown output. Default is False.
    strip_brackets : bool, default: False
        If True, strip any text between brackets at the beginning of the issue/PR title.
        E.g., [MRG], [DOC], etc.
    include_contributors_list : bool, default: False
        If True, a list of contributors for a given release/tag will be added at the
        changelog entries
    heading_level : int, default: 1
        Base heading level to use.
        By default, top-level heading is h1, sections are h2.
        With heading_level=2 those are increased to h2 and h3, respectively.
    branch : str | None, default: None
        The branch or reference name to filter pull requests by.
    local : bool, default: False
        If target is a local repository.
    labels_metadata : list of dicts | None, default: None
        A list of the dict of labels with their metadata to use in generating
        subsets of MRs for the markdown report.

        Must be one of form:

            [
                {"labels": [ "feature", "feat", "new" ],
                 "pre": [ "NEW", "FEAT", "FEATURE" ],
                 "description": "New features added" },
            ]

        If None, all of the MRs will be placed as one subset.
    bot_users: list of strs | None, default: None
        A list of bot users to be excluded from contributors list. By default usernames
        that contain 'bot' will be treated as bot users.
    cached: bool, default: False
        If True activity data will be cached in ~/.cache/gitlab-activity-cache folder
        in form of CSV files

    Returns
    -------
    entry: str
        The markdown changelog entry.

    Raises
    ------
    RuntimeError
        When since is None and no latest tag is available for target
    """
    domain, target, target_type, targetid = parse_target(target, auth)

    # If no since parameter is given, find the name of the latest release
    # using the _local_ git repostory
    if since is None:
        since = get_latest_tag(domain, target, targetid, local, auth)

        # If we failed to get latest_tag raise an exception
        if since is None:
            msg = (
                f'Failed to get latest tag for target {target}. '
                f'Please provide a valid datestring using --since/-s option'
            )
            raise RuntimeError(msg)

    # Grab the data according to our query
    data = get_activity(
        target, since=since, until=until, kind=kind, auth=auth, cached=cached
    )
    if data.empty:
        return None

    # Collect authors of comments on issues/MRs that they didn't open for our
    # attribution list
    all_contributors = []

    # add column for participants in each issue (not just original author)
    data['contributors'] = [[]] * len(data)
    for ix, row in data.iterrows():
        item_contributors = []

        # contributor order:
        # - author
        # - committers
        # - merger
        # - reviewers

        item_contributors.append(row.author)

        if row.kind == 'mergeRequests':
            for committer in row.committers:
                if committer not in item_contributors:
                    item_contributors.append(committer)
            if row.mergeUser and row.mergeUser != row.author:
                item_contributors.append(row.mergeUser)
            for reviewer in row.reviewers:
                if reviewer not in item_contributors:
                    item_contributors.append(reviewer)

        for commenter in row['commenters']['edges']:
            # Skip commenter is bot
            if commenter['node']['bot']:
                continue

            # If there is bot in the name of user, treat it as bot and skip
            if 'bot' in commenter['node']['username']:
                continue

            # If username is in list of bot_users config, skip them
            if bot_users is not None and any(
                re.match(rf'{user}', commenter['node']['username'])
                for user in bot_users
            ):
                continue

            # A tuple of author's username and webURL
            comment_author = (
                commenter['node']['username'],
                commenter['node']['webUrl'],
            )

            # Add to list of commentors for this item so we can see how many times
            # they commented
            item_contributors.append(comment_author)

            # count all comments on a PR as a contributor
            if comment_author not in item_contributors:
                item_contributors.append(comment_author)

        # Treat any commentors on the issue to be a contributor
        all_contributors.extend(item_contributors)

        # record contributor list (ordered, unique)
        data.at[ix, 'contributors'] = item_contributors

    # Filter the MRs by branch (or ref) if given
    if branch is not None:
        index_names = data[
            (data['kind'] == 'mergeRequests') & (data['targetBranch'] != branch)
        ].index
        data.drop(index_names, inplace=True)

    # Separate into closed and opened
    until_dt_str = data.until_dt_str  # noqa: F841
    since_dt_str = data.since_dt_str  # noqa: F841
    merged = data.query('mergedAt >= @since_dt_str and mergedAt <= @until_dt_str')
    opened = data.query('createdAt >= @since_dt_str and createdAt <= @until_dt_str')

    # Separate into MRs and issues
    merged_mrs = merged.query("kind == 'mergeRequests'")
    closed_issues = merged.query("kind == 'issues'")
    opened_mrs = opened.query("kind == 'mergeRequests'")
    opened_issues = opened.query("kind == 'issues'")

    # Remove the MRs/Issues that from "opened" if they were also closed
    mask_open_and_close_pr = opened_mrs['id'].map(
        lambda iid: iid in merged_mrs['id'].values
    )
    mask_open_and_close_issue = opened_issues['id'].map(
        lambda iid: iid in closed_issues['id'].values
    )
    opened_mrs = opened_mrs.loc[~mask_open_and_close_pr]
    opened_issues = opened_issues.loc[~mask_open_and_close_issue]

    # Now remove the *closed* MRs (not merged) for our output list
    merged_mrs = merged_mrs.query("state != 'closed'")

    # Add any contributors to a merged PR to our contributors list
    all_contributors += merged_mrs['contributors'].explode().unique().tolist()

    # Remove duplicates from all_contributors
    all_contributors = list(set(all_contributors))

    # If labels_metadata is None, initialize one
    if labels_metadata is None:
        labels_metadata = [
            {
                'description': 'All Merged MRs',
                'labels': ['.*'],
                'pre': [],
            }
        ]

    # Initialize our labels with empty metadata
    for labelinfo in labels_metadata:
        labelinfo.update(
            {
                'mask': None,
                'md': [],
                'data': None,
            }
        )

    # Separate out items by their label types
    for labelinfo in labels_metadata:
        # First find the MRs based on label
        mask = merged_mrs['labels'].map(
            lambda rlabels, labelinfo=labelinfo: any(
                re.match(rf'{label}', rlabel)
                for label in labelinfo['labels']
                for rlabel in rlabels
            )
        )

        # Now find MRs based on prefix
        mask_pre = merged_mrs['title'].map(
            lambda title, labelinfo=labelinfo: any(
                f'{pre}:' in title for pre in labelinfo['pre']
            )
        )
        mask = mask | mask_pre

        labelinfo['data'] = merged_mrs.loc[mask]
        labelinfo['mask'] = mask

    # All remaining MRs w/o a label go here
    all_masks = np.array([~labelinfo['mask'].values for labelinfo in labels_metadata])

    mask_others = all_masks.all(0)
    others = merged_mrs.loc[mask_others]
    other_description = (
        'Other merged MRs' if len(others) != len(merged_mrs) else 'Merged MRs'
    )

    # Add some optional kinds of MRs / issues
    labels_metadata.append(
        {
            'description': other_description,
            'data': others,
            'md': [],
            'labels': [],
            'pre': [],
        }
    )
    if include_issues:
        labels_metadata.append(
            {
                'description': 'Closed issues',
                'data': closed_issues,
                'md': [],
                'labels': [],
                'pre': [],
            }
        )
        if include_opened:
            labels_metadata.append(
                {
                    'description': 'Opened issues',
                    'data': opened_issues,
                    'md': [],
                    'labels': [],
                    'pre': [],
                }
            )
    if include_opened:
        labels_metadata.append(
            {
                'description': 'Opened MRs',
                'data': opened_mrs,
                'md': [],
                'labels': [],
                'pre': [],
            }
        )

    # Generate the markdown
    mrs = labels_metadata

    extra_head = '#' * (heading_level - 1)

    for items in mrs:
        n_orgs = len(items['data']['org'].unique())
        for org, _ in items['data'].groupby('org'):
            if n_orgs > 1:
                items['md'].append(f'{extra_head}## {org}')
                items['md'].append('')

            for _, irowdata in items['data'].iterrows():
                ititle = irowdata['title']
                if strip_brackets and ititle.strip().startswith('[') and ']' in ititle:
                    ititle = ititle.split(']', 1)[-1].strip()
                contributor_list = ', '.join(
                    [f'[@{user[0]}]({user[1]})' for user in irowdata.contributors]
                )
                this_md = f"- {ititle} [#{irowdata['reference']}]({irowdata['webUrl']}) ({contributor_list})"  # noqa: E501
                items['md'].append(this_md)

    # Get functional GitLab references for only projects: any git reference
    if merged_mrs.size > 0 and not data.since_is_git_ref and target_type == 'project':
        since = f'{branch}@{{{data.since_dt:%Y-%m-%d}}}'
        closest_date_start = merged_mrs.loc[
            abs(
                pd.to_datetime(merged_mrs['mergedAt'], utc=True)
                - pd.to_datetime(data.since_dt, utc=True)
            ).idxmin()
        ]
        since_ref = closest_date_start['mergeCommitSha']
    else:
        since_ref = since

    if merged_mrs.size > 0 and not data.until_is_git_ref and target_type == 'project':
        until = f'{branch}@{{{data.until_dt:%Y-%m-%d}}}'
        closest_date_stop = merged_mrs.loc[
            abs(
                pd.to_datetime(merged_mrs['mergedAt'], utc=True)
                - pd.to_datetime(data.until_dt, utc=True)
            ).idxmin()
        ]
        until_ref = closest_date_stop['mergeCommitSha']
    else:
        until_ref = until

    # SHAs for our dates to build the GitLab diff URL
    changelog_url = f'https://{domain}/{target}/-/compare/{since_ref}...{until_ref}?from_project_id={targetid}&straight=false'

    # Build the Markdown
    md = [
        f'{extra_head}# {since}...{until}',
        '',
    ]
    # Add full changelog for only projects and do not add it for groups
    if target_type == 'project':
        md += [
            f'([full changelog]({changelog_url}))',
        ]

    for info in mrs:
        if len(info['md']) > 0:
            md += ['']
            md.append(f"{extra_head}## {info['description']}")
            md += ['']
            md += info['md']

    # Add a list of author contributions
    if include_contributors_list:
        all_contributor_links = [
            f"[@{iauthor[0]}]({iauthor[1]})" for iauthor in all_contributors
        ]
        contributor_md = ' | '.join(all_contributor_links)
        md += ['']
        md += [
            f'{extra_head}## [Contributors to this release](https://gitlab-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports)'
        ]
        md += ['']
        md += [contributor_md]
        md += ['']

    # Finally join all lines
    return '\n'.join(md)


def generate_changelog(changelog_path, entry, append=False):
    """Generate a changelog file from md entry

    Parameters
    ----------
    changelog_path : str
        Path where changelog file will be created
    entry : list of str
        The markdown changelog entry.
    append: bool, default: False
        Append the current entry to existing changelog file. If set to False
        and a changelog already exists, it will be overwritten
    """
    # If append is true, add entry to existing file
    if append:
        entry = update_changelog(changelog_path, entry)

    # Create parent dir(s) if they dont exist
    changelog_path = Path(changelog_path).resolve()
    output_dir = Path(changelog_path).parent
    if not Path(output_dir).exists():
        Path(output_dir).mkdir(parents=True)

    Path(changelog_path).write_text(entry, encoding='utf-8')
    log(f'Finished generating changelog: {changelog_path}')


def update_changelog(changelog_path, entry):
    """Update a changelog with a new entry

    Parameters
    ----------
    changelog_path : str
        Path where changelog file will be created
    entry : list of str
        The markdown changelog entry.
    """
    # Get the existing changelog and run some validation
    changelog = Path(changelog_path).read_text(encoding='utf-8')
    return insert_entry(changelog, entry)


def insert_entry(changelog, entry):
    """Insert the entry into the existing changelog

    Parameters
    ----------
    changelog : str
        Content of existing changelog file
    entry : list of str
        The markdown changelog entry

    Returns
    -------
    str
        Updated changelog content after appending entry.
    """
    # Test if we are augmenting an existing changelog entry (for new PRs)
    # Preserve existing PR entries since we may have formatted them
    new_entry = f"{START_MARKER}\n\n{entry}\n\n{END_MARKER}"
    changelog = changelog.replace(END_MARKER, "")
    changelog = changelog.replace(START_MARKER, new_entry)
    return format(changelog)
