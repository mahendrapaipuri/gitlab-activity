"""gitlab_activity Module"""
from pathlib import Path

# Markers to insert changelog entry
START_MARKER = '<!-- <START NEW CHANGELOG ENTRY> -->'
END_MARKER = '<!-- <END NEW CHANGELOG ENTRY> -->'

# Supported activity types
ALLOWED_ACTIVITIES = ['issues', 'mergeRequests']

# Default path to cache data
DEFAULT_PATH_CACHE = Path('~/.cache/gitlab-activity-data').expanduser()

# Default groups
_DEFAULT_GROUPS = [
    {
        'labels': ['feature', 'feat', 'new'],
        'pre': ['NEW', 'FEAT', 'FEATURE'],
        'description': 'New features added',
    },
    {
        'labels': ['enhancement', 'enhancements'],
        'pre': ['ENH', 'ENHANCEMENT', 'IMPROVE', 'IMP'],
        'description': 'Enhancements made',
    },
    {
        'labels': ['bug', 'bugfix', 'bugs'],
        'pre': ['FIX', 'BUG'],
        'description': 'Bugs fixed',
    },
    {
        'labels': ['maintenance', 'maint'],
        'pre': ['MAINT', 'MNT'],
        'description': 'Maintenance and upkeep improvements',
    },
    {
        'labels': ['documentation', 'docs', 'doc'],
        'pre': ['DOC', 'DOCS'],
        'description': 'Documentation improvements',
    },
    {
        'labels': ['deprecation', 'deprecate'],
        'pre': ['DEPRECATE', 'DEPRECATION', 'DEP'],
        'description': 'Deprecated features',
    },
]
DEFAULT_GROUPS = {
    'issues': _DEFAULT_GROUPS,
    'mrs': _DEFAULT_GROUPS,
}

# Default bot users
DEFAULT_BOT_USERS = [
    'codecov',
    'codeco-io',
    'dependabot',
    'gitlab-bot',
    'pre-commit-ci',
    'welcome',
    'stale',
]
