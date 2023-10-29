"""Class that makes and parses GraphQL query"""
from collections import Counter

import numpy as np
import pandas as pd
import requests
from tqdm.auto import tqdm

from gitlab_activity.utils import convert_snake_case_to_camel_case
from gitlab_activity.utils import get_namespace_projects
from gitlab_activity.utils import log

GQL_ELEMENT_QUERY = {
    "merge_requests": """\
        state
        id
        iid
        title
        webUrl
        createdAt
        updatedAt
        mergedAt
        mergeCommitSha
        sourceBranch
        reference
        sourceProject {
          webUrl
        }
        targetBranch
        labels (first: 10) {
          edges {
            node {
              title
            }
          }
        }
        author {
          username
          webUrl
          bot
        }
        mergeUser {
          username
          webUrl
          bot
        }
        awardEmoji (first: 10) {
          edges {
            node {
              emoji
              name
            }
          }
        }
        commenters (last: 100) {
          edges {
            node {
              username
              webUrl
              bot
            }
          }
        }
        committers(first: 100) {
          edges {
            node {
              username
              webUrl
              bot
            }
          }
        }
        reviewers (first: 100) {
          edges {
            node {
              username
              webUrl
              bot
            }
          }
        }
        participants (first: 100) {
          edges {
            node {
              username
              webUrl
              bot
            }
          }
        }
""",
    "issues": """\
        state
        id
        iid
        title
        webUrl
        createdAt
        updatedAt
        closedAt
        mergeRequestsCount
        labels (first: 10) {
          edges {
            node {
              title
            }
          }
        }
        reference
        author {
          username
          webUrl
          bot
        }
        participants (last: 100) {
          edges {
            node {
              username
              webUrl
              bot
            }
          }
        }
""",
}

GQL_TEMPLATE = """\
{{
  {scope_query} {{
    {search_query} {{
        count
        nodes {{
          {search_elements}
        }}
        pageInfo {{
            endCursor
            hasNextPage
        }}
     }}
  }}
}}
"""


class FailedQueryException(Exception):
    pass


