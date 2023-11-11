---
id: cli
title: Command Line Options
---

<!-- ../../../main.md -->

# gitlab-activity

Generate a markdown changelog of GitLab activity within a date window

## Usage

```
Usage: main [OPTIONS] COMMAND [ARGS]...
```

## Options

- `config`:

  - Type: <click.types.Path object at 0x7fbacb9614c0>
  - Default: `.gitlab-activity.toml`
  - Usage: `-c/--config`

  A TOML file that can be used to configure gitlab-activity. All CLI
  flags can be passed using the config file. In addition this file can be used
  to define the labels and bot users that repo/org uses.

  The labels on MRs will be used to categorize them in the generated Changelog.
  List of bot users defined in the config file will be excluded in contributors list

  By default, config file .gitlab-activity.yaml in current directory will be
  used if it exists. The configuration also supports

  - `pyproject.toml` within section `[tool.gitlab-activity]`

  - `package.json` within `gitlab-activity` key

  The order of priority of loading configuration file is as follows:

  - `.gitlab-activity.yaml`

  - `pyproject.toml`

  - `package.json`

  Configuration **will not** be merged from different files. All configuration
  will be loaded from the first file that is found in the current directory.

  If a configuration file is found, the default options will be loaded from the file.

- `print_config`:

  - Type: BOOL
  - Default: `false`
  - Usage: `--print-config`

  Prints current configuration after loading config files to stderr

- `target`:

  - Type: STRING
  - Default: `none`
  - Usage: `-t/--target`

  The GitLab organization/repo for which you want to grab recent activity
  [issues/merge_requests]. Can either be _just_ an organization (e.g., `gitlab-org`),
  or a combination organization and repo (e.g., `gitlab-org/gitlab-docs`).
  If the former, all repositories for that org will be used. If the latter,
  only the specified repository will be used.

  Can also be a GitLab URL to an organization or repo e.g.,
  https://gitlab.com/gitlab-org/gitlab-docs.

  Self hosted gitlab instances are also supported. Ensure that full URL of
  the organization or repository is provided when using self hosted instances.
  In absence of domain in the URL, gitlab.com will be used.

  If None, the org/repo will attempt to be inferred from `git remote -v` in current
  directory.

- `branch`:

  - Type: STRING
  - Default: `main`
  - Usage: `-b/--branch`

  Activity will be filtered by this branch or reference name

- `since`:

  - Type: STRING
  - Default: `none`
  - Usage: `-s/--since`

  Return activity since this date or git reference.
  Can be any string that is parsed with `dateutil.parser.parse`. If None, activity
  since latest tag will be reported.

- `until`:

  - Type: STRING
  - Default: `none`
  - Usage: `-u/--until`

  Return activity until this date or git reference.
  Can be any string that is parsed with `dateutil.parser.parse`. If None, today's
  date will be used.

- `activity`:

  - Type: STRING
  - Default: `['merge_requests']`
  - Usage: `--activity`

  Activity to report. Currently issues and merge_requests are
  supported.

  This option can be passed multiple times, e.g.,

  `gitlab-activity --activity issues --activity merge_requests`

  By default only merge_requests activity will be returned.

- `auth`:

  - Type: STRING
  - Default: `none`
  - Usage: `--auth`

  An authentication token for GitLab. If None, then the environment
  variable `GITLAB_ACCESS_TOKEN` will be tried. If it does not exist
  then attempt to infer the token from `glab auth status -t`.

- `output`:

  - Type: STRING
  - Default: `none`
  - Usage: `-o/--output`

  Write the markdown to a file if desired.

- `append`:

  - Type: BOOL
  - Default: `false`
  - Usage: `--append`

  Whether to append to the existing output file. If this flag is active
  there should be a marker

  <!-- <START NEW CHANGELOG ENTRY> -->

  in the existing changelog file. In the absence of this marker an error will be
  raised.

- `heading_level`:

  - Type: INT
  - Default: `1`
  - Usage: `--heading-level`

  Base heading level to add when generating markdown.
  Useful when including changelog output in an existing document.
  By default, changelog is emitted with one h1 and an h2 heading for each section.
  --heading-level=2 starts at h2, etc.

- `include_opened`:

  - Type: BOOL
  - Default: `false`
  - Usage: `--include-opened`

  Include a list of opened items in the markdown output

- `include_contributors_list`:

  - Type: BOOL
  - Default: `false`
  - Usage: `--include-contributors-list`

  Include a list of contributors at the end of each release log

- `strip_brackets`:

  - Type: BOOL
  - Default: `false`
  - Usage: `--strip-brackets`

  If True, strip any text between brackets at the beginning of the issue/PR
  title. E.g., [MRG], [DOC], etc.

- `all`:

  - Type: BOOL
  - Default: `false`
  - Usage: `--all`

  Whether to include all the GitLab tags

