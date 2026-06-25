from config import settings
from mcp.server.fastmcp import FastMCP
from storage import get_session, Transaction
from datetime import datetime
from embedder import add_example
from categorization_agent import run_categorization as trigger_categorization
from queries import query_balances, query_income, query_spending, query_transactions_by_category, query_uncategorized_transactions


mcp = FastMCP("personal_finance_tracker")

@mcp.tool()
def get_balance() -> str:
    """
    Return the latest available balance for every bank account, plus currency totals.

    Queries the most recent ITAV (Instant Total Available) balance snapshot for each
    (bank, currency) pair and aggregates them into per-currency grand totals.

    Returns a plain-text report with two sections:
    - One line per account: "Account: <bank_name> - <currency>: <amount>, retrieved at <YYYY-MM-DD HH:MM>"
    - One summary line per currency that has a non-zero total: "Total amount - <currency>: <amount>"

    Supported currencies are HUF, EUR and USD.  Accounts with a zero aggregate are
    omitted from the totals section.

    Use this tool whenever the user asks about their current balance, net worth,
    how much money they have, or wants an overview of their accounts.
    """
    balances_output: dict[tuple[str, str], tuple[float, datetime]] = {}
    account_outputs: list[str] = []
    total_outputs: list[str] = []

    balances = query_balances()

    for balance in balances:
        balances_output[(balance[0], balance[1])] = (float(balance[2]), balance[3].strftime("%Y-%m-%d %H:%M"))

    for key, value in balances_output.items():
        account_outputs.append(f"Account: {key[0]} - {key[1]}: {value[0]}, retrieved at {value[1]}")

    for currency in settings.currencies:
        total_value = sum(v[0] for k, v in balances_output.items() if k[1] == currency)
        if total_value > 0:
            total_outputs.append(f"Total amount - {currency}: {total_value}")

    final_output: str = "\n".join(account_outputs) + "\n" + "\n".join(total_outputs)

    return final_output
        

@mcp.tool()
def get_spending_summary(date_from: str, date_to: str, categories: list[str] | None = None) -> str:
    """
    Return a spending summary grouped by category and currency for a given date range.

    Only debit (DBIT) transactions are included — credit/income transactions are excluded.
    Amounts are summed per (category, currency) pair and presented as positive values
    representing money spent.

    Args:
        date_from: Start of the period, inclusive. ISO 8601 date string: "YYYY-MM-DD".
        date_to:   End of the period, inclusive. ISO 8601 date string: "YYYY-MM-DD".
        categories: Optional list of category names to filter by. When omitted or None,
                    all categories are returned. Valid category names are:
                    Spending  — "Groceries", "Clothes", "Utilities", "Subscriptions",
                                "Eating out", "Irregular", "Transport", "Sports"
                    Income    — "Salary", "Ingenium", "Other Income"
                    Savings   — "Revolut Spare Change"
                    Transfer  - "Currency Exchange"

    Returns a plain-text report:
        "Starting date: <date_from>\\nEnding date: <date_to>\\n"
        followed by one line per (category, currency) pair:
        "Category: <name> (<currency>) - Spending: <total_amount>"

    Use this tool when the user asks how much they spent in a period, wants a
    breakdown by category, or wants to compare spending across time ranges.
    """
    category_outputs: list[str] = []

    spending_summary = query_spending(date_from=date_from, date_to=date_to, categories=categories)

    category_outputs.append(f"Starting date: {date_from}\nEnding date: {date_to}\n")

    for category in spending_summary:
        category_outputs.append(f"Category: {category[0]} ({category[1]}) - Spending: {float(category[2])}")

    final_output: str = "\n".join(category_outputs)

    return final_output


