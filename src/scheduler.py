from config import BANKS
from bank_client import initialize_session
from fetcher import uid_detail_retriever, fetch_transactions, fetch_balances
from processor import process_transactions, process_balances
from categorization_agent import run_categorization
import logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


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

    uid_detail_pairs = uid_detail_retriever()
    all_transactions = fetch_transactions(uid_detail_pairs=uid_detail_pairs)
    all_balances = fetch_balances(uid_detail_pairs=uid_detail_pairs)

    for bank in BANKS:
        for uid_detail_pair in uid_detail_pairs[bank]:
            account_uid = uid_detail_pair["uid"]
            account_detail = uid_detail_pair["detail"]

            process_transactions(
                transaction_list=all_transactions[(bank, account_uid, account_detail)],
                bank_name=bank,
                account_uid=account_uid
            )
            process_balances(
                balance_list=all_balances[(bank, account_uid, account_detail)],
                bank_name=bank,
                account_uid=account_uid,
                account_detail=account_detail
            )

    run_categorization()

if __name__ == "__main__":
    main()
