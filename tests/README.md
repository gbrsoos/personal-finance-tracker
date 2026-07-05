# Tests

```bash
pytest
```

## Layout

- `conftest.py` — fixtures shared across all tests: an in-memory SQLite database (`in_memory_engine`, `db_session`), ORM object factories (`make_transaction`, `make_balance`), and sample raw Enable Banking payloads (`raw_transaction_payload`, `raw_balance_payload`).
- `test_processor.py` — `prepare_transaction()` / `prepare_balance()` field mapping and edge cases.
- `test_queries.py` — read-only query functions in `queries.py`.
- `test_categorization.py` — `update_categories()` / `get_uncategorized_transactions()` in `categorization_agent.py`.
- `test_fetcher.py` — `get_date_from()` in `fetcher.py`.

## Conventions

- Every test runs against an in-memory SQLite database — `data/finance.db` is never touched. `conftest.py` monkeypatches `storage.Session` so any code path calling `get_session()` transparently uses the in-memory DB for the duration of the test.
- No real network calls. Anthropic, OpenAI, and Enable Banking are never hit — `config.Settings()` is satisfied with dummy env vars set in `conftest.py`, and `test_categorization.py` adds an autouse fixture that fails loudly if the real Anthropic client is ever invoked.
- Use the `make_transaction` / `make_balance` fixtures to build ORM rows directly for query tests; use `raw_transaction_payload` / `raw_balance_payload` for processor tests that exercise raw-payload parsing.
