# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.1] — 2026-07-26

### Fixed
- Deploy watcher now uses a configurable `POETRY_PATH` setting instead of relying on PATH resolution, fixing deployment failures caused by systemd's restricted environment

## [0.3.0] — 2026-07-26

### Added
- Spending / Income / Transfer toggle above the dashboard transaction list, filtering categories by type
- `query_categories()` in `queries.py` and `/api/categories` endpoint in `dashboard.py`
- Transactions now ordered by booking date descending (most recent first)

### Fixed
- Duplicate `run` key in GitHub Actions CI workflow that was blocking merges
- CI environment variables missing `DEPLOY_CWD`, causing test failures

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