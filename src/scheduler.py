from config import BANKS
from bank_client import initialize_session
from fetcher import uid_retriever, fetch_transactions, fetch_balances
from processor import process_transactions, process_balances


def main():
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
            
if __name__ == "__main__":
    main()