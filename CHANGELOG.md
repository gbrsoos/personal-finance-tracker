# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — 2026-07-13

### Added
- Transaction category displayed in dashboard transaction list
- Account name for named Revolut pockets (e.g. Nyaralas) shown in balance cards
- `deploy_watcher.py` — automatic Pi deployment on new GitHub release tags
- Poetry for dependency management (replaces `requirements.txt`)
- `CLAUDE.md` updated with fetcher architecture and Poetry conventions

### Fixed
- Stale balance rows from old Revolut sessions no longer shown
- Future booking dates no longer cause 422 errors in `get_date_from()`
- `capture_auth_code()` typed correctly with `_AuthCallbackServer`

## [0.1.0] — 2026-07-05

Initial working release. See GitHub release notes for details.