@mcp.tool()
def get_transactions_by_category(category: str, date_from: str, date_to: str) -> str:
    """
    Return every individual transaction belonging to a specific category within a date range.

    Retrieves all transactions (both debit and credit) whose category matches the
    given value and whose booking_date falls within [date_from, date_to] inclusive.

    Args:
        category:  Exact category name to filter by. Valid values:
                   Spending  — "Groceries", "Clothes", "Utilities", "Subscriptions",
                               "Eating out", "Irregular", "Transport", "Sports"
                   Income    — "Salary", "Ingenium", "Other Income"
                   Savings   — "Revolut Spare Change"
                   Transfer  - "Currency Exchange"
        date_from: Start of the period, inclusive. ISO 8601 date string: "YYYY-MM-DD".
        date_to:   End of the period, inclusive. ISO 8601 date string: "YYYY-MM-DD".

    Returns a plain-text list headed by:
        "Transactions in category <category> between <date_from> and <date_to>:"
    followed by one line per transaction:
        "ID: <full_uuid> | Date: YYYY-MM-DD - <remittance_information> - <currency> <amount>"

    The full transaction UUID returned here can be passed directly to
    recategorize_transaction without any modification.

    Use this tool when the user wants to see the individual transactions behind a
    category total, investigate a specific expense, or review all entries in a group.
    """
    category_output: list[str] = []

    category_transactions = query_transactions_by_category(category=category, date_from=date_from, date_to=date_to)

    category_output.append(
        f"Transactions in category {category} between {date_from} and {date_to}:\n"
        )


    for tr in category_transactions:
        category_output.append(
            f"ID: {tr[0]} | Date: {tr[4].strftime('%Y-%m-%d')} - {tr[3]} - {tr[1]} {tr[2]}"
            )

    final_output: str = "\n".join(category_output)

    return final_output


@mcp.tool()
def recategorize_transaction(transaction_id: str, new_category: str) -> str:
    """
    Change the category of a single transaction and teach the system to remember the pattern.

    Performs two actions atomically:
    1. Updates the transaction's category in the database.
    2. Adds the transaction's remittance_information string as a new categorization
       example (via the vector-embedding learning layer), so similar future transactions
       will automatically receive the correct category.

    Args:
        transaction_id: Full UUID of the transaction to update. Both
                        get_transactions_by_category and get_uncategorized_transactions
                        return the complete UUID, which can be passed here directly.
                        Tip: show the user the transaction details and ask them to confirm
                        before calling this tool, since the change is immediately committed.
        new_category:   The correct category to assign. Must be one of:
                        Spending  — "Groceries", "Clothes", "Utilities", "Subscriptions",
                                    "Eating out", "Irregular", "Transport", "Sports"
                        Income    — "Salary", "Ingenium", "Other Income"
                        Savings   — "Revolut Spare Change"
                        Transfer  - "Currency Exchange"

    Returns a confirmation string on success:
        "Transaction <first_8_chars>... has been recategorized from <old> to <new>"
    Or an error string if the ID is not found:
        "Transaction with <transaction_id> is not found"

    Use this tool when the user identifies a miscategorized transaction and wants to
    correct it. Always confirm the transaction details with the user before calling.
    """
    with get_session() as session:
        tr = session.get(Transaction, transaction_id)
        if tr:
            old_category = tr.category
            tr.category = new_category
            session.commit()

            add_example(
                pattern=tr.remittance_information,
                category=new_category,
                added_by="user"
            )

            return f"Transaction {transaction_id[:8]}... has been recategorized from {old_category} to {new_category}"
        else:
            return f"Transaction with {transaction_id} is not found"
        

