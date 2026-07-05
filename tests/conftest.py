import os

# Required Settings fields must resolve before any project module is imported
# (config.Settings() raises ValidationError otherwise). Real .env values, if
# present, are irrelevant to tests since every external call is mocked.
os.environ.setdefault("ENABLE_BANKING_APP_ID", "test-app-id")
os.environ.setdefault("ENABLE_BANKING_KEY_PATH", "/tmp/test-enable-banking-key.pem")
os.environ.setdefault("REDIRECT_URL", "https://localhost/callback")
os.environ.setdefault("SSL_CERT_PATH", "/tmp/test-cert.pem")
os.environ.setdefault("SSL_KEY_PATH", "/tmp/test-ssl-key.pem")
os.environ.setdefault("SESSIONS_INFO_PATH", "/tmp/test-sessions.json")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import storage
from storage import Balance, Base, Transaction


@pytest.fixture
def in_memory_engine(monkeypatch):
    """
    Fresh in-memory SQLite database with all tables created. Patches
    storage.Session so that every call to storage.get_session() throughout
    the codebase (processor, queries, categorization_agent, fetcher) is
    transparently redirected to this database instead of the real one.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    monkeypatch.setattr(storage, "Session", sessionmaker(bind=engine))

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(in_memory_engine):
    """A session connected to the in-memory engine, for seeding test data."""
    with storage.get_session() as session:
        yield session


@pytest.fixture
def make_transaction():
    """Factory for building Transaction ORM objects with sane defaults."""
    counter = {"n": 0}

    def _make(**overrides) -> Transaction:
        counter["n"] += 1
        defaults = dict(
            id=f"tx-{counter['n']:04d}",
            bank_name="Revolut",
            account_uid="acc-uid-1",
            entry_reference=f"entry-{counter['n']:04d}",
            amount=Decimal("10.00"),
            currency="HUF",
            credit_debit_indicator="DBIT",
            booking_date=date(2026, 1, 15),
            value_date=date(2026, 1, 15),
            remittance_information="lidl_budapest",
            transaction_code="PMNT",
            status="BOOK",
            category=None,
            notes=None,
            ingested_at=datetime.now(timezone.utc),
        )
        defaults.update(overrides)
        return Transaction(**defaults)

    return _make


@pytest.fixture
def make_balance():
    """Factory for building Balance ORM objects with sane defaults."""
    counter = {"n": 0}

    def _make(**overrides) -> Balance:
        counter["n"] += 1
        defaults = dict(
            bank_name="Revolut",
            account_uid="acc-uid-1",
            account_name="Main Account",
            amount=Decimal("1000.00"),
            currency="HUF",
            balance_type="ITAV",
            reference_date=date(2026, 1, 15),
            retrieved_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        )
        defaults.update(overrides)
        return Balance(**defaults)

    return _make


@pytest.fixture
def raw_transaction_payload() -> dict:
    """Realistic Enable Banking transaction payload (Revolut format)."""
    return {
        "entry_reference": "revolut-entry-ref-98765",
        "transaction_amount": {"amount": "12.50", "currency": "HUF"},
        "credit_debit_indicator": "DBIT",
        "booking_date": "2026-06-15",
        "value_date": "2026-06-15",
        "remittance_information": ["Lidl Budapest", "Card payment"],
        "bank_transaction_code": {"code": "PMNT"},
        "status": "BOOK",
    }


@pytest.fixture
def raw_balance_payload() -> dict:
    """Realistic Enable Banking balance payload (Revolut format)."""
    return {
        "balance_amount": {"amount": "1234.56", "currency": "HUF"},
        "balance_type": "ITAV",
        "reference_date": "2026-07-01",
    }
