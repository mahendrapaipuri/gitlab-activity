"""Basic cache module tests"""
import shutil
from pathlib import Path

import pandas as pd
from pytest import mark
from pytest import raises

from gitlab_activity.cache import cache_data
from gitlab_activity.cache import get_cache_stats
from gitlab_activity.cache import load_from_cache

# Globals
REPO = 'mahendrapaipuri/gitlab-activity-tests'
DATA_PATH = Path('tests').resolve().joinpath('resources', 'data')


@mark.parametrize(
    'df,targets',
    [
        ('repo_data.pkl', [REPO]),
        # ('group_data.pkl',
        #     [
        #      'idris-cnrs/jupyter/jupyter-services/jupyterhub-announcement',
        #      'idris-cnrs/jupyter/jupyter-services/jupyterhub-documentation',
        #      'idris-cnrs/jupyter/jupyter-services/jupyterhub-server-manager'
        #     ]
        # ),
    ],
)
def test_cache_data(tmpdir, df, targets):
    """Test cache_data given query_data"""
    path_tmp = Path(tmpdir).joinpath('activity-cache')
    data_path = DATA_PATH.joinpath(df)
    # Read query data
    query_data = pd.read_pickle(data_path)

    for activity in ['issues', 'merge_requests']:
        for target in targets:
            # Copy csv data to path_cache
            src = DATA_PATH.joinpath(f'{activity}.csv')
            dst = path_tmp.joinpath(target, f'{activity}.csv')
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

    # Cache data
    cache_data(query_data, path_cache=path_tmp)

    # Check if csv files exists
    for target in targets:
        assert path_tmp.joinpath(target, 'issues.csv').exists()
        assert path_tmp.joinpath(target, 'merge_requests.csv').exists()


@mark.parametrize('activity,count', [('issues', 6), ('merge_requests', 10)])
def test_load_cache(tmpdir, activity, count):
    """Test load_from_data given csv data"""
    path_tmp = Path(tmpdir)
    path_cache = path_tmp.joinpath(REPO)
    path_cache.mkdir(parents=True)

    # Copy csv data to path_cache
    src = DATA_PATH.joinpath(f'{activity}.csv')
    dst = path_cache.joinpath(f'{activity}.csv')
    shutil.copyfile(src, dst)

    # Load from cache
    data = load_from_cache(REPO, activity, path_cache=tmpdir)
    assert len(data) == count


def test_cache_stats(tmpdir):
    """Test cache_stats"""
    path_tmp = Path(tmpdir)
    path_cache = path_tmp.joinpath(REPO)
    path_cache.mkdir(parents=True)

    # Copy csv data to path_cache
    for activity in ['issues', 'merge_requests']:
        src = DATA_PATH.joinpath(f'{activity}.csv')
        dst = path_cache.joinpath(f'{activity}.csv')
        shutil.copyfile(src, dst)

    # Get stats
    df = get_cache_stats(tmpdir)
    assert df.query('activity == "issues"').iloc[0]['nrecords'] == 6
    assert df.query('activity == "merge_requests"').iloc[0]['nrecords'] == 10


def test_unknown_activity_type(tmpdir):
    """Test if exception is raised when unknown activity is passed"""
    # Load from cache
    with raises(RuntimeError) as excinfo:
        load_from_cache(REPO, 'foo', path_cache=tmpdir)
    assert (
        str(excinfo.value) == 'Activity must be one of issues,merge_requests, not foo'
    )


def test_cache_path_not_found(tmpdir):
    """Test if exception is raised when target's path_cache is not found"""
    org = REPO.split('/')[0]
    # Load from cache
    with raises(FileNotFoundError) as excinfo:
        load_from_cache(REPO, 'issues', path_cache=tmpdir)
    assert str(excinfo.value) == f'Could not find cache for org: {org}'
