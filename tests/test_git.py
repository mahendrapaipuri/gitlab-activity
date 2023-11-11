"""Test git.py functions"""
import os
from unittest import mock

from pytest import mark
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


@mock.patch('subprocess.check_call')
def test_git_installed_when_not_avail(sub_func):
    """Test if git_installed_check return False when subprocess raises exception"""
    sub_func.side_effect = subprocess.CalledProcessError('127', 'glab')
    status = git_installed_check()
    assert status == False


@mock.patch('subprocess.run')
@mark.parametrize(
    'value',
    [
        """origin\tgit@gitlab.com:group/project.git\t(fetch)
origin\tgit@gitlab.com:group/project.git\t(push)""",
        """upstream\tgit@gitlab.com:group/project.git\t(fetch)
upstream\tgit@gitlab.com:group/project.git\t(push)""",
    ],
)
def test_git_remotes(sub_func, value, sp_completed_process):
    """Test if git remote refs return correct remote references"""

    class MockSubprocessReturn:
        def __init__(self, stdout):
            self.stdout = stdout.encode()

    sub_func.return_value = sp_completed_process(
        stdout=value
    )  # MockSubprocessReturn(stdout=value)
    remotes = get_remote_ref()
    assert remotes == 'git@gitlab.com:group/project.git'
