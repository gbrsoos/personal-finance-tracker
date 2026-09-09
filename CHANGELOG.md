# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.2] - 2026.09.09

### Added
- `is_topup` column on `transactions`, set by `prepare_transaction()` when `transaction_code` is "TOPUP"
- `query_spending()`, `query_income()`, and `query_transactions_by_category()` now filter out `is_topup` transactions, so card/account top-ups no longer inflate spending, income, or category totals

## [0.4.1] - 2026.09.06

### Fixed
- `deploy_watcher.py` now runs `src/storage.py` during deploy, alongside the existing `alembic upgrade head` step, so newly added categories (e.g. `Internal Transfer` from 0.4.0) are seeded onto already-deployed databases automatically instead of requiring a manual run

## [0.4.0] - 2026.09.06

### Added
- Deterministic internal transfer / currency exchange categorization in `processor.py`: `identify_internal_transfer()` categorizes a transaction as "Currency Exchange" (EXCHANGE transaction code) or "Internal Transfer" (counterparty IBAN/BBAN matches one of your own tracked accounts) at ingestion time, ahead of the AI categorization pass; `get_own_account_identifiers()` collects those account IBANs from `sessions.json`
- `creditor_iban`, `creditor_bban`, `debtor_iban`, `debtor_bban` columns on `transactions`, populated from the Enable Banking payload
- New `Internal Transfer` category (type: transfer)

### Fixed
- Using isort within poetry to handle import sorting and formatting.

## [0.3.2] - 2026.08.03

### Fixed
- `get_date_from()` now applies a 3-day overlap buffer when determining the sync start date, preventing late-posting transactions (e.g. transfers or payments that settle a day or two after being recorded elsewhere) from being silently skipped

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