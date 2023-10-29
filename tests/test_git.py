"""Test git.py functions"""
import os

from pytest import raises

from gitlab_activity.git import *


def test_invalid_local_repo(tmpdir):
    """Test when there is no local git repo"""
    old_path = os.getcwd()
    try:
        os.chdir(tmpdir)
        with raises(ValueError) as excinfo:
            get_remote_ref()
        assert 'No remote/upstream origin found on local repository ' in str(
            excinfo.value
        )
    except Exception:
        pass
    finally:
        os.chdir(old_path)
