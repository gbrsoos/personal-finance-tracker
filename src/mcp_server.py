from config import settings
from mcp.server.fastmcp import FastMCP
from storage import get_session, Balance, Transaction
from sqlalchemy import func
from datetime import datetime, date

mcp = FastMCP("personal_finance_tracker")

@mcp.tool()
def get_balance() -> str:
    balances_output: dict[tuple[str, str], tuple[float, datetime]] = {}
    account_outputs: list[str] = []
    total_outputs: list[str] = []

    with get_session() as session:
        balances = session.query(
            Balance.bank_name, 
            Balance.currency, 
            Balance.amount, 
            func.max(Balance.retrieved_at)
            ).filter(
                Balance.balance_type == "ITAV"
            ).group_by(Balance.account_uid, Balance.currency)

        session.expunge_all()

        for balance in balances:
            balances_output[(balance.bank_name, balance.currency)] = (float(balance.amount), balance[3].strftime("%Y-%m-%d %H:%M"))

        for key, value in balances_output.items():
            account_outputs.append(f"Account: {key[0]} - {key[1]}: {value[0]}, retrieved at {value[1]}")

        for currency in settings.currencies:
            total_value = sum(v[0] for k, v in balances_output.items() if k[1] == currency)
            if total_value > 0:
                total_outputs.append(f"Total amount - {currency}: {total_value}")

    final_output: str = "\n".join(account_outputs) + "\n" + "\n".join(total_outputs)

    return final_output
        

@mcp.tool()
def get_spending_summary(date_from: str, date_to: str, categories: list[str] = None) -> str:
    category_outputs: list[str] = []
    date_from_parsed: date = date.fromisoformat(date_from)
    date_to_parsed: date = date.fromisoformat(date_to)

    with get_session() as session:
        all_categories_summary = session.query(
            Transaction.category,
            Transaction.currency,
            func.sum(Transaction.amount)
        ).filter(Transaction.credit_debit_indicator == "DBIT"
        ).filter(Transaction.booking_date >= date_from_parsed
        ).filter(Transaction.booking_date <= date_to_parsed
        ).group_by(Transaction.category, Transaction.currency)

        if categories:
            spending_summary = all_categories_summary.filter(Transaction.category.in_(categories)).all()
        else:
            spending_summary = all_categories_summary.all()

        session.expunge_all()

    category_outputs.append(f"Starting date: {date_from}\nEnding date: {date_to}\n")

    for category in spending_summary:
        category_outputs.append(f"Category: {category.category} ({category.currency}) - Spending: {float(category[2])}")

    final_output: str = "\n".join(category_outputs)

    return final_output


if __name__ == "__main__":
    spending_sum = get_spending_summary(date_from="2025-05-01", date_to="2026-06-30")
    print(spending_sum)
