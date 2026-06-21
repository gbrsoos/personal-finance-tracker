from decimal import Decimal
from storage import Transaction, Balance, get_session
import hashlib
import uuid
from datetime import date, datetime, timezone
from sqlalchemy.exc import IntegrityError
import logging
import json
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# Transaction branch
def prepare_transaction(transaction: dict, bank_name: str, account_uid: str) -> Transaction:
    #DB elements to be extracted from the nested payload
    amount = Decimal(transaction["transaction_amount"]["amount"].strip('"'))
    currency = transaction["transaction_amount"]["currency"]
    transaction_code = (transaction.get("bank_transaction_code") or {}).get("code")
    remittance_information = ", ".join(transaction["remittance_information"]).lower().replace(" ", "_")
    entry_ref = transaction.get("entry_reference") or str(uuid.uuid4())
    booking_date = date.fromisoformat(transaction["booking_date"]) if transaction["booking_date"] else None
    value_date = date.fromisoformat(transaction["value_date"]) if transaction["value_date"] else None

    # DB elements to be created
    unique_id = hashlib.sha256(
    f"{bank_name}_{account_uid}_{entry_ref}".encode()
    ).hexdigest()
    ingested_at = datetime.now(timezone.utc)
    category = None

    output = Transaction(
        id=unique_id,
        bank_name=bank_name,
        account_uid=account_uid,
        entry_reference=entry_ref,
        amount=amount,
        currency=currency,
        credit_debit_indicator=transaction["credit_debit_indicator"],
        booking_date=booking_date,
        value_date=value_date,
        remittance_information=remittance_information,
        transaction_code=transaction_code,
        status=transaction["status"],
        category=category,
        ingested_at=ingested_at,
    )

    return output


def save_transaction(transaction: Transaction):
    try:
        with get_session() as session:
            session.add(transaction)
            session.commit()
    except IntegrityError:
            logger.info("Transaction already exists, skipping.")
    except Exception as e:
        logger.error("Failed to save transaction %s: %s", transaction.id, e)


def process_transactions(transaction_list: list, bank_name: str, account_uid: str):
    num_tr = len(transaction_list)

    for i, tr in enumerate(transaction_list):
        processed_tr = prepare_transaction(tr, bank_name, account_uid)
        save_transaction(processed_tr)
        logger.info("Transaction %d/%d has been processed.", i+1, num_tr)


# Balance branch
def prepare_balance(balance: dict, bank_name: str, account_uid: str) -> Balance:
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
        amount=amount,
        currency=currency,
        balance_type=balance_type,
        reference_date=reference_date,
        retrieved_at=retrieved_at
    )

    return output


def save_balance(balance: Balance):
    try:
        with get_session() as session:
            session.add(balance)
            session.commit()
    except IntegrityError:
            logger.info("Balance instance already exists, skipping.")
    except Exception as e:
            logger.error("Failed to save balance for account %s: %s", balance.account_uid, e)


def process_balances(balance_list: list, bank_name: str, account_uid: str):
    num_tr = len(balance_list)

    for i, bal in enumerate(balance_list):
        processed_bal = prepare_balance(bal, bank_name, account_uid)
        save_balance(processed_bal)
        logger.info("Balance %d/%d has been processed.", i+1, num_tr)


""" if __name__ == "__main__":
    with open("secrets/sessions.json", "r") as f:
        sessions = json.load(f)

    bank_name = "Revolut"
    account_uid = sessions[bank_name]["accounts"][0]["uid"]
    file_name = "transactions_revolut_huf.json"

    with open(f"data/{file_name}", "r") as f:
        transaction_list = json.load(f)

    process_transactions(transaction_list=transaction_list, bank_name=bank_name, account_uid=account_uid) """

if __name__ == "__main__":
    with open("secrets/sessions.json", "r") as f:
        sessions = json.load(f)

    bank_name = "Revolut"
    account_uid = sessions[bank_name]["accounts"][0]["uid"]
    file_name = "balances_test.json"

    with open(f"data/{file_name}", "r") as f:
        balance_list = json.load(f)

    process_balances(balance_list=balance_list, bank_name=bank_name, account_uid=account_uid)