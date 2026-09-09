import hashlib
import json
import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from config import BANKS, settings
from storage import Balance, Transaction, get_session

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# Transaction branch
## Internal transfer and currency exchange subbranch
def get_own_account_identifiers() -> set[str]:
    """Return the IBANs of every tracked cash account across all configured banks."""
    account_identifiers: set[str] = set()

    with open(settings.sessions_info_path, "r") as f:
        session_info = json.load(f)

    for bank in BANKS:
        for account in session_info[bank]["accounts"]:
            if account["cash_account_type"] == "CACC":
                account_identifiers.add(account["account_id"]["iban"])

    return account_identifiers


def identify_internal_transfer(
    transaction_code: str | None,
    creditor_iban: str | None,
    debtor_iban: str | None,
    creditor_bban: str | None,
    debtor_bban: str | None,
    credit_debit_indicator: str,
    own_accounts: set[str],
) -> str | None:
    """
    Deterministically categorize a transaction as an internal transfer or currency
    exchange based on its transaction code and counterparty account identifiers.

    A transaction is a "Currency Exchange" when its transaction code is EXCHANGE.
    Otherwise it's an "Internal Transfer" when the relevant counterparty account —
    the creditor for an outgoing (DBIT) transaction, the debtor for an incoming
    (CRDT) one — matches one of `own_accounts` by IBAN or BBAN. Returns None when
    neither condition holds.
    """
    own_accounts_bban = {iban[4:] for iban in own_accounts}

    if transaction_code == "EXCHANGE":
        return "Currency Exchange"

    if credit_debit_indicator == "DBIT":
        counterparty_iban, counterparty_bban = creditor_iban, creditor_bban
    elif credit_debit_indicator == "CRDT":
        counterparty_iban, counterparty_bban = debtor_iban, debtor_bban
    else:
        return None

    if counterparty_iban in own_accounts or counterparty_bban in own_accounts_bban:
        return "Internal Transfer"

    return None


## Main (casual) transaction subbranch
def prepare_transaction(transaction: dict, bank_name: str, account_uid: str, own_accounts: set[str]) -> Transaction:
    """
    Parse a raw transaction payload from the Enable Banking API and return an
    unsaved Transaction ORM object ready for insertion.
    """
    # DB elements to be extracted from the nested payload
    amount = Decimal(transaction["transaction_amount"]["amount"].strip('"'))
    currency = transaction["transaction_amount"]["currency"]
    transaction_code = (transaction.get("bank_transaction_code") or {}).get("code")
    remittance_information = ", ".join(transaction["remittance_information"]).lower().replace(" ", "_")
    credit_debit_indicator = transaction["credit_debit_indicator"]
    entry_ref = transaction.get("entry_reference") or str(uuid.uuid4())
    booking_date = date.fromisoformat(transaction["booking_date"]) if transaction["booking_date"] else None
    value_date = date.fromisoformat(transaction["value_date"]) if transaction["value_date"] else None
    creditor_iban = (transaction.get("creditor_account") or {}).get("iban")
    creditor_bban = ((transaction.get("creditor_account") or {}).get("other") or {}).get("identification")
    debtor_iban = (transaction.get("debtor_account") or {}).get("iban")
    debtor_bban = ((transaction.get("debtor_account") or {}).get("other") or {}).get("identification")
    status = transaction["status"]

    # DB elements to be created
    unique_id = hashlib.sha256(
        f"{bank_name}_{account_uid}_{entry_ref}".encode()
    ).hexdigest()
    ingested_at = datetime.now(timezone.utc)

    # Checking category to identify internal transfers (between tracked accounts) deterministically
    category = identify_internal_transfer(
        transaction_code=transaction_code,
        creditor_iban=creditor_iban,
        debtor_iban=debtor_iban,
        creditor_bban=creditor_bban,
        debtor_bban=debtor_bban,
        credit_debit_indicator=credit_debit_indicator,
        own_accounts=own_accounts,
    )

    # Checking if the transaction's transaction_code is TOPUP and populating the boolean accordingly
    is_topup: bool = transaction_code == "TOPUP"

    output = Transaction(
        id=unique_id,
        bank_name=bank_name,
        account_uid=account_uid,
        entry_reference=entry_ref,
        amount=amount,
        currency=currency,
        credit_debit_indicator=credit_debit_indicator,
        booking_date=booking_date,
        value_date=value_date,
        remittance_information=remittance_information,
        transaction_code=transaction_code,
        creditor_iban=creditor_iban,
        creditor_bban=creditor_bban,
        debtor_iban=debtor_iban,
        debtor_bban=debtor_bban,
        status=status,
        is_topup=is_topup,
        category=category,
        ingested_at=ingested_at,
    )

    return output