- `cache`:

  - Type: BOOL
  - Default: `false`
  - Usage: `--cache`

  Whether to cache activity data in CSV files. The data files can be
  found at `~/.cache/gitlab-activity-cache` folder organized based on org/repo.

- `categories`:

  - Type: <gitlab_activity.utils.CustomParamType object at 0x7fbaa9a408f0>
  - Default: `none`
  - Usage: `--categories`

  Activity categories

- `bot_users`:

  - Type: <gitlab_activity.utils.CustomParamType object at 0x7fbaa9a408f0>
  - Default: `none`
  - Usage: `--bot-users`

  List of bot users

- `help`:

  - Type: BOOL
  - Default: `false`
  - Usage: `--help`

  Show this message and exit.

## CLI Help

```
Usage: main [OPTIONS] COMMAND [ARGS]...

  Generate a markdown changelog of GitLab activity within a date window

Options:
  -c, --config <str>           A TOML file that can be used to configure
                               gitlab-activity. All CLI flags can be passed
                               using the config file. In addition this file
                               can be used to define the labels and bot users
                               that repo/org uses.

                               The labels on MRs will be used to categorize
                               them in the generated Changelog. List of bot
                               users defined in the config file will be
                               excluded in contributors list

                               By default, config file .gitlab-activity.yaml
                               in current directory will be used if it exists.
                               The configuration also supports

                               - `pyproject.toml` within section
                               `[tool.gitlab-activity]`

                               - `package.json` within `gitlab-activity` key

                               The order of priority of loading configuration
                               file is as follows:

                               - `.gitlab-activity.yaml`

                               - `pyproject.toml`

                               - `package.json`

                               Configuration **will not** be merged from
                               different files. All configuration will be
                               loaded from the first file that is found in the
                               current directory.

                               If a configuration file is found, the default
                               options will be loaded from the file.
                               [default: .gitlab-activity.toml]
  --print-config               Prints current configuration after loading
                               config files to stderr
  -t, --target <str>           The GitLab organization/repo for which you want
                               to grab recent activity
                               [issues/merge_requests]. Can either be _just_
                               an organization (e.g., `gitlab-org`), or a
                               combination organization and repo (e.g.,
                               `gitlab-org/gitlab-docs`). If the former, all
                               repositories for that org will be used. If the
                               latter, only the specified repository will be
                               used.

                               Can also be a GitLab URL to an organization or
                               repo e.g., https://gitlab.com/gitlab-
                               org/gitlab-docs.

                               Self hosted gitlab instances are also
                               supported. Ensure that full URL of the
                               organization or repository is provided when
                               using self hosted instances. In absence of
                               domain in the URL, gitlab.com will be used.

                               If None, the org/repo will attempt to be
                               inferred from `git remote -v` in current
                               directory.
  -b, --branch <str>           Activity will be filtered by this branch or
                               reference name  [default: main]
  -s, --since <str>            Return activity since this date or git
                               reference. Can be any string that is parsed
                               with `dateutil.parser.parse`. If None, activity
                               since latest tag will be reported.
  -u, --until <str>            Return activity until this date or git
                               reference. Can be any string that is parsed
                               with `dateutil.parser.parse`. If None, today's
                               date will be used.
  --activity <str>             Activity to report. Currently issues and
                               merge_requests are supported.

                               This option can be passed multiple times, e.g.,

                               `gitlab-activity --activity issues --activity
                               merge_requests`

                               By default only merge_requests activity will be
                               returned.  [default: merge_requests]
  --auth <str>                 An authentication token for GitLab. If None,
                               then the environment variable
                               `GITLAB_ACCESS_TOKEN` will be tried. If it does
                               not exist then attempt to infer the token from
                               `glab auth status -t`.
  -o, --output <str>           Write the markdown to a file if desired.
  --append                     Whether to append to the existing output file.
                               If this flag is active there should be a marker

                               <!-- <START NEW CHANGELOG ENTRY> -->

                               in the existing changelog file. In the absence
                               of this marker an error will be raised.
  --heading-level <int>        Base heading level to add when generating
                               markdown. Useful when including changelog
                               output in an existing document. By default,
                               changelog is emitted with one h1 and an h2
                               heading for each section. --heading-level=2
                               starts at h2, etc.  [default: 1]
  --include-opened             Include a list of opened items in the markdown
                               output
  --include-contributors-list  Include a list of contributors at the end of
                               each release log
  --strip-brackets             If True, strip any text between brackets at the
                               beginning of the issue/PR title. E.g., [MRG],
                               [DOC], etc.
  --all                        Whether to include all the GitLab tags
  --cache                      Whether to cache activity data in CSV files.
                               The data files can be found at
                               `~/.cache/gitlab-activity-cache` folder
                               organized based on org/repo.
  --help                       Show this message and exit.
```
