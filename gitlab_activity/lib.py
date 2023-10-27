"""Use the GraphQL api to grab issues/MRs that match a query."""
import copy
import datetime
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytz

from gitlab_activity import ALLOWED_ACTIVITIES
from gitlab_activity import DEFAULT_GROUPS
from gitlab_activity import END_MARKER
from gitlab_activity import START_MARKER
from gitlab_activity.cache import cache_data
from gitlab_activity.git import get_latest_tag
from gitlab_activity.graphql import GitLabGraphQlQuery
from gitlab_activity.utils import get_all_tags
from gitlab_activity.utils import get_datetime_and_type
from gitlab_activity.utils import log
from gitlab_activity.utils import parse_target

# Placeholder columns for creating an empty df
PLACEHOLDER_DF_COLS = [
    'createdAt',
    'mergedAt',
    'state',
    'contributors',
    'labels',
    'title',
    'repo',
]


def get_activity(target, since, until=None, activity=None, auth=None, cached=False):
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
    activity : ["issue", "mergeRequests"], default: None
        Return only issues or MRs. If None, only mergeRequests will be returned
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

    if activity and not all(a in ALLOWED_ACTIVITIES for a in activity):
        msg = f'Activity must be one of {ALLOWED_ACTIVITIES}'
        raise RuntimeError(msg)
    requested_activity = ('mergeRequests') if activity is None else activity

    # Query for both opened and closed issues/mergeRequests in this window
    query_data = []
    for act in requested_activity:
        log(
            f'Running search query on {target} for {act} '
            f'from {since_dt_str} until {until_dt_str}',
        )
        qql = GitLabGraphQlQuery(
            domain, target, target_type, act, since_dt_str, until_dt_str, auth=auth
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
    activity=None,
    auth=None,
    include_opened=False,
    strip_brackets=False,
    include_contributors_list=False,
    branch=None,
    local=False,
    groups=None,
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
    activity : ["issues", "mergeRequests"] | None, default: None
        Return only issues or MRs. If None, only mergeRequests will be returned.
    auth : str | None, default: None
        An authentication token for GitLab. If None, then the environment
        variable `GITLAB_ACCESS_TOKEN` will be tried.
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
    groups : list of dict | None, default: None
        A list of the dict of groups with their metadata to use in generating
        the markdown report.

        Must be one of form:

            [
                {"labels": [ "feature", "feat", "new" ],
                 "pre": [ "NEW", "FEAT", "FEATURE" ],
                 "description": "New features added" },
            ]

        The elements in labels and pre can be regex expressions.

        If None, all of the MRs will be placed as one group.
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

    # Get all tags and sha for each tag for only projects
    # For group activity use dummy tags and get activity between since and now
    if target_type == 'project':
        tags = get_all_tags(domain, target, targetid, auth)
    else:
        until = f'{datetime.datetime.now().astimezone(pytz.utc):%Y-%m-%dT%H:%M:%SZ}'
        tags = [
            (f'Activity since {since}', until, until),
            (f'Activity since {since}', since, since),
        ]

    # Generate a changelog entry for each version and sha range
    output = ''

    for i in range(len(tags) - 1):
        curr_tag = tags[i]
        prev_tag = tags[i + 1]

        # Tag refs
        since_ref = prev_tag[1]
        until_ref = curr_tag[1]

        # Tag name
        tag = curr_tag[0]

        # Tag date. Use only date and strip time
        tag_date = curr_tag[2].split('T')[0]

        log(f'Tag {i + 1} of {len(tags)} being processed')
        md = generate_activity_md(
            target,
            since=since_ref,
            heading_level=2,
            until=until_ref,
            auth=auth,
            activity=activity,
            include_opened=include_opened,
            strip_brackets=strip_brackets,
            include_contributors_list=include_contributors_list,
            branch=branch,
            local=local,
            groups=groups,
            bot_users=bot_users,
            cached=cached,
        )

        if not md:
            continue

        # Replace the header line with our version tag
        md = '\n'.join(md.splitlines()[1:])

        output += f"""
## {tag} ({tag_date})
{md}
"""
    return output


def generate_desc_from_label(label):
    """Generate a description from label"""
    desc = f"{' '.join([w.capitalize() for w in label.split('_')])}"
    if 'Mrs' in desc:
        desc = desc.split('Mrs')[0] + 'MRs'
    return desc


def update_groups_with_activity_data(groups, data):
    """Separate the activity data based on groups

    Parameters
    ----------
    groups : list of dict | None
        A list of the dict of groups with their metadata to use in generating
        the markdown report.
    data : dict(str, pandas DataFrame)
        Dict of grouped Issues/MRs munged Dataframe data

    Returns
    -------
    grouped_data : dict
        Updated groups with activity data
    """
    grouped_data = {}
    # If groups is None, initialize one
    if groups is None:
        groups = DEFAULT_GROUPS
    # Iterate through dict and separate each activity data based on labels
    for gtype, group_data in data.items():
        # Data desc
        desc = generate_desc_from_label(gtype)
        # Get current group from data type
        group = groups[gtype.split('_')[-1]]
        # # If groups is None, initialize one
        # if initialize_groups:
        #     group = [
        #         {
        #             'description': f'All {desc}',
        #             'labels': ['.*'],
        #             'pre': [],
        #         }
        #     ]

        # This container will hold all grouped data for each activity type
        # As groups is nested object, we need to make a deep copy
        group_and_data = copy.deepcopy(group)

        for group in group_and_data:
            # Initialize our labels with empty data
            group.update(
                {
                    'mask': None,
                    'md': [],
                    'data': None,
                }
            )

            # Separate out items by their label types
            # First find the MRs/Issues based on label
            mask = group_data['labels'].map(
                lambda rlabels, group=group: any(
                    re.match(re.escape(rf'{label}'), rlabel)
                    for label in group['labels']
                    for rlabel in rlabels
                )
            )

            # Now find MRs/Issues based on prefix
            mask_pre = group_data['title'].map(
                lambda title, group=group: any(
                    re.match(re.escape(rf'{pre}'), title) for pre in group['pre']
                )
            )
            mask = mask | mask_pre

            group['data'] = group_data.loc[mask]
            group['mask'] = mask

        # All remaining MRs/Issues w/o a label go here
        all_masks = np.array([~group['mask'].values for group in group_and_data])

        mask_others = all_masks.all(0)
        others = group_data.loc[mask_others]
        other_description = f'Unlabelled {desc}'

        # Add some optional kinds of MRs/Issues
        group_and_data.append(
            {
                'description': other_description,
                'data': others,
                'md': [],
                'labels': [],
                'pre': [],
            }
        )
        grouped_data[gtype] = group_and_data
    return grouped_data


def generate_activity_md(
    target,
    since=None,
    until=None,
    activity=None,
    auth=None,
    include_opened=False,
    strip_brackets=False,
    include_contributors_list=False,
    heading_level=1,
    branch=None,
    local=False,
    groups=None,
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
    activity : ["issues", "mergeRequests"], default: None
        Return only issues or MRs. If None, only mergeRequests will be returned.
    auth : str | None, default: None
        An authentication token for GitLab. If None, then the environment
        variable `GITLAB_ACCESS_TOKEN` will be tried.
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
    groups : list of dict | None, default: None
        A list of the dict of groups with their metadata to use in generating
        the markdown report.

        Must be one of form:

            [
                {"labels": [ "feature", "feat", "new" ],
                 "pre": [ "NEW", "FEAT", "FEATURE" ],
                 "description": "New features added" },
            ]

        The elements in labels and pre can be regex expressions.

        If None, all of the MRs will be placed as one group.
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
        target, since=since, until=until, activity=activity, auth=auth, cached=cached
    )
    if data.empty:
        return None

    # Collect authors of comments on issues/MRs that they didn't open for our
    # attribution list
    # all_contributors = []

    # add column for participants in each issue (not just original author)
    data['contributors'] = [[]] * len(data)
    for ix, row in data.iterrows():
        # contributor order:
        # - author
        # - committers
        # - participants  ref: https://docs.gitlab.com/ee/api/graphql/reference/index.html#mergerequestparticipantconnection

        item_contributors = [row.author]

        if row.activity == 'mergeRequests':
            # committers and participants are already unique list of user tuples
            # so we can safely append them
            item_contributors += [
                user
                for user in row.committers + row.participants
                if user not in item_contributors
            ]
            if row.mergeUser and row.mergeUser != row.author:
                item_contributors.append(row.mergeUser)

        # Treat participants as contributors for issues
        if row.activity == 'issues':
            item_contributors += [
                user for user in row.participants if user not in item_contributors
            ]

        # Remove duplicates and bot accounts from user configured list
        item_contributors = [
            user
            for user in list(set(item_contributors))
            if user[0] not in bot_users and 'bot' not in user[0]
        ]

        # record contributor list (ordered, unique)
        data.at[ix, 'contributors'] = item_contributors

    # Filter the MRs by branch (or ref) if given
    # If there are no MR entries, we cannot access targetBranch column. Check for it
    # before accessing it
    if branch is not None and 'targetBranch' in data.columns:
        index_names = data[
            (data['activity'] == 'mergeRequests') & (data['targetBranch'] != branch)
        ].index
        data.drop(index_names, inplace=True)

    # Separate into MRs and issues
    merge_requests = data.query("activity == 'mergeRequests'")
    issues = data.query("activity == 'issues'")

    # if filtered df are empty override them with placeholders
    if merge_requests.empty:
        merge_requests = pd.DataFrame(columns=PLACEHOLDER_DF_COLS)
    if issues.empty:
        issues = pd.DataFrame(columns=PLACEHOLDER_DF_COLS)

    # Separate into closed and opened
    until_dt_str = data.until_dt_str  # noqa: F841
    since_dt_str = data.since_dt_str  # noqa: F841
    merged_mrs = merge_requests.query(
        'mergedAt >= @since_dt_str and mergedAt <= @until_dt_str'
    )
    opened_mrs = merge_requests.query(
        'createdAt >= @since_dt_str and createdAt <= @until_dt_str'
    )
    closed_issues = issues.query(
        'closedAt >= @since_dt_str and closedAt <= @until_dt_str'
    )
    opened_issues = issues.query(
        'createdAt >= @since_dt_str and createdAt <= @until_dt_str'
    )

    # Remove the MRs/Issues that from "opened" if they were also closed
    opened_mrs = opened_mrs.query("state == 'opened'")
    opened_issues = opened_issues.query("state == 'opened'")

    # Now remove the *closed* MRs (not merged) for our output list
    merged_mrs = merged_mrs.query("state != 'closed'")

    # Add any contributors to a merged PR to our contributors list
    all_contributors = merged_mrs['contributors'].explode().unique().tolist()

    # Grouped data. Make a dict of grouped data
    data_cont = {
        'merged_mrs': merged_mrs,
    }

    # Add Opened MRs next if asked
    if include_opened:
        data_cont.update(
            {
                'opened_mrs': opened_mrs,
            }
        )

    # Finally include closed and opened issues if asked
    if 'issues' in activity:
        # If issues are asked in the report, add contributors of issues as well
        # But add participants of closed issues that successfully merged atleast
        # one MR
        all_contributors.extend(
            closed_issues.query('mergeRequestsCount > 0')['contributors']
            .explode()
            .unique()
            .tolist()
        )
        data_cont.update(
            {
                'closed_issues': closed_issues,
            }
        )
        if include_opened:
            data_cont.update(
                {
                    'opened_issues': opened_issues,
                }
            )

    # If more than one group activity is requested we need to add one more depth
    # to heading to categorize them
    group_head = ''
    if len(data_cont.values()) > 1:
        group_head = '#'

    # Update groups with data
    grouped_data = update_groups_with_activity_data(groups, data_cont)

    # Generate the markdown
    extra_head = '#' * (heading_level - 1)
    for group_data in grouped_data.values():
        for items in group_data:
            n_orgs = len(items['data']['repo'].unique())
            for repo, _ in items['data'].groupby('repo'):
                if n_orgs > 1:
                    items['md'].append(f'{extra_head}## {repo}')
                    items['md'].append('')

                for _, irowdata in items['data'].iterrows():
                    ititle = irowdata['title']
                    if (
                        strip_brackets
                        and ititle.strip().startswith('[')
                        and ']' in ititle
                    ):
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
        since = f'{data.since_dt:%Y-%m-%d}'
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
        until = f'{data.until_dt:%Y-%m-%d}'
        until_ref = until

    # SHAs for our dates to build the GitLab diff URL
    changelog_url = f'https://{domain}/{target}/-/compare/{since_ref}...{until_ref}?from_project_id={targetid}&straight=false'

    # Build the Markdown
    # If there is a env var NEXT_VERSION_SPECIFIER, use it in the header
    # Typically we can set it in CI pipelines that do releases
    if os.environ.get('NEXT_VERSION_SPECIFIER'):
        md = [
            f"{extra_head}# {os.environ.get('NEXT_VERSION_SPECIFIER')} ({data.until_dt:%Y-%m-%d})",  # noqa: E501
            '',
        ]
    else:
        md = [
            f'{extra_head}# {since}...{until}',
            '',
        ]
    # Add full changelog for only projects and do not add it for groups
    if target_type == 'project' and activity in [None, 'mergeRequests']:
        md += [
            f'([Full Changelog]({changelog_url}))',
        ]

    for gtype, group_data in grouped_data.items():
        if group_head and any(len(info['md']) > 0 for info in group_data):
            desc = generate_desc_from_label(gtype)
            md += [f'{extra_head}## {desc}']
        for info in group_data:
            if len(info['md']) > 0:
                md += ['']
                md.append(f"{extra_head}{group_head}## {info['description']}")
                md += ['']
                md += info['md']

    # Add a list of author contributions
    if include_contributors_list:
        # Ensure we remove all duplicated
        all_contributors = list(set(all_contributors))
        all_contributor_links = [
            f"[@{iauthor[0]}]({iauthor[1]})" for iauthor in all_contributors
        ]
        contributor_md = ' | '.join(all_contributor_links)
        md += ['']
        # TODO: Add link to docs when available
        md += [
            f'{extra_head}{group_head}## [Contributors to this release](https://gitlab.com/mahendrapaipuri/gitlab-activity)'
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
