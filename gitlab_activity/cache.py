"""Cache activity data in form of CSV files"""
from pathlib import Path

import pandas as pd

from gitlab_activity import ALLOWED_KINDS
from gitlab_activity import DEFAULT_PATH_CACHE
from gitlab_activity.utils import log


def cache_data(query_data, path_cache):
    """Cache activity data

    Parameters
    ----------
    query_data : pandas DataFrame
        A munged collection of data returned from your query. This
        will be a combination of issues and MRs.
    path_cache : str | bool
        If True default path will be used.
        If string cache will be stored at this path
    """
    # Use default path if no specific path is given
    if path_cache is True:
        path_cache = DEFAULT_PATH_CACHE
    path_cache = Path(path_cache)

    # Create dirs if they do not exist
    if not path_cache.exists():
        log(f'Creating a new cache at {path_cache}')
        path_cache.mkdir()

    for (org, repo), _ in query_data.groupby(['org', 'repo']):
        # Create a subdir for each org/repo
        path_repo_cache = path_cache.joinpath(org, repo)
        path_repo_cache.mkdir(parents=True, exist_ok=True)

        # MRs cache
        data_mrs = query_data.query("kind == 'mergeRequests'")
        path_mr_cache = path_repo_cache.joinpath('mergeRequests.csv')
        if path_mr_cache.exists():
            mrs_cache = pd.read_csv(path_mr_cache)
            mrs_cache = pd.concat([mrs_cache, data_mrs], sort=False).drop_duplicates(
                subset=['webUrl']
            )
        else:
            mrs_cache = data_mrs
        mrs_cache.to_csv(path_mr_cache, index=False)

        # Issues cache
        data_issues = query_data.query("kind == 'issues'")
        path_issues_cache = path_repo_cache.joinpath('issues.csv')
        if path_issues_cache.exists():
            issues_cache = pd.read_csv(path_issues_cache)
            issues_cache = pd.concat(
                [issues_cache, data_issues], sort=False
            ).drop_duplicates(subset=['webUrl'])
        else:
            issues_cache = data_issues
        issues_cache.to_csv(path_issues_cache, index=False)


def load_from_cache(target, kind, path_cache=None):
    """Load data from cache

    Parameters
    ----------
    target : str
        The GitLab organization/repo for which you want to grab recent issues/MRs.
    kind : str
        Type of activity data to load from cache
    path_cache : str | None
        If None default cache path will be used.
        If string cache will be stored at this path

    Returns
    -------
    data : pandas DataFrame
        A munged collection of data returned from your query.

    Raises
    ------
    RuntimeError
        When kind is not in ALLOWED_KINDS or target is not valid
    FileNotFoundError
        When path_cache file does not exist
    """
    # Checks for correctness and existence of cache
    if path_cache is None:
        path_cache = DEFAULT_PATH_CACHE
    if kind not in ALLOWED_KINDS:
        msg = f'Kind must be one of {ALLOWED_KINDS}, not {kind}'
        raise RuntimeError(msg)
    path_cache = Path(path_cache)

    # Resolve org / repo
    parts = target.split('/')
    if len(parts) == 1:
        org = parts[0]
        repo = None
    elif len(parts) > 1:
        org = parts[0]
        repo = '/'.join(parts[1:])
    else:
        msg = f'Target must be of form org/repo, got: {target}'
        raise RuntimeError(msg)

    path_cache_org = path_cache.joinpath(org)
    if not path_cache_org.exists():
        msg = f'Could not find cache for org: {org}'
        raise FileNotFoundError(msg)
    if repo is None:
        repos = [
            ii
            for ii in path_cache_org.glob('*')
            if ii.is_dir() and not ii.name.startswith('.')
        ]
    else:
        repos = [path_cache_org.joinpath(repo)]

    # Now loop through the repos and grab data from the cache
    data = []
    for irepo in repos:
        path_cache_repo = path_cache_org.joinpath(irepo)
        if not path_cache_repo.exists():
            msg = f'Could not find cache for org/repo: {org}/{repo}'
            raise FileNotFoundError(msg)
        path_csv = path_cache_repo.joinpath(f'{kind}.csv')
        data.append(pd.read_csv(path_csv))
    return pd.concat(data)


def get_cache_stats(path_cache=None):
    """Get stats from cached data"""
    if path_cache is None:
        path_cache = DEFAULT_PATH_CACHE

    out_data = []
    for org in path_cache.glob('*'):
        for repo in org.glob('*'):
            for ipath in repo.glob('*'):
                kind = ipath.with_suffix('').name
                idata = pd.read_csv(ipath)
                mindate = idata['createdAt'].min()
                maxdate = idata['createdAt'].max()
                nrecords = idata.shape[0]
                out_data.append(
                    {
                        'org': org.name,
                        'repo': repo.name,
                        'kind': kind,
                        'start': mindate,
                        'end': maxdate,
                        'nrecords': nrecords,
                    }
                )
    return pd.DataFrame(out_data)
