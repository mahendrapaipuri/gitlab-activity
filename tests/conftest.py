"""Config for pytest"""
import os
from functools import lru_cache

import pytest


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
