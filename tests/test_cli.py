"""Basic CLI tests"""
import os
import shutil
from pathlib import Path
from subprocess import run

from pytest import mark

from gitlab_activity import START_MARKER

# Repo used for tests
NS, REPO = ('mahendrapaipuri', 'gitlab-activity-tests')
TIME_WINDOW = '-s 2023-10-20 -u 2023-10-28'
CONFIG_PATH = (
    Path('tests').resolve().joinpath('resources', 'config', '.gitlab-activity.toml')
)
URL = f'https://gitlab.com/{NS}/{REPO}'


@mark.parametrize(
    'cmd,basename',
    [
        # CLI with URL
        (
            f'gitlab-activity -t {URL} {TIME_WINDOW}',
            'cli_timed_activity',
        ),
        # CLI with parts
        (
            f'gitlab-activity -t {NS}/{REPO} {TIME_WINDOW}',
            'cli_timed_activity',
        ),
        # CLI without time window
        (
            f'gitlab-activity -t {NS}/{REPO}',
            'cli_since_last_tag',
        ),
        # CLI with only namespace
        (
            f'gitlab-activity -t {NS} -s 2021-01-01 -u 2023-10-28',
            'cli_timed_ns_activity',
        ),
        # CLI with only group
        (
            f'gitlab-activity -t idris-cnrs/jupyter -s 2023-07-01 -u 2023-09-01',
            'cli_timed_group_activity',
        ),
        # CLI with all time activity
        (
            f'gitlab-activity -t {URL} --all',
            'cli_all_time_activity',
        ),
        # CLI with no target. We should get activity of current repo
        (
            f'gitlab-activity -s 2023-09-01 -u 2023-10-28',
            'cli_no_target',
        ),
    ],
)
def test_cli(tmpdir, file_regression, cmd, basename):
    """The output of all file_regressions should be the same, testing diff opts."""
    path_tmp = Path(tmpdir)
    path_output = path_tmp.joinpath('out.md')

    # Add config file and output file options to cmd
    cmd += f' -c {CONFIG_PATH} -o {path_output}'
    run(cmd.split(), check=True)
    md = path_output.read_text()
    if basename == 'cli_since_last_tag':
        # Remove first line which will emit date that will always change
        md = '\n'.join(md.splitlines()[1:])
    file_regression.check(md, basename=basename, extension='.md')


def test_cli_local_all_activity(tmpdir, file_regression):
    """Test that local git repo can all activity"""
    path_tmp = Path(tmpdir)
    repo_dir = path_tmp.joinpath('repo')
    path_output = path_tmp.joinpath('out.md')

    # Clone repo to tmpdir
    cmd = f'git clone https://gitlab.com/{NS}/{REPO} {repo_dir}'
    run(cmd.split(), check=True)

    # Get all activity of local repo
    cmd = f'gitlab-activity -c {CONFIG_PATH} --all -o {path_output}'
    run(cmd.split(), check=True, cwd=repo_dir)
    md = path_output.read_text()
    file_regression.check(md, extension='.md')


def test_cli_local_latest_activity(tmpdir, file_regression):
    """Test that local git repo can get latest activity"""
    path_tmp = Path(tmpdir)
    repo_dir = path_tmp.joinpath('repo')
    path_output = path_tmp.joinpath('out.md')

    # Clone repo to tmpdir
    cmd = f'git clone https://gitlab.com/{NS}/{REPO} {repo_dir}'
    run(cmd.split(), check=True)

    # Get latest activity of local repo
    cmd = f'gitlab-activity -c {CONFIG_PATH} -o {path_output}'
    env = os.environ.copy()
    env.update({'NEXT_VERSION_SPECIFIER': 'v3.1.0'})
    run(cmd.split(), check=True, cwd=repo_dir, env=env)
    md = path_output.read_text()
    # Remove first line which will emit date that will always change
    md = '\n'.join(md.splitlines()[1:])
    file_regression.check(md, extension='.md')


def test_cli_nonexistant_tags(tmpdir):
    """Test when target with no tags and no since dt is given"""
    path_tmp = Path(tmpdir)
    path_output = path_tmp.joinpath('out.md')

    # Get all activity of local repo
    cmd = (
        f'gitlab-activity -c {CONFIG_PATH} -t mahendrapaipuri/ska-working-docs '
        f'-o {path_output}'
    )
    completed = run(cmd.split(), capture_output=True, cwd=tmpdir)
    assert 'RuntimeError' in completed.stderr.decode()
    assert completed.returncode == 1


def test_cli_nonexistant_local_repo(tmpdir):
    """Test when no target is given and local wd is not a git repo"""
    path_tmp = Path(tmpdir)
    path_output = path_tmp.joinpath('out.md')

    # Get all activity of local repo
    cmd = f'gitlab-activity -c {CONFIG_PATH} --all -o {path_output}'
    completed = run(cmd.split(), capture_output=True, cwd=tmpdir)
    assert 'Could not automatically detect target' in completed.stderr.decode()
    assert completed.returncode == 1


