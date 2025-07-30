"""Config for pytest"""
import os
from functools import lru_cache

import pandas as pd
import pytest

from gitlab_activity import DEFAULT_CATEGORIES
from gitlab_activity import lib

# Set an environment variable for tests
os.environ['PYTEST'] = '1'


def pytest_runtest_setup(item):
    for marker in item.iter_markers():
        if marker.name == 'requires_internet' and not network_connectivity():  # no cov
            pytest.skip('No network connectivity')


def pytest_configure(config):
    config.addinivalue_line(
        'markers', 'requires_internet: Tests that require access to the internet'
    )


def running_in_ci():
    return os.environ.get('CI_JOB_TOKEN') is not None


@lru_cache
def network_connectivity():  # no cov
    if running_in_ci():
        return True

    import socket

    try:
        # Test availability of DNS first
        host = socket.gethostbyname('www.google.com')
        # Test connection
        socket.create_connection((host, 80), 2).close()
        return True
    except Exception:
        return False


@pytest.fixture
def sp_completed_process():
    """Fixture to subprocess.CompletedProcess"""

    class MockSubprocessReturn:
        def __init__(self, stdout='', stderr=''):
            self.stdout = stdout.encode()
            self.stderr = stderr.encode()

    return MockSubprocessReturn


@pytest.fixture
def fake_activity_df():
    df = pd.DataFrame(
        [
            {
                'state': 'merged',
                'id': 'gid://gitlab/MergeRequest/1',
                'iid': 1,
                'title': 'Add feature',
                'webUrl': 'https://gitlab.com/org/repo/-/merge_requests/1',
                'createdAt': '2025-07-23T00:00:00Z',
                'updatedAt': '2025-07-23T00:00:00Z',
                'mergedAt': '2025-07-23T08:00:00Z',
                'mergeCommitSha': 'sha1',
                'sourceBranch': 'feat',
                'reference': '!1',
                'sourceProject': {'webUrl': 'https://gitlab.com/org/repo'},
                'targetBranch': 'main',
                'labels': ['feature'],
                'author': ('alice', 'https://gitlab.com/alice'),
                'mergeUser': ('alice', 'https://gitlab.com/alice'),
                'awardEmoji': {'edges': []},
                'commenters': {'edges': []},
                'committers': [('alice', 'https://gitlab.com/alice')],
                'reviewers': [],
                'participants': [('alice', 'https://gitlab.com/alice')],
                'activity': 'merge_requests',
                'org': 'org',
                'repo': 'repo2',
                'emojis': [],
                'closedAt': None,
                'mergeRequestsCount': None,
            },
            {
                'state': 'merged',
                'id': 'gid://gitlab/MergeRequest/2',
                'iid': 2,
                'title': 'Skip this',
                'webUrl': 'https://gitlab.com/org/repo/-/merge_requests/2',
                'createdAt': '2025-07-23T00:00:00Z',
                'updatedAt': '2025-07-23T00:00:00Z',
                'mergedAt': '2025-07-23T10:00:00Z',
                'mergeCommitSha': 'sha2',
                'sourceBranch': 'skip',
                'reference': '!2',
                'sourceProject': {'webUrl': 'https://gitlab.com/org/repo'},
                'targetBranch': 'main',
                'labels': ['foo', 'skip-changelog', 'bar', 'feature'],
                'author': ('bob', 'https://gitlab.com/bob'),
                'mergeUser': ('bob', 'https://gitlab.com/bob'),
                'awardEmoji': {'edges': []},
                'commenters': {'edges': []},
                'committers': [('bob', 'https://gitlab.com/bob')],
                'reviewers': [],
                'participants': [('bob', 'https://gitlab.com/bob')],
                'activity': 'merge_requests',
                'org': 'org',
                'repo': 'repo2',
                'emojis': [],
                'closedAt': None,
                'mergeRequestsCount': None,
            },
        ]
    )
    df.since_dt = pd.Timestamp('2025-07-01T00:00:00Z')
    df.until_dt = pd.Timestamp('2025-07-24T00:00:00Z')
    df.since_dt_str = '2025-07-01T00:00:00Z'
    df.until_dt_str = '2025-07-24T00:00:00Z'
    df.since_is_git_ref = False
    df.until_is_git_ref = False
    return df


@pytest.fixture
def changelog_md():
    return lib.generate_activity_md(
        'org/repo',
        since='2025-07-01',
        until='2025-07-24',
        activity=['merge_requests'],
        include_contributors_list=True,
        categories=DEFAULT_CATEGORIES,
        bot_users=[],
        exclude_labels=['skip-changelog'],
    )
