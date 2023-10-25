"""Git related functions for gitlab-activity"""
import subprocess

from gitlab_activity.utils import get_latest_tag_remote
from gitlab_activity.utils import log


def git_installed_check():
    """Return True if git is installed else False"""
    try:
        subprocess.check_call(
            ['git', '--help'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return False
    return True


def get_remote_ref():
    """Return the remote reference of repository by querying the local repo.

    Returns
    -------

    str
        Remote origin URL

    Raises
    ------
    ValueError
        When no remote origin found or current folder is not git repository
    """
    out = subprocess.run(['git', 'remote', '-v'], check=True, stdout=subprocess.PIPE)
    remotes = out.stdout.decode().split('\n')
    remotes = {
        remote.split('\t')[0]: remote.split('\t')[1].split()[0]
        for remote in remotes
        if remote
    }
    if 'upstream' in remotes:
        return remotes['upstream']
    elif 'origin' in remotes:  # noqa: RET505
        return remotes['origin']
    msg = (
        'No remote/upstream origin found on local repository or '
        'current directory is not a git repository'
    )
    raise ValueError(msg)


def get_latest_tag(domain, target, targetid, local, auth):
    """Return the latest tag name for a given repository or None."""
    # If it is local repo, run git command to get all tags
    if local:
        try:
            out = subprocess.run(
                ['git', 'describe', '--tags'], check=True, stdout=subprocess.PIPE
            )
        except subprocess.CalledProcessError:
            log(f'No tags found for the target {target}')
            return None
        else:
            return out.stdout.decode().rsplit("-", 2)[0]
    return get_latest_tag_remote(domain, target, targetid, auth)