from config import BANKS
from bank_client import initialize_session
from fetcher import uid_retriever, fetch_transactions, fetch_balances
from processor import process_transactions, process_balances
from categorization_agent import run_categorization


def main() -> None:
    """
    Orchestrate the full data pipeline:
    1. Ensure valid sessions exist for all configured banks.
    2. Fetch transactions and balances for every account.
    3. Persist new records to the database.
    4. Run the LLM categorization agent on any uncategorized transactions.
    """
    for bank, country in BANKS.items():
        initialize_session(name=bank, country=country)

    account_uids = uid_retriever()
    all_transactions = fetch_transactions(account_uids=account_uids)
    all_balances = fetch_balances(account_uids=account_uids)

    for bank in BANKS:
        for i in range(len(account_uids[bank])):
            process_transactions(
                transaction_list=all_transactions[(bank, account_uids[bank][i])],
                bank_name=bank,
                account_uid=account_uids[bank][i]
            )
            process_balances(
                balance_list=all_balances[(bank, account_uids[bank][i])],
                bank_name=bank,
                account_uid=account_uids[bank][i])

    run_categorization()

if __name__ == "__main__":
    main()
