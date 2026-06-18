from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy import Numeric, Date, DateTime, PrimaryKeyConstraint, String, create_engine
from decimal import Decimal
from datetime import date, datetime
from config import settings

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
    value_date: Mapped[date] = mapped_column(Date)
    # List in raw data, joined to string before storage e.g. ", ".join(remittance_information)
    remittance_information: Mapped[str] = mapped_column(String, name="transa_details")
    transaction_code: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime)

class Balances(Base):
    __tablename__ = "balances"

    account_uid: Mapped[str] = mapped_column(String, name="subaccount_id")
    bank_name: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6))
    currency: Mapped[str] = mapped_column(String)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        PrimaryKeyConstraint("subaccount_id", "retrieved_at"),
    )

engine = create_engine(settings.database_url)
Session = sessionmaker(engine)

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    with Session() as session:
        yield session

if __name__ == "__main__":
    init_db()