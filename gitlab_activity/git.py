"""Git related functions for gitlab-activity"""
import subprocess


def git_installed_check():
    """Return True if git is installed else False"""
    try:
        subprocess.check_call(
            ['git', '--help'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:  # pragma: no cover
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
