# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

## Unreleased (2025-02-08)

([Full Changelog](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/compare/7494706b954459aa5d1da15d2fbcb920653cba31...2dccb2994b3a48d3966dc4e72399f8a7ca28e58a?from_project_id=51534402&straight=false))

### Maintenance and upkeep improvements

- refactor: Verify auth token before using it [!24](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/24) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### [Contributors to this release](https://mahendrapaipuri.gitlab.io/gitlab-activity/usage#contributors-list)

[@mahendrapaipuri](https://gitlab.com/mahendrapaipuri)

<!-- <END NEW CHANGELOG ENTRY> -->

## 0.1.3 (2024-11-04)

([Full Changelog](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/compare/ce998f5c653ee34eaf4491fbe073f95ff2da5620...086a104419eaf53861c346799b3423fc8e0e33f7?from_project_id=51534402&straight=false))

### Bugs fixed

- fix: Encode URL before passing to requests [!23](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/23) ([@vectrovectro](https://gitlab.com/vectrovectro), [@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- refactor: Use auth instead of headers for requests auth [!22](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/22) ([@vectrovectro](https://gitlab.com/vectrovectro), [@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### Maintenance and upkeep improvements

- refactor: Use auth instead of headers for requests auth [!22](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/22) ([@vectrovectro](https://gitlab.com/vectrovectro), [@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### [Contributors to this release](https://mahendrapaipuri.gitlab.io/gitlab-activity/usage#contributors-list)

[@vectrovectro](https://gitlab.com/vectrovectro) | [@mahendrapaipuri](https://gitlab.com/mahendrapaipuri)

## 0.1.2 (2024-09-16)

([Full Changelog](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/compare/368a6ca67022722d8ab4146ae09cd8af2afe77db...5b5780b9fafd3285a721d3303b8c5069afc186de?from_project_id=51534402&straight=false))

### Bugs fixed

- Ensure target URL is conserved in `generate_all_activity_md` [!21](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/21) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### [Contributors to this release](https://mahendrapaipuri.gitlab.io/gitlab-activity/usage#contributors-list)

[@mahendrapaipuri](https://gitlab.com/mahendrapaipuri)

## 0.1.1 (2024-09-15)

([Full Changelog](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/compare/6b6d4d9b241e3819aad78245a7ef562a5710b547...90910e1e55927baf8268e8421c453b6737b1a913?from_project_id=51534402&straight=false))

### New features added

- Update Changelog for after each MR event [!18](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/18) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### Bugs fixed

- Do not overwrite target URL [!19](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/19) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### Documentation improvements

- Bump docusaurus to v3 [!20](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/20) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Add CLI options to documentation [!17](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/17) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### [Contributors to this release](https://mahendrapaipuri.gitlab.io/gitlab-activity/usage#contributors-list)

[@mahendrapaipuri](https://gitlab.com/mahendrapaipuri)

## 0.1.0 (2023-11-02)

([Full Changelog](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/compare/6c710c92265819a8a2d1a59317b9c7e9d0d47fe7...fcc20006f29d94bbe20cbb139a07ff117c9fa566?from_project_id=51534402&straight=false))

### New features added

- Add release workflows in CI and get first and last commits when no tags found [!12](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/12) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Add source code [!1](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/1) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### Enhancements made

- Add example configs [!8](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/8) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Change vars & opts names for consistency [!7](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/7) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Improve getting latest tags of local repos [!5](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/5) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Look for auth token from CI vars [!4](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/4) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Get created and also merged/closed activity [!3](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/3) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Improve API and grouping logic [!2](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/2) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### Build changes

- Drop support for Python 3.12 [!16](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/16) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### CI changes

- Fixes in CI and docs [!13](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/13) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Add release workflows in CI and get first and last commits when no tags found [!12](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/12) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Add CI YAML file for testing [!10](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/10) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### Maintenance and upkeep improvements

- Change vars & opts names for consistency [!7](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/7) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Improve getting latest tags of local repos [!5](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/5) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Improve API and grouping logic [!2](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/2) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### Documentation improvements

- Add sphinx API docs [!14](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/14) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Fixes in CI and docs [!13](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/13) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Add docs [!11](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/11) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Add example configs [!8](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/8) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### Unlabelled Merged MRs

- Add new cli tests [!15](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/15) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Add more tests [!9](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/9) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))
- Add tests [!6](https://gitlab.com/mahendrapaipuri/gitlab-activity/-/merge_requests/6) ([@mahendrapaipuri](https://gitlab.com/mahendrapaipuri))

### [Contributors to this release](https://mahendrapaipuri.gitlab.io/gitlab-activity/usage#contributors-list)

[@mahendrapaipuri](https://gitlab.com/mahendrapaipuri)
