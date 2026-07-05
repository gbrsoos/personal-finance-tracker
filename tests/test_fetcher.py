from datetime import datetime, timedelta, timezone

from fetcher import get_date_from


def test_get_date_from_empty_database_returns_90_days_ago(db_session):
    expected = (datetime.now(timezone.utc) - timedelta(days=90)).date().isoformat()

    result = get_date_from()

    assert result == expected


def test_get_date_from_future_booking_date_returns_today(db_session, make_transaction):
    future_date = (datetime.now(timezone.utc) + timedelta(days=30)).date()
    db_session.add(make_transaction(booking_date=future_date))
    db_session.commit()

    result = get_date_from()

    assert result == datetime.now(timezone.utc).date().isoformat()


def test_get_date_from_past_booking_date_returns_that_date(db_session, make_transaction):
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).date()
    db_session.add(make_transaction(booking_date=past_date))
    db_session.commit()

    result = get_date_from()

    assert result == past_date.isoformat()


def test_get_date_from_uses_most_recent_of_multiple_transactions(db_session, make_transaction):
    older_date = (datetime.now(timezone.utc) - timedelta(days=20)).date()
    newer_date = (datetime.now(timezone.utc) - timedelta(days=5)).date()
    db_session.add_all([
        make_transaction(booking_date=older_date),
        make_transaction(booking_date=newer_date),
    ])
    db_session.commit()

    result = get_date_from()

    assert result == newer_date.isoformat()
