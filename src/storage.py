from contextlib import contextmanager
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy import Numeric, Date, DateTime, PrimaryKeyConstraint, String, create_engine, LargeBinary, event
from decimal import Decimal
from datetime import date, datetime
from config import settings
from typing import Optional
import sqlite_vec


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String, name="transaction_id", primary_key=True)
    bank_name: Mapped[str] = mapped_column(String, nullable=False)
    account_uid: Mapped[str] = mapped_column(String, name="subaccount_id")
    entry_reference: Mapped[str] = mapped_column(String, name="orig_reference_id", nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6))
    currency: Mapped[str] = mapped_column(String)
    credit_debit_indicator: Mapped[str] = mapped_column(String)
    booking_date: Mapped[date] = mapped_column(Date)
    value_date: Mapped[date] = mapped_column(Date, nullable=True)
    # List in raw data, joined to string before storage e.g. ", ".join(remittance_information)
    remittance_information: Mapped[str] = mapped_column(String, name="transa_details")
    transaction_code: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime)


class Balance(Base):
    __tablename__ = "balances"

    bank_name: Mapped[str] = mapped_column(String)
    account_uid: Mapped[str] = mapped_column(String, name="subaccount_id")
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6))
    currency: Mapped[str] = mapped_column(String)
    balance_type: Mapped[str] = mapped_column(String, nullable=True)
    reference_date: Mapped[Optional[date]] = mapped_column(DateTime, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        PrimaryKeyConstraint("subaccount_id", "retrieved_at"),
    )


class Category(Base):
    __tablename__ = "categories"

    category_name: Mapped[str] = mapped_column(String, primary_key=True)
    category_type: Mapped[str] = mapped_column(String, nullable=True)


class CategorizationExample(Base):
    __tablename__ = "categorization_examples"

    remittance_pattern: Mapped[str] = mapped_column(String, primary_key=True)
    correct_category: Mapped[str] = mapped_column(String)
    added_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    embedding: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)


def init_db():
    Base.metadata.create_all(engine)


@contextmanager
def get_session():
    with Session() as session:
        yield session


def seed_categories():
    categories = [
        Category(category_name="Groceries", category_type="spending"),
        Category(category_name="Clothes", category_type="spending"),
        Category(category_name="Utilities", category_type="spending"),
        Category(category_name="Subscriptions", category_type="spending"),
        Category(category_name="Eating out", category_type="spending"),
        Category(category_name="Irregular", category_type="spending"),
        Category(category_name="Salary", category_type="income"),
        Category(category_name="Ingenium", category_type="income"),
        Category(category_name="Other Income", category_type="income"),
        Category(category_name="Revolut Spare Change", category_type="savings"),
    ]
    
    with get_session() as session:
        for category in categories:
            existing = session.get(Category, category.category_name)
            if not existing:
                session.add(category)
        session.commit()

engine = create_engine(settings.database_url)

@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    dbapi_connection.enable_load_extension(True)
    sqlite_vec.load(dbapi_connection)
    dbapi_connection.enable_load_extension(False)

Session = sessionmaker(engine)


if __name__ == "__main__":
    init_db()
    seed_categories()