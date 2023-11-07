---
id: contributing
title: Contributing
---

<!-- ../../../CONTRIBUTING.md -->

# Contributing to GitLab Activity

If you're reading this section, you're probably interested in contributing to
`gitlab-activity`. Welcome and thanks for your interest in contributing. There are many
ways to contribute to the project.

## Contribution types

### Bug reports

Bug reports are an important type of contribution - it's important to get feedback
about how the tool is failing, and there's no better way to do that than to hear
about real-life failure cases. A good bug report will include:

- A minimal, reproducible example - a small, self-contained script that can reproduce
  the behavior is the best way to get your bug fixed. For more information and tips on
  how to structure these, read
  [Stack Overflow's guide to creating a minimal, complete, verified example](https://stackoverflow.com/help/mcve).

- The platform and versions of everything involved, at a minimum please include
  operating system, python version and `gitlab-activity` version.
  Instructions on getting your versions:

      - `gitlab-activity`: `python -c "import gitlab-activity; print(gitlab-activity.__version__)"`
      - Python: `python --version`

- A description of the problem - what is happening and what should happen.

While pull requests fixing bugs are accepted, they are not required - the bug report
in itself is a great contribution.

### Feature requests

If you would like to see a new feature in `gitlab-activity`, it is probably best to
start an issue for discussion rather than taking the time to implement a feature
which may or may not be appropriate for `gitlab-activity`. For minor features
(ones where you don't have to put a lot of effort into the MR), a pull request
is fine but still not necessary.

### Merge requests

If you would like to fix something in `gitlab-activity` - improvements to documentation,
bug fixes, feature implementations, fixes to the build system, etc - merge requests
are welcome! Where possible, try to keep your coding to PEP 8 style. `pre-commit` can
be used to stay within styling guides.

The most important thing to include in your merge request are tests - please write
one or more tests to cover the behavior you intend your patch to improve.

## Development Setup

### Using a virtual environment

It is advisable to work in a virtual environment for development of `gitlab-activity`.
This can be done using [virtualenv](https://virtualenv.pypa.io/):

```
python -m virtualenv .venv      # Create virtual environment in .venv directory
source .venv/bin/activate       # Activate the virtual environment
```

Alternatively you can create a
[conda environment](https://conda.io/docs/user-guide/tasks/manage-environments.html):

```
conda create -n gitlab-activity                # Create a conda environment
# conda create -n gitlab-activity python=3.8   # Or specify a version
conda activate gitlab-activity                 # Activate the conda environment
```

Once your virtual environment is created, install the library in development mode:

```
pip install -e '.[dev]'
```

This will install all the package dependencies including the ones required for
development.

### pre-commit

The package uses [pre-commit](https://pre-commit.com/) to run styling packages like
`black`, `ruff`, _etc._. First install `pre-commit` components to setup the development
environment

```
pre-commit install
```

After this step, `pre-commit` will run at every git commit and reformats the files
according to styling config provided in the `pyproject.toml`. If user wishes to run
`pre-commit` manually, it can be done using

```
pre-commit run --all-files
```

### Tests

Tests can be run in the current environment using `pytest` command

```
pytest
```

In order to test multiple Python versions, we can use
[hatch environments](https://hatch.pypa.io/latest/environment/) which are analogous
to tools `tox` and `nox`. Unlike the stated tools, `hatch` can create a Python
installation without having to dependent on existing Python versions on the
local machine.

In order to use `hatch` environments, first the user need to install `hatch` in
the current environment

```
pip install 'hatch>1.7.0'
```

:::note

It is important to install `hatch>1.7.0` as the feature that creates the different
versions of Python environments has been added after `1.7.0`. See related
[PR](https://github.com/pypa/hatch/pull/1002).

:::

Once `hatch` is installed, users can run test in a given Python environment using

```
hatch run +py=3.11 test:test
```

This command will do following:

- Create a Python environment with Python 3.11
- Install project and its dependencies in development mode
- Invoke `pytest` command and executes all the tests

If user wishes to test all Python versions that the package supports, they can do
it with single command

```
hatch run test:test
```

If users want to run the tests with all the supported Python versions _modulo_
Python 3.8, it can be done using

```
hatch run -py=3.8 test:test
```

To list all the supported environments of current package, we can use

```
hatch env show --ascii
```

which will list the names of supported environments and their variants.
