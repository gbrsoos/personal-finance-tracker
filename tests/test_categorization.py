import pytest

import storage
import categorization_agent
from categorization_agent import get_uncategorized_transactions, update_categories
from storage import Transaction


@pytest.fixture(autouse=True)
def block_real_anthropic_calls(monkeypatch):
    """Safety net: fail loudly if any test path ever reaches the real Claude API."""

    def _fail(*args, **kwargs):
        raise AssertionError("Real Anthropic API call attempted in tests")

    monkeypatch.setattr(categorization_agent.client.messages, "create", _fail)


def _fetch(tr_id: str) -> Transaction | None:
    with storage.get_session() as session:
        return session.get(Transaction, tr_id)


def test_update_categories_writes_to_database(db_session, make_transaction):
    tr = make_transaction(category=None)
    db_session.add(tr)
    db_session.commit()
    tr_id = tr.id

    update_categories({tr_id: "Groceries"})

    result = _fetch(tr_id)
    assert result is not None
    assert result.category == "Groceries"


def test_update_categories_does_not_overwrite_already_categorized(db_session, make_transaction):
    tr = make_transaction(category="Groceries")
    db_session.add(tr)
    db_session.commit()
    tr_id = tr.id

    update_categories({tr_id: "Eating out"})

    result = _fetch(tr_id)
    assert result is not None
    assert result.category == "Groceries"


def test_update_categories_ignores_unknown_ids(db_session, make_transaction):
    tr = make_transaction(category=None)
    db_session.add(tr)
    db_session.commit()

    update_categories({"nonexistent-id": "Groceries"})

    result = _fetch(tr.id)
    assert result is not None
    assert result.category is None


def test_get_uncategorized_transactions_returns_only_null_category(db_session, make_transaction):
    uncategorized = make_transaction(category=None)
    categorized = make_transaction(category="Salary")
    db_session.add_all([uncategorized, categorized])
    db_session.commit()

    results = get_uncategorized_transactions()

    assert len(results) == 1
    assert results[0].id == uncategorized.id
    assert results[0].category is None
