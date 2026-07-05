# CLAUDE.md — Personal Finance Tracker

This file provides context for Claude Code when working on this project.

## Project Overview

A self-hosted personal finance tracker that:
- Connects to European bank accounts via PSD2 open banking (Enable Banking API)
- Automatically categorizes transactions using Claude AI (Anthropic API)
- Uses OpenAI `text-embedding-3-small` + `sqlite-vec` for semantic similarity search on categorization examples
- Exposes data via a FastMCP server (Claude desktop interface) and a FastAPI read-only web dashboard
- Runs on a Raspberry Pi Argon with daily cron sync

## Architecture

```
src/
├── config.py                 # Pydantic BaseSettings — all env vars loaded here
├── bank_client.py            # Enable Banking OAuth flow + session management
├── fetcher.py                # Fetches transactions/balances from Enable Banking API
├── processor.py              # Normalizes raw API payloads → SQLAlchemy ORM objects
├── storage.py                # SQLAlchemy models (Transaction, Balance, Category, CategorizationExample)
├── categorization_agent.py   # Claude API categorization pipeline
├── embedder.py               # OpenAI embeddings + sqlite-vec similarity search
├── queries.py                # Shared read-only DB query functions (used by MCP + dashboard)
├── scheduler.py              # Orchestrates full pipeline: fetch → process → categorize
├── mcp_server.py             # FastMCP server exposing 7 tools to Claude desktop
├── dashboard.py              # FastAPI backend serving read-only dashboard
├── dashboard.html            # Single-file frontend (Chart.js, dark Revolut-style)
└── prompts/
    └── categorization_system_prompt.txt
```

## Key Design Decisions

- **SQLite** for storage (via SQLAlchemy ORM). Schema changes go through **Alembic** migrations — never `DROP TABLE`.
- **`sessions.json`** in `secrets/` stores Enable Banking OAuth sessions (one entry per bank).
- **`BANKS`** dict in `config.py` (not `.env`) defines which banks to sync: `{"Erste Bank": "HU", "Revolut": "HU"}`.
- **SHA256 hash** of `(bank_name, account_uid, entry_reference)` is the transaction primary key — deduplication is idempotent.
- **`sqlite-vec`** extension must be loaded via SQLAlchemy event listener (see `storage.py`) before any vector queries.
- **`render_as_batch=True`** is set in `migrations/env.py` — required for SQLite column alterations.
- All **file paths** in `.env` must be absolute when running via Claude desktop MCP or cron.

## Database Schema

### `transactions`
| Column | Type | Notes |
|--------|------|-------|
| transaction_id | VARCHAR PK | SHA256 hash |
| bank_name | VARCHAR | "Erste Bank" / "Revolut" |
| subaccount_id | VARCHAR | Enable Banking account UID |
| orig_reference_id | VARCHAR | Raw bank reference |
| amount | NUMERIC(20,6) | Always positive |
| currency | VARCHAR | "HUF" / "EUR" / "USD" |
| credit_debit_indicator | VARCHAR | "CRDT" or "DBIT" |
| booking_date | DATE | |
| value_date | DATE nullable | |
| transa_details | VARCHAR | remittance_information joined |
| transaction_code | VARCHAR nullable | |
| status | VARCHAR nullable | "BOOK" / "PDNG" |
| category | VARCHAR nullable | Filled by categorization agent |
| notes | VARCHAR nullable | Manual notes |
| ingested_at | DATETIME | UTC |

### `balances`
Composite PK: `(subaccount_id, retrieved_at)`

### `categories`
PK: `category_name`. Seeded by `storage.seed_categories()`.

### `categorization_examples`
PK: `remittance_pattern`. Includes `embedding` (LargeBinary) for sqlite-vec.

## Running the Project

```bash
# Activate environment
conda activate finance-tracker  # or: source venv/bin/activate

# Run from project root with PYTHONPATH set
PYTHONPATH=src python src/scheduler.py
PYTHONPATH=src uvicorn src.dashboard:app --port 8080
PYTHONPATH=src alembic upgrade head
```

## Environment Variables

All defined in `config.py` as Pydantic fields. See `.env.example` for the full list.
Key vars: `ENABLE_BANKING_APP_ID`, `ENABLE_BANKING_KEY_PATH`, `DATABASE_URL`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SESSIONS_INFO_PATH`, `CURRENCIES`.

## Testing Conventions

- Tests live in `tests/` at the project root
- Use `pytest`
- Use an **in-memory SQLite database** for all DB tests — never touch the real `data/finance.db`
- Mock all external API calls (Enable Banking, Anthropic, OpenAI) — never make real network calls in tests
- Import modules with `sys.path.insert(0, 'src')` or configure `pytest` with `pythonpath = src` in `pyproject.toml`

## What NOT to Do

- Never `DROP TABLE` in code — use Alembic migrations
- Never commit to `secrets/`, `data/`, or `.env`
- Never hardcode file paths — use `Path(__file__)` or settings
- Never call real APIs in tests
- Never use `Float` for monetary amounts — always `Numeric`/`Decimal`
- Never print to stdout in MCP server code — it corrupts the stdio protocol; use `logging` to stderr

## Categories

```
Spending:  Groceries, Clothes, Utilities, Subscriptions, Eating out, Transport, Sports, Irregular
Income:    Salary, Ingenium, Other Income
Savings:   Revolut Spare Change
Transfer:  Currency Exchange
```