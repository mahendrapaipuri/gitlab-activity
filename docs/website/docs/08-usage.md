---
id: usage
title: Usage
---

# Usage

## Auth token

`gitlab-activity` uses the GitLab API to pull information about a repository’s activity.
The token is **required** to be able to use the tool. Here are instructions to generate
and use a GitLab access token for use with `gitlab-activity`.

- Go to [GitLab Access Tokens](https://gitlab.com/-/profile/personal_access_tokens) and
  create a token with `read_api` scope.
- Then user can set an environment variable `GITLAB_ACCESS_TOKEN` with the created
  token and invoke `gitlab-activity` CLI.
- If there is no environment variable `GITLAB_ACCESS_TOKEN`, nor a token is passed
  using CLI option `--auth <token>`, the tool tries to get the token from
  `glab auth status -t` command if `glab` is installed.

## CLI options

The tool can be used to get variety of activity. All the following commands assume that user has set up an environment variable `GITLAB_ACCESS_TOKEN`. Some of the examples are:

- Get activity of the repo `repo` in namespace `ns` between `2023-01-01` and
  `2023-10-10`

```
gitlab-activity -t ns/repo --since 2023-01-01 --until 2023-10-10
```

- By default, the tool outputs only MR activity. To include issues as well use

```
gitlab-activity -t ns/repo --since 2023-01-01 --until 2023-10-10 --activity issues --activity merge_requests
```

- To include MRs and issues that are open as well, use

```
gitlab-activity -t ns/repo --since 2023-01-01 --until 2023-10-10 --activity issues --activity merge_requests --include-opened
```

- To include list of contributors at the end of each entry

```
gitlab-activity -t ns/repo --since 2023-01-01 --until 2023-10-10 --activity issues --activity merge_requests --include-opened --include-contributors-list
```

- By default, the activity is printed to standard `stdout`, _i.e.,_ terminal. To create a file with activity, use

```
gitlab-activity -t ns/repo --since 2023-01-01 --until 2023-10-10 --activity issues --activity merge_requests --include-opened --include-contributors-list --output ACTIVITYLOG.md
```

- To get all the MRs since beginning until now use,

```
gitlab-activity -t ns/repo --all --output CHANGELOG.md
```

- To get MRs since last tag and append to the existing `CHANGELOG.md`. Note that `CHANGELOG.md` should have a marker `<!-- <START NEW CHANGELOG ENTRY> -->` to indicate where to add the activity data.

```
gitlab-activity -t ns/repo --append --output CHANGELOG.md
```

## Using in CI

The repository of `gitlab-activity` uses the tool to generate its own
[changelog](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/blob/main/CHANGELOG.md)
file. Here is the excerpt of the CI job file that does the job of updating changelog

```
prepare_release:
  stage: release
  when: manual
  variables:
    VERSION: minor
    BRANCH: main
  before_script:
    - echo "Preparing release..."
    # Install hatch and install package
    - pip install git+https://github.com/pypa/hatch
    - pip install -e .
  script:
    - hatch version ${VERSION}
    # Get new version
    - export NEXT_VERSION_SPECIFIER=$(hatch version)
    # Generate changelog
    - gitlab-activity --append -o CHANGELOG.md
    - cat CHANGELOG.md
    - git add CHANGELOG.md gitlab_activity/_version.py
    # Configure mail and name of the user who should be visible in the commit history
    - git config --global user.email 'release-bot@gitlab.com'
    - git config --global user.name 'Release Bot'
    - git commit -m 'Bump version and update CHANGELOG.md'
    # Create new tag
    - git tag ${NEXT_VERSION_SPECIFIER} -m "Release ${NEXT_VERSION_SPECIFIER}"
    # Set remote push URL and push to originating branch
    - git remote set-url --push origin "https://${GITLAB_CI_USER}:${GITLAB_CI_TOKEN}@${CI_REPOSITORY_URL#*@}"
    - git push origin HEAD:${CI_COMMIT_REF_NAME} -o ci.skip # Pushes to the same branch as the trigger
    - git push origin ${NEXT_VERSION_SPECIFIER} # Pushes the tag BUT triggers the CI to run tagged jobs
  # Only run on main branch and do not run on tags
  # Because we create tag in this job
  only:
    - main
  except:
    - tags

```

The current project uses [`hatch`](https://github.com/pypa/hatch) as the build system.
As it is a manual job, the maintainer can set the version using `VERSION` variable in
GitLab UI before triggering job. Using that `VERSION` variable, `hatch` bumps version
and sets a new environment variable `NEXT_VERSION_SPECIFIER`.

:::important

We **should** set this environment variable `NEXT_VERSION_SPECIFIER` in the CI job to
the bumped version. `gitlab-activity` reads this environment variable, if set, and emits
the version name in the Changelog. If not, it will emit the dates in the Changelog
header

:::

The command `gitlab-activity --append -o CHANGELOG.md` will update the Changelog since
the last tag until the new one. The rest of the job is to commit the changes and create
a new tag and eventually push them to remote.

The tag commit will trigger a new CI in the current project which will eventually
publish the package to PyPI. Notice that in the current job show above, we add a rule
to skip that job for tags using `except:` keyword to avoid infinite loop.

## Contributors list

`gitlab-activity` outputs the contributors list, if asked, at the end of each tag entry in the changelog file. The list of contributors are estimated in the following way:

- Author of the MR is always a contributor by default
- All the MR's [participants](https://docs.gitlab.com/ee/api/graphql/reference/#mergerequestparticipant) will be added to the contributors list.
- If there are any bot accounts in the participants, they will be removed. Bot accounts are identified based on the config provided by the user and GitLab API marking the user as bot or not. In addition, if there are usernames with "bot" in them, they will be excluded in the list too.

Finally, all the unique contributors from each MR will be added at the end of each MR entry.