def test_cli_nonexistent_branch(tmpdir):
    """Test that no existend branch should emit empty md"""
    path_tmp = Path(tmpdir)
    path_output = path_tmp.joinpath('out.md')

    cmd = (
        f'gitlab-activity -c {CONFIG_PATH} -t {NS}/{REPO} -s 2023-09-20 '
        f'-o {path_output} -b foo'
    )
    run(cmd.split(), check=True)
    md = path_output.read_text()
    assert 'Full Changelog' not in md


def test_cli_include_open(tmpdir, file_regression):
    """Test that include-open option includes all open MRs."""
    path_tmp = Path(tmpdir)
    path_output = path_tmp.joinpath('out.md')

    cmd = (
        f'gitlab-activity -c {CONFIG_PATH} -t {NS}/{REPO} {TIME_WINDOW} '
        f'--include-opened -o {path_output}'
    )
    run(cmd.split(), check=True)
    md = path_output.read_text()
    md = md.split('## Opened MRs')[-1]
    file_regression.check(md, extension='.md')


def test_cli_include_issues(tmpdir, file_regression):
    """Test that issues and include-opened option includes all issues."""
    path_tmp = Path(tmpdir)
    path_output = path_tmp.joinpath('out.md')

    cmd = (
        f'gitlab-activity -c {CONFIG_PATH} -t {NS}/{REPO} {TIME_WINDOW} '
        f'--activity merge_requests --activity issues --include-opened '
        f'-o {path_output}'
    )
    run(cmd.split(), check=True)
    md = path_output.read_text()
    md = md.split('## Closed Issues')[-1]
    file_regression.check(md, extension='.md')


def test_cli_include_contributors(tmpdir, file_regression):
    """Test that include-contributors-list option includes list of contributors."""
    path_tmp = Path(tmpdir)
    path_output = path_tmp.joinpath('out.md')

    cmd = (
        f'gitlab-activity -c {CONFIG_PATH} -t {NS}/{REPO} {TIME_WINDOW} '
        f'--include-contributors-list -o {path_output}'
    )
    run(cmd.split(), check=True)
    md = path_output.read_text()
    md = md.split(
        '## [Contributors to this release](https://gitlab.com/mahendrapaipuri/gitlab-activity)'
    )[-1]
    file_regression.check(md, extension='.md')


@mark.parametrize(
    'file',
    [
        '.gitlab-activity.toml',
        'pyproject.toml',
        'package.json',
    ],
)
def test_cli_config_files(tmpdir, file):
    """Test if correct config file is being loaded"""
    path_tmp = Path(tmpdir)
    config_path = CONFIG_PATH.parent

    # Copy config data to tmp dir
    src = config_path.joinpath(f'{file}')
    dst = path_tmp.joinpath(f'{file}')
    shutil.copyfile(src, dst)

    # Invoke cmd
    cmd = f'gitlab-activity -t gitlab-org/gitlab-docs --print-config'
    completed = run(cmd.split(), check=True, capture_output=True, cwd=tmpdir)

    assert (
        f'gitlab-activity configuration loaded from {file}' in completed.stderr.decode()
    )


def test_cli_append_output_create_file(tmpdir):
    """Test if we create a file when --append and --output are used together"""
    path_tmp = Path(tmpdir)
    path_output = path_tmp.joinpath('out.md')

    # Invoke cmd
    cmd = (
        f'gitlab-activity -c {CONFIG_PATH} -t {NS}/{REPO} --append '
        f'--output={path_output}'
    )
    run(cmd.split(), check=True)

    md = path_output.read_text()
    assert START_MARKER in md


def test_cli_append_output_without_marker(tmpdir):
    """Test if we show error when append is used without marker in file"""
    path_tmp = Path(tmpdir)
    path_output = path_tmp.joinpath('out.md')
    path_output.write_text('#Changelog', encoding='utf-8')

    # Invoke cmd
    cmd = f'gitlab-activity -c {CONFIG_PATH} --append --output={path_output}'
    completed = run(cmd.split(), capture_output=True)

    assert completed.returncode == 1
    assert 'Missing insert marker' in completed.stderr.decode()


def test_cli_append_output_with_multiple_markers(tmpdir):
    """Test if we show error when append is used and multiple markers in file"""
    path_tmp = Path(tmpdir)
    path_output = path_tmp.joinpath('out.md')
    content = f"""
{START_MARKER}
# Changelog
{START_MARKER}
"""
    path_output.write_text(content, encoding='utf-8')

    # Invoke cmd
    cmd = f'gitlab-activity -c {CONFIG_PATH} --append --output={path_output}'
    completed = run(cmd.split(), capture_output=True)

    assert completed.returncode == 1
    assert 'More than one insert markers are found' in completed.stderr.decode()


def test_cli_raise_exception_when_target_is_unknown():
    """Test if we raise exception when targed cannot be identified"""
    # Invoke cmd
    cmd = f'gitlab-activity -c {CONFIG_PATH} -t {REPO}'
    completed = run(cmd.split(), capture_output=True)

    assert completed.returncode == 1
    assert (
        f'RuntimeError: Cannot identify if the target {REPO} is group/project/namespace'
        in completed.stderr.decode()
    )