@mcp.tool()
def add_categorization_example(pattern: str, new_category: str) -> str:
    """
    Add a remittance pattern as a labelled example to the categorization learning layer.

    Stores the given text pattern with its correct category in the
    categorization_examples table and generates a vector embedding for it.
    The embedding is used by the LLM categorization agent to find similar patterns
    via semantic similarity search, improving automatic categorization of future
    transactions that have similar remittance information.

    This tool is additive-only: it does not modify any existing transaction records.
    Use recategorize_transaction instead when you also want to fix a specific transaction.

    Args:
        pattern:      A representative remittance_information string (the description
                      field on a bank transaction). Should reflect the actual text that
                      appears on statements — e.g. "SPAR BUDAPEST", "Netflix subscription",
                      "Employer payroll transfer". Can be a partial pattern.
        new_category: The category this pattern should map to. Must be one of:
                      Spending  — "Groceries", "Clothes", "Utilities", "Subscriptions",
                                  "Eating out", "Irregular", "Transport", "Sports"
                      Income    — "Salary", "Ingenium", "Other Income"
                      Savings   — "Revolut Spare Change"
                      Transfer  - "Currency Exchange"

    Returns:
        "Pattern '<pattern>' added as an example for category '<new_category>'."

    Use this tool when the user wants to teach the system a new categorization rule
    without targeting a specific past transaction, for example when setting up
    recurring merchant rules or correcting systematic misclassifications.
    """
    add_example(
        pattern=pattern,
        category=new_category,
        added_by="user"
    )   

    return f"Pattern '{pattern}' added as an example for category '{new_category}'."     


@mcp.tool()
def get_uncategorized_transactions() -> str:
    """
    Return all transactions that have not yet been assigned a category.

    Queries for every transaction where the category field is NULL. These are
    transactions that either arrived after the last categorization run or that the
    automatic categorization agent was unable to classify with sufficient confidence.

    Returns a plain-text list headed by "Uncategorized transactions:" followed by
    one line per transaction:
        "ID: <full_uuid> | Date: YYYY-MM-DD | Pattern: <remittance_information> - <currency> <amount>"

    If there are no uncategorized transactions, returns:
        "There are currently no uncategorized transactions"

    Typical workflow after calling this tool:
    1. Review the list with the user.
    2. Call run_categorization to let the LLM agent attempt automatic classification.
    3. For any remaining or incorrectly categorized items, call recategorize_transaction
       with the correct category.
    4. Optionally call add_categorization_example to teach the system for the future.

    Use this tool when the user asks what needs categorizing, wants to review pending
    transactions, or before triggering a manual categorization run.
    """
    uncat_trs_collect: list[str] = []

    uncat_trs = query_uncategorized_transactions()

    uncat_trs_collect.append(f"Uncategorized transactions:\n")

    for tr in uncat_trs:
        uncat_trs_collect.append(f"ID: {tr[0]} | Date: {tr[1].strftime('%Y-%m-%d')} | Pattern: {tr[2]} - {tr[3]} {float(tr[4])}")

    final_output: str = "\n".join(uncat_trs_collect)

    if len(uncat_trs) > 0:
        return final_output
    else:
        return "There are currently no uncategorized transactions"
    
@mcp.tool()
def run_categorization() -> str:
    """
    Trigger the LLM categorization agent to automatically categorize all pending transactions.

    Invokes the categorization pipeline which:
    1. Fetches all transactions where category IS NULL.
    2. For each transaction, performs a semantic similarity search against stored
       categorization examples (via sqlite-vec embeddings) to find the closest matching
       patterns and their known categories.
    3. Passes the transaction's remittance_information together with the retrieved
       examples to Claude as few-shot context.
    4. Writes the LLM-assigned category back to the transaction record.

    Returns:
        "Categorization has been conducted, <N> transactions categorized"  — if any
        transactions were processed.
        "There are currently no uncategorized transactions"  — if nothing needed
        categorizing.

    This tool has no parameters; it always processes all uncategorized transactions
    in a single batch run.

    Use this tool when the user asks to categorize transactions, after new bank data
    has been imported, or as the first step before reviewing uncategorized items.
    Call get_uncategorized_transactions afterwards to verify results and handle any
    transactions the agent could not confidently classify.
    """
    count = trigger_categorization()

    if count > 0:
        return f"Categorization has been conducted, {count} transactions categorized"
    else:
        return "There are currently no uncategorized transactions"

if __name__ == "__main__":
    mcp.run()