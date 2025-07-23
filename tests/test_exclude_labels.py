import re
from unittest import mock

import pytest


class TestExcludeLabels:
    @pytest.fixture(autouse=True)
    def apply_mocks(self, fake_activity_df):
        with (
            mock.patch(
                "gitlab_activity.lib.get_activity", return_value=fake_activity_df
            ),
            mock.patch(
                "gitlab_activity.utils._get_project_or_group_id", return_value=12345
            ),
        ):
            yield

    def test_skipped_merge_request_not_included(self, changelog_md):
        """`Skip this` should be filtered out by exclude_labels."""
        assert 'Skip this' not in changelog_md

    def test_its_author_not_in_contributors_list(self, changelog_md):
        """Bob shouldn`t show up as a contributor, since his MR was skipped."""
        assert 'bob' not in changelog_md

    def test_included_merge_request_present(self, changelog_md):
        """`Add feature` should still be in the changelog."""

        pattern = r"^- Add feature"
        assert re.search(pattern, changelog_md, re.MULTILINE)

    def test_its_author_shows_up(self, changelog_md):
        """Alice should appear in the contributors list."""

        pattern = r"^\[@alice\]\(https://gitlab\.com/alice\)"
        assert re.search(pattern, changelog_md, re.MULTILINE)