# Define our query object that we'll re-use for gitlab search
class GitLabGraphQlQuery:
    def __init__(  # PLR0913
        self,
        domain,
        target,
        target_type,
        activity,
        since,
        until,
        display_progress=True,
        auth=None,
    ) -> None:
        """Run a GitLab GraphQL query and return the issue/PR data from it.

        Parameters
        ----------
        domain : string
          The GitLab search domain, e.g., gitlab.com, example.gitlab.com
        target : string
          The GitLab query target. It can be a project, group or namespace
        target_type : string
          The GitLab query target type. It can be a project, group or namespace
        activity : string
          The type of GitLab activity to query. Whether for issues or for
          merge_requests
        since : string
          Activity since this date. It should be a date string
        until : string
          Activity until this data. It should be a date string
        display_progress : bool
          Whether to display a progress bar as data is fetched.
        auth : string | None
          An authentication token for GitLab. If None, then the environment
          variable `GITLAB_ACCESS_TOKEN` will be tried.
        """
        self.domain = domain
        self.activity = activity
        # For internal use only. GraphQL expects camelCased variables
        self._activity = convert_snake_case_to_camel_case(activity)
        # Get headers
        self.headers = {
            'Authorization': f'Bearer {auth}',
            'Content-Type': 'application/json',
        }

        # If target type is project or group we can use the graphql out-of-the-box
        # If it is a namespace, first get all projects in the namespace and execute
        # query for each project separately
        if target_type in ['project', 'group']:
            self.targets = [target]
            self.scope = target_type
        else:
            self.targets = get_namespace_projects(self.domain, target, auth)
            self.scope = 'project'

        # Different queries for issues and merge_requests. We need to get created/merged
        # MRs in time window and created/closed for issues
        self.search_queries = {
            'created': f'{self._activity} (createdAfter: \"{since}\", createdBefore: \"{until}\")',  # noqa: E501
        }
        if self.activity == 'issues':
            self.search_queries.update(
                {
                    'closed': f'{self._activity} (closedAfter: \"{since}\", closedBefore: \"{until}\")',  # noqa: E501
                }
            )
        elif self.activity == 'merge_requests':
            self.search_queries.update(
                {
                    'merged': f'{self._activity} (mergedAfter: \"{since}\", mergedBefore: \"{until}\")',  # noqa: E501
                }
            )

        self.gql_template = GQL_TEMPLATE
        self.display_progress = display_progress

    def _request(self, gql_query):
        """Make actual request to GraphQL API and return response if successful"""
        response = requests.post(
            f'https://{self.domain}/api/graphql',
            json={'query': gql_query},
            headers=self.headers,
        )
        if response.status_code != 200:  # noqa: PLR2004
            msg = (
                f'Query failed to run by returning code of '
                f'{response.status_code}: {gql_query}'
            )
            raise FailedQueryException(msg)
        if 'errors' in response.json():
            msg = (
                f"Query failed to run with error "
                f"{response.json()['errors']}: {gql_query}"
            )
            raise FailedQueryException(msg)
        return response.json()

    @staticmethod
    def get_user(user):
        return (user['username'], user['webUrl']) if not pd.isna(user) else user

    @staticmethod
    def get_emoji_count(emojis):
        """map awardEmoji graph to total emoji count"""
        return Counter(
            [emoji['node']['emoji'] for emoji in emojis['edges']]
        ).most_common()

    @staticmethod
    def get_unique_users(users):
        """map reviewer/committer graph to unique list of users excluding bots"""
        if pd.isna(users) or not users:
            return []
        return sorted(
            {
                (user['node']['username'], user['node']['webUrl'])
                for user in users['edges']
                if not user['node']['bot']
            }
        )

    def get_data(self, n_pages=100, n_per_page=50):
        """Make a request to the GitLab GraphQL API and get data.

        Return a pandas DataFrame of the issue / MR activity
        corresponding to the query you ran.
        """

        # Ref: https://docs.gitlab.com/ee/api/graphql/reference/index.html
        pageInfo = None
        self.issues_and_or_mrs = []
        for target in self.targets:
            # log(f'Running {self.activity} query on target {target}')

            # Make query string
            scope_query = f'{self.scope} (fullPath: \"{target}\")'
            break_from_target = False
            for search_type, search_query in self.search_queries.items():
                for ipage in range(n_pages):
                    gitlab_search_query = search_query[:-1] + f', first: {n_per_page})'
                    if ipage != 0:
                        gitlab_search_query = (
                            gitlab_search_query[:-1]
                            + f', after: "{pageInfo["endCursor"]}")'
                        )

                    gql_query = self.gql_template.format(
                        scope_query=scope_query,
                        search_query=gitlab_search_query,
                        search_elements=GQL_ELEMENT_QUERY[self.activity],
                    )

                    # Parse the response for this pagination
                    json = self._request(gql_query)['data'][self.scope]
                    if ipage == 0:
                        if json[self._activity]['count'] == 0:
                            log(
                                f'Found no entries for {search_type} {self.activity} '
                                f'query on target {target}'
                            )
                            break_from_target = True
                            break

                        n_pages = int(
                            np.ceil(json[self._activity]['count'] / n_per_page)
                        )
                        log(
                            f"Found {json[self._activity]['count']} {search_type} "
                            f"{self.activity} on target {target}, which will take "
                            f"{n_pages} pages"
                        )
                        prog = tqdm(
                            total=json[self._activity]['count'],
                            desc='Downloading',
                            unit=f' {self.activity}',
                            disable=n_pages == 1 or not self.display_progress,
                        )

                    # If there are no entries break from this target
                    if break_from_target:
                        break

                    # Add the JSON to the raw data list
                    self.issues_and_or_mrs.extend(json[self._activity]['nodes'])
                    pageInfo = json[self._activity]['pageInfo']
                    self.last_query = gql_query

                    # Update progress and should we stop?
                    prog.update(len(json[self._activity]['nodes']))
                    if not pageInfo['hasNextPage']:
                        break

        # If there are no entries overall return
        if len(self.issues_and_or_mrs) == 0:
            return pd.DataFrame()

        # Create a dataframe of the issues and/or PRs
        data = pd.DataFrame(self.issues_and_or_mrs)

        data['author'] = data['author'].map(self.get_user)
        data['labels'] = data['labels'].map(
            lambda a: [edge['node']['title'] for edge in a['edges']]
        )
        data['activity'] = self.activity

        # URLs of form https://gitlab.com/org/grp1/grp2/repo/-/issues/[\d+]
        # We split at '/-/' and take top group as org and rest as repo path
        data['org'] = data['webUrl'].map(lambda a: a.split('/-/')[0].split('/')[3])
        data['repo'] = data['webUrl'].map(
            lambda a: '/'.join(a.split('/-/')[0].split('/')[4:])
        )

        # Get unique participants
        data['participants'] = data['participants'].map(self.get_unique_users)

        if self.activity == 'merge_requests':
            data['mergeUser'] = data['mergeUser'].map(self.get_user)
            data['emojis'] = data['awardEmoji'].map(self.get_emoji_count)
            data['reviewers'] = data['reviewers'].map(self.get_unique_users)
            data['committers'] = data['committers'].map(self.get_unique_users)
        # Snippet to generate dataset for tests
        # tt = '_'.join(target.split('/'))
        # import os
        # if os.path.exists(tt):
        #     prev_data = pd.read_pickle(f'{tt}.pkl')
        #     curr_data = pd.concat(
        #         [prev_data, data]
        #     ).drop_duplicates(subset=['id']).reset_index(drop=True)
        # else:
        #     curr_data = data
        # curr_data.to_pickle(f'{tt}.pkl')
        return data
