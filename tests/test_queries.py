from datetime import date, datetime, timezone
from decimal import Decimal

from queries import (
    query_balances,
    query_income,
    query_spending,
    query_transactions_by_category,
    query_uncategorized_transactions,
)


def test_query_balances_returns_only_latest_per_account(db_session, make_balance):
    older = make_balance(
        retrieved_at=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        amount=Decimal("900.00"),
    )
    latest = make_balance(
        retrieved_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        amount=Decimal("1000.00"),
    )
    wrong_type = make_balance(
        balance_type="CLBD",
        retrieved_at=datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        amount=Decimal("999.00"),
    )
    db_session.add_all([older, latest, wrong_type])
    db_session.commit()

    results = query_balances()

    assert len(results) == 1
    assert results[0].amount == Decimal("1000.00")


def test_query_balances_groups_separately_per_account(db_session, make_balance):
    account_a = make_balance(
        account_uid="acc-a",
        retrieved_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        amount=Decimal("100.00"),
    )
    account_b = make_balance(
        account_uid="acc-b",
        retrieved_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        amount=Decimal("200.00"),
    )
    db_session.add_all([account_a, account_b])
    db_session.commit()

    results = query_balances()

    assert len(results) == 2
    assert {row.amount for row in results} == {Decimal("100.00"), Decimal("200.00")}


def test_query_spending_filters_by_date_range_and_indicator(db_session, make_transaction):
    in_range_debit = make_transaction(
        category="Groceries",
        credit_debit_indicator="DBIT",
        booking_date=date(2026, 1, 10),
        amount=Decimal("50.00"),
    )
    in_range_credit = make_transaction(
        category="Salary",
        credit_debit_indicator="CRDT",
        booking_date=date(2026, 1, 12),
        amount=Decimal("500.00"),
    )
    out_of_range_debit = make_transaction(
        category="Groceries",
        credit_debit_indicator="DBIT",
        booking_date=date(2025, 12, 1),
        amount=Decimal("20.00"),
    )
    db_session.add_all([in_range_debit, in_range_credit, out_of_range_debit])
    db_session.commit()

    results = query_spending("2026-01-01", "2026-01-31")

    assert len(results) == 1
    assert results[0].category == "Groceries"
    assert results[0][2] == Decimal("50.00")


def test_query_income_filters_for_credit_transactions(db_session, make_transaction):
    salary = make_transaction(
        category="Salary",
        credit_debit_indicator="CRDT",
        booking_date=date(2026, 1, 5),
        amount=Decimal("1500.00"),
    )
    groceries = make_transaction(
        category="Groceries",
        credit_debit_indicator="DBIT",
        booking_date=date(2026, 1, 6),
        amount=Decimal("30.00"),
    )
    old_salary = make_transaction(
        category="Salary",
        credit_debit_indicator="CRDT",
        booking_date=date(2025, 11, 5),
        amount=Decimal("1400.00"),
    )
    db_session.add_all([salary, groceries, old_salary])
    db_session.commit()

    results = query_income("2026-01-01", "2026-01-31")

    assert len(results) == 1
    assert results[0].category == "Salary"
    assert results[0][2] == Decimal("1500.00")


def test_query_transactions_by_category_returns_matching_rows(db_session, make_transaction):
    match = make_transaction(
        category="Eating out",
        booking_date=date(2026, 2, 10),
        remittance_information="pizza_place",
        amount=Decimal("15.00"),
    )
    wrong_category = make_transaction(
        category="Groceries",
        booking_date=date(2026, 2, 11),
        amount=Decimal("40.00"),
    )
    wrong_date = make_transaction(
        category="Eating out",
        booking_date=date(2026, 3, 1),
        amount=Decimal("22.00"),
    )
    db_session.add_all([match, wrong_category, wrong_date])
    db_session.commit()

    results = query_transactions_by_category("Eating out", "2026-02-01", "2026-02-28")

    assert len(results) == 1
    assert results[0].id == match.id
    assert results[0].remittance_information == "pizza_place"
    assert results[0].amount == Decimal("15.00")


def test_query_uncategorized_transactions_returns_only_null_category(db_session, make_transaction):
    uncategorized = make_transaction(category=None)
    categorized = make_transaction(category="Groceries")
    db_session.add_all([uncategorized, categorized])
    db_session.commit()

    results = query_uncategorized_transactions()

    assert len(results) == 1
    assert results[0].id == uncategorized.id
