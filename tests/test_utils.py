"""Tests for utility functions"""
import os
from pathlib import Path
from unittest import mock

import toml
from pytest import mark
from pytest import raises

from gitlab_activity import utils
from gitlab_activity.utils import *


@mark.parametrize(
    'config',
    [
        {'options': {'activity': {'foo': 'bar'}}},
        {'options': {'since': 12345678}},
        {'options': {'append': 'True'}},
        {'activity': 'True'},
        {'activity': {'bot_users': {'foo': 'bar'}}},
        {'activity': {'foo': []}},
        {'activity': {'categories': {'issues': {'foo': 'bar'}}}},
        {'activity': {'categories': {'merge_requests': [{'foo': 'bar'}]}}},
    ],
)
def test_read_config_validation(tmpdir, config):
    """Test if read_config catch validation exceptions"""
    path_tmp = Path(tmpdir)
    config_file = path_tmp.joinpath('config.toml')

    # Config that raises validation error
    with open(config_file, 'w') as f:
        toml.dump(config, f)

    with raises(RuntimeError) as excinfo:
        read_config(config_file)


@mark.parametrize(
    'env_name',
    ['GITLAB_ACCESS_TOKEN', 'CI_JOB_TOKEN'],
)
def test_auth_token(env_name):
    """Test if auth token can be taken from different env vars"""
    with mock.patch.dict(os.environ, {env_name: env_name}):
        print(os.environ)
        token = get_auth_token()
        if env_name == 'CI_JOB_TOKEN':
            # Seems like CI_JOB_TOKEN is always masked even when we mock environ
            assert any(v in token for v in [env_name, '[MASKED]'])
        else:
            assert token == env_name
    assert False


@mark.parametrize(
    'arg,exp_domain,exp_target',
    [
        ('example.domain.io/foo/bar', 'example.domain.io', 'foo/bar'),
        ('http://user@example.domain.io/foo/bar', 'example.domain.io', 'foo/bar'),
    ],
)
def test_parse_target(arg, exp_domain, exp_target):
    """Test parse_target when targets are given in non-standard format"""

    domain, target = sanitize_target(arg)

    assert domain == exp_domain
    assert target == exp_target


def test_get_commits_exception():
    """Test get_commits catches exception when invalid input is given"""
    commits = get_commits('gitlab.com', 'foo', 123456, 'token')
    assert commits == None


def test_all_tags_exception():
    """Test get_all_tags raises Exception when tags not found"""
    with raises(RuntimeError) as excinfo:
        get_all_tags('gitlab.com', 'foo', 12345, 'token')
    assert str(excinfo.value) == 'Failed to get tags for target foo'


def test_get_namespace_projects_exception():
    """Test get_namespace_projects raises exception when invalid target"""
    with raises(RuntimeError) as excinfo:
        get_namespace_projects('gitlab.com', 'foo', 'token')
    assert str(excinfo.value) == 'Failed to retrieve projects for namespace foo'


def test_get_project_id():
    """Test _get_project_id returns None when invalid input"""
    tid = utils._get_project_or_group_id('gitlab.com', 'foo', 'group', 'token')
    assert tid is None


def test_get_datetime_and_type():
    """Test get_datetime_and_type raises exception when invalid input"""
    with raises(RuntimeError) as excinfo:
        get_datetime_and_type('gitlab.com', 12345, '2023-15-10', 'token')
    assert str(excinfo.value) == '2023-15-10 not found as a ref or valid date format'
