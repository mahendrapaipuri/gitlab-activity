---
id: config
title: Configuration
---

<!-- ../../../example-configs/README.md -->

# Configuration

This folder contains example config files that can be used to configure
`gitlab-activity`. Using CLI arguments is a cumbersome task, and thus,
`gitlab-activity` supports configuring all the CLI options using a config file.

Currently, `gitlab-activity` supports three different files based on the type of
target project. `gitlab-activity` will check for the following files in the current
working directory in the order of priority to load the configuration.

- `.gitlab-activity.toml`
- `pyproject.toml`
- `package.json`

:::note

If, for example, both `.gitlab-activity.toml` and `pyproject.toml` are found to
have valid configuration, only configuration from `.gitlab-activity.toml` file
will be loaded and used due to its higher priority.

:::

## Configuration using `.gitlab-activity.toml`

An example [configuration file](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/blob/main/example-configs/.gitlab-activity.toml)
can be found in the repository. Globally, this
TOML file has two sections namely, `options` and `activity`.

:::tip

If the file `.gitlab-activity.toml` exists in the directory where the
`gitlab-activity` CLI command will be invoked, it will automatically loaded. If it is
placed elsewhere, users need to pass the path of config file using `--config` CLI option.

:::

All CLI options can be configured within `options` section and repository specific
metadata like the labels used by Issues and MRs, bot users used within the repository
can be configured within `activity` section. Within the `activity` section, users can
define list of bot users under variable `bot_users`. These users will be excluded in
the generated report in the contributors list.

`activity` section has another subsection called `activity.categories` which should be
used to define the labels used for the repository. An excerpt is as follows:

```
[activity.categories]
# Dicts must be inline for linters not to complain
issues = [
  { labels = [ "feature", "feat", "new" ], pre = [ "NEW", "FEAT", "FEATURE" ], description = "New features added" },
  { labels = [ "enhancement", "enhancements" ], pre = [ "ENH", "ENHANCEMENT", "IMPROVE", "IMP" ], description = "Enhancements made" },
  { labels = [ "bug", "bugfix", "bugs" ], pre = [ "FIX", "BUG" ], description = "Bugs fixed" },
  { labels = [ "maintenance", "maint" ], pre = [ "MAINT", "MNT" ], description = "Maintenance and upkeep improvements" },
  { labels = [ "documentation", "docs", "doc" ], pre = [ "DOC", "DOCS" ], description = "Documentation improvements" },
  { labels = [ "deprecation", "deprecate" ], pre = [ "DEPRECATE", "DEPRECATION", "DEP" ], description = "Deprecated features" },
]
# Dicts must be inline for linters not to complain
mrs = [
  { labels = [ "feature", "feat", "new" ], pre = [ "NEW", "FEAT", "FEATURE" ], description = "New features added" },
  { labels = [ "enhancement", "enhancements" ], pre = [ "ENH", "ENHANCEMENT", "IMPROVE", "IMP" ], description = "Enhancements made" },
  { labels = [ "bug", "bugfix", "bugs" ], pre = [ "FIX", "BUG" ], description = "Bugs fixed" },
  { labels = [ "maintenance", "maint" ], pre = [ "MAINT", "MNT" ], description = "Maintenance and upkeep improvements" },
  { labels = [ "documentation", "docs", "doc" ], pre = [ "DOC", "DOCS" ], description = "Documentation improvements" },
  { labels = [ "deprecation", "deprecate" ], pre = [ "DEPRECATE", "DEPRECATION", "DEP" ], description = "Deprecated features" },
]
```

The categories of either `issues` or `merge_requests` should be a list of dicts. Each
dict should have three keys namely:

- `labels`: List of labels the project uses to categorize in issues/MRs
- `pre`: List of prefixes used in the titles of issues/MRs
- `description`: Description that must be emitted in the generated activity report/Changelog

Users can define the categories of labels for issues and MRs separately. This gives
more flexibility to properly categorize the activity in changelogs. If a project uses
same labels for both issues and MRs, users can define just one of
`activity.categories.issues` or `activity.categories.merge_requests`, and the tool
will use the same categories for the other one. This avoids duplicating config.

## Configuration using `pyproject.toml`

Configuration using `pyproject.toml` follows exactly the same pattern as the
configuration through `.gitlab-activity.toml`, albeit, the configuration should go
under section `[tool.gitlab-activity]`. An example [config file](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/blob/main/example-configs/pyproject.toml)
is provided in the repository. This is very convienet for Python based projects where
the configuration can be included in the packages main `pyproject.toml` and avoid
having separate configuration file.

## Configuration using `package.json`

Configuration using `package.json` should go under the key `gitlab-activity`. It
follows same schema as `.gitlab-acivity.toml`, albeit, in JSON format.
A [schema](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/blob/main/gitlab_activity/schema.json)
is available in the repository which will be used to validate the config file. Projects
based on `node` can use this file to include the `gitlab-activity` config.

# Which file should I use?

It depends on the type of project. If your project is based on Python we recommend using
`pyproject.toml` or if your project is based on `node`, we recommend using `package.json`.
If your project is based on other frameworks, you can use `.gitlab-activity.toml` and
place it in the root of the repository.
