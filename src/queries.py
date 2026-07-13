from storage import get_session, Balance, Transaction
from sqlalchemy import func
from sqlalchemy.engine import Row
from datetime import date


def query_balances() -> list[Row]:
    with get_session() as session:
        balances = session.query(
            Balance.bank_name, 
            Balance.currency, 
            Balance.amount, 
            Balance.account_name,
            func.max(Balance.retrieved_at)
            ).filter(
                Balance.balance_type == "ITAV"
            ).group_by(Balance.account_uid, Balance.currency, Balance.account_name).all()
        
        return balances


def query_spending(date_from: str, date_to: str, categories=None) -> list[Row]:
    date_from_parsed: date = date.fromisoformat(date_from)
    date_to_parsed: date = date.fromisoformat(date_to)

    with get_session() as session:
        spending_summary = session.query(
            Transaction.category,
            Transaction.currency,
            func.sum(Transaction.amount)
        ).filter(Transaction.credit_debit_indicator == "DBIT"
        ).filter(Transaction.booking_date >= date_from_parsed
        ).filter(Transaction.booking_date <= date_to_parsed
        ).group_by(Transaction.category, Transaction.currency)

        if categories:
            spending_summary = spending_summary.filter(Transaction.category.in_(categories))

        return spending_summary.all()
    

def query_income(date_from: str, date_to: str, categories=None) -> list[Row]:
    date_from_parsed: date = date.fromisoformat(date_from)
    date_to_parsed: date = date.fromisoformat(date_to)

    with get_session() as session:
        income_summary = session.query(
            Transaction.category,
            Transaction.currency,
            func.sum(Transaction.amount)
        ).filter(Transaction.credit_debit_indicator == "CRDT"
        ).filter(Transaction.booking_date >= date_from_parsed
        ).filter(Transaction.booking_date <= date_to_parsed
        ).group_by(Transaction.category, Transaction.currency)

        if categories:
            income_summary = income_summary.filter(Transaction.category.in_(categories))

        return income_summary.all()
    

def query_transactions_by_category(category: str, date_from: str, date_to: str) -> list[Row]:
    date_from_parsed: date = date.fromisoformat(date_from)
    date_to_parsed: date = date.fromisoformat(date_to)

    with get_session() as session:
        category_transactions = session.query(
            Transaction.id,
            Transaction.currency,
            Transaction.amount,
            Transaction.remittance_information,
            Transaction.booking_date,
            Transaction.category
        ).filter(Transaction.booking_date >= date_from_parsed
        ).filter(Transaction.booking_date <= date_to_parsed
        ).filter(Transaction.category == category).all()

        return category_transactions


def query_uncategorized_transactions() -> list[Row]:
    with get_session() as session:
        uncat_trs = session.query(
            Transaction.id,
            Transaction.booking_date,
            Transaction.remittance_information,
            Transaction.currency,
            Transaction.amount
        ).filter(Transaction.category.is_(None)).all()

        return uncat_trs