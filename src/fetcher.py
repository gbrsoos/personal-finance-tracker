from config import settings, BANKS
import json
from bank_client import API_ORIGIN, jwt_gen
from datetime import datetime, timezone, timedelta
import requests
import logging
from sqlalchemy import func
from storage import get_session, Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def uid_retriever() -> dict[str, list[str]]:
    """
    Read the saved sessions file and return a mapping of bank name →
    list of account UIDs for every configured bank.
    """
    account_uids: dict[str, list[str]] = {}

    with open(settings.sessions_info_path, "r") as f:
        session_info = json.load(f)

    for bank in BANKS.keys():
        account_uids[bank] = []

        for account in range(len(session_info[bank]['accounts'])):
            account_uid = session_info[bank]['accounts'][account]['uid']
            account_uids[bank].append(account_uid)

    return account_uids


def get_date_from() -> str:
    """
    Return the ISO date string to use as the start of the next transaction
    fetch. Uses the most recent booking date already in the database, or
    falls back to 90 days ago if no transactions exist yet.
    """
    with get_session() as session:
        last_date = session.query(func.max(Transaction.booking_date)).scalar()

    if last_date is None:
        return  (datetime.now(timezone.utc) - timedelta(days=90)).date().isoformat()
    else:
        return last_date.isoformat()

def fetch_transactions(account_uids: dict[str, list[str]]) -> dict[tuple[str, str], list[dict]]:
    """
    Fetch all transactions for every account from the Enable Banking API,
    following pagination via continuation keys.

    Returns a dict keyed by (bank_name, account_uid) whose values are lists
    of raw transaction dicts as returned by the API.
    """
    base_headers = jwt_gen()
    all_transactions: dict[tuple[str, str], list[dict]] = {}

    for bank in account_uids:
        for account_uid in account_uids[bank]:
            all_transactions[(bank, account_uid)] = []

            query = {
                "date_from": get_date_from(),
            }
            continuation_key = None
            while True:
                if continuation_key:
                    query["continuation_key"] = continuation_key
                r = requests.get(
                    f"{API_ORIGIN}/accounts/{account_uid}/transactions",
                    params=query,
                    headers=base_headers,
                )
                if r.status_code == 200:
                    resp_data = r.json()
                    all_transactions[(bank, account_uid)].extend(resp_data["transactions"])
                    continuation_key = resp_data.get("continuation_key")
                    if not continuation_key:
                        logger.info("No continuation key. All transactions were fetched")
                        break
                    logger.info("Going to fetch more transactions with continuation key %s", continuation_key)
                else:
                    if r.status_code == 401:
                        error_code = r.json().get("error", "")
                        if error_code == "EXPIRED_SESSION":
                            logger.warning("Session expired for account %s — re-authentication required.", account_uid)
                            break
                        logger.error("Unauthorized for account %s: %s", account_uid, r.text)
                        break
                    else:
                        logger.error("Error response %s: %s", r.status_code, r.text)
                        break

    return all_transactions


def fetch_balances(account_uids: dict[str, list[str]]) -> dict[tuple[str, str], list[dict]]:
    """
    Fetch the current balances for every account from the Enable Banking API.

    Returns a dict keyed by (bank_name, account_uid) whose values are lists
    of raw balance dicts as returned by the API.
    """
    base_headers = jwt_gen()
    all_balances: dict[tuple[str, str], list[dict]] = {}

    for bank in account_uids:
        for account_uid in account_uids[bank]:
            all_balances[(bank, account_uid)] = []

            r = requests.get(f"{API_ORIGIN}/accounts/{account_uid}/balances", headers=base_headers)
            if r.status_code == 200:
                resp_data = r.json()
                all_balances[(bank, account_uid)].extend(resp_data["balances"])
                logger.info("Balance for %s - %s has been retrieved.", bank, account_uid)
            else:
                if r.status_code == 401:
                    error_code = r.json().get("error", "")
                    if error_code == "EXPIRED_SESSION":
                        logger.warning("Session expired for account %s — re-authentication required.", account_uid)
                        break
                    logger.error("Unauthorized for account %s: %s", account_uid, r.text)
                    break
                else:
                    logger.error("Error response %s: %s", r.status_code, r.text)
                    break

    return all_balances


if __name__ == "__main__":
    account_uids = uid_retriever()
    transactions = fetch_transactions(account_uids)
    balances = fetch_balances(account_uids)
    print(transactions)
    print(balances)