def save_transaction(transaction: Transaction) -> None:
    """Persist a Transaction to the database, silently skipping duplicates."""
    try:
        with get_session() as session:
            session.add(transaction)
            session.commit()
    except IntegrityError:
            logger.info("Transaction already exists, skipping.")
    except Exception as e:
        logger.error("Failed to save transaction %s: %s", transaction.id, e)


def process_transactions(transaction_list: list[dict], bank_name: str, account_uid: str) -> None:
    """Prepare and save every transaction in the list, logging progress per entry."""
    num_tr = len(transaction_list)

    own_accounts = get_own_account_identifiers()

    for i, tr in enumerate(transaction_list):
        processed_tr = prepare_transaction(tr, bank_name, account_uid, own_accounts=own_accounts)
        save_transaction(processed_tr)
        logger.info("Transaction %d/%d has been processed.", i+1, num_tr)


# Balance branch
def prepare_balance(balance: dict, bank_name: str, account_uid: str, account_name: str | None = None) -> Balance:
    """
    Parse a raw balance payload from the Enable Banking API and return an
    unsaved Balance ORM object ready for insertion.
    """
    #DB elements to be extracted from the nested payload
    amount = Decimal(balance["balance_amount"]["amount"].strip('"'))
    currency = balance["balance_amount"]["currency"]
    balance_type = balance["balance_type"]
    reference_date = date.fromisoformat(balance["reference_date"]) if balance["reference_date"] else None

    # DB elements to be created
    retrieved_at = datetime.now(timezone.utc)


    output = Balance(
        bank_name=bank_name,
        account_uid=account_uid,
        account_name=account_name,
        amount=amount,
        currency=currency,
        balance_type=balance_type,
        reference_date=reference_date,
        retrieved_at=retrieved_at
    )

    return output


def save_balance(balance: Balance) -> None:
    """Persist a Balance snapshot to the database, silently skipping duplicates."""
    try:
        with get_session() as session:
            session.add(balance)
            session.commit()
    except IntegrityError:
            logger.info("Balance instance already exists, skipping.")
    except Exception as e:
            logger.error("Failed to save balance for account %s: %s", balance.account_uid, e)


def process_balances(balance_list: list[dict], bank_name: str, account_uid: str, account_detail: str) -> None:
    """Prepare and save every balance snapshot in the list, logging progress per entry."""
    num_bal = len(balance_list)

    for i, bal in enumerate(balance_list):
        processed_bal = prepare_balance(bal, bank_name, account_uid, account_detail)
        save_balance(processed_bal)
        logger.info("Balance %d/%d has been processed.", i+1, num_bal)


if __name__ == "__main__":
    with open("secrets/sessions.json", "r") as f:
        sessions = json.load(f)

    bank_name = "Revolut"
    account_uid = sessions[bank_name]["accounts"][0]["uid"]
    account_detail = sessions[bank_name]["accounts"][0].get("details")
    file_name = "balances_test.json"

    with open(f"data/{file_name}", "r") as f:
        balance_list = json.load(f)

    process_balances(balance_list=balance_list, bank_name=bank_name, account_uid=account_uid, account_detail=account_detail)
