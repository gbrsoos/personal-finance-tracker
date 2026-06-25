from fastapi import FastAPI
from fastapi.responses import FileResponse
from queries import query_balances, query_spending, query_income, query_transactions_by_category
from sqlalchemy.engine import Row

app = FastAPI()


@app.get("/")
def serve_dashboard():
    return FileResponse("src/dashboard.html")

@app.get("/api/balances")
def get_balances_api() -> list[dict]:
    output: list[dict] = []
    balances: list[Row] = query_balances()

    for balance in balances:
        output.append({
            "bank_name": balance[0],
            "currency": balance[1],
            "amount": float(balance[2]),
            "retrieved_at": balance[3].strftime("%Y-%m-%d %H:%M")
        })

    return output


@app.get("/api/spending")
def get_spending_summary_api(date_from: str, date_to: str, categories=None) -> list[dict]:
    output: list[dict] = []
    spending_summary: list[Row] = query_spending(date_from=date_from, date_to=date_to, categories=categories)

    for spending in spending_summary:
        output.append({
            "category": spending[0],
            "currency": spending[1],
            "amount": float(spending[2])
        })

    return output


@app.get("/api/income")
def get_income_summary_api(date_from: str, date_to: str, categories=None) -> list[dict]:
    output: list[dict] = []
    income_summary: list[Row] = query_income(date_from=date_from, date_to=date_to, categories=categories)

    for income in income_summary:
        output.append({
            "category": income[0],
            "currency": income[1],
            "amount": float(income[2])
        })

    return output


@app.get("/api/transactions")
def get_transactions_by_category_api(category: str, date_from: str, date_to: str) -> list[dict]:
    output: list[dict] = []
    trs_by_cat: list[Row] = query_transactions_by_category(category=category, date_from=date_from, date_to=date_to)

    for tr in trs_by_cat:
        output.append({
            "id": tr[0],
            "currency": tr[1],
            "amount": float(tr[2]),
            "remittance_information":tr[3],
            "booking_date":tr[4].strftime("%Y-%m-%d")
        })

    return output