import hashlib
from datetime import date
from decimal import Decimal

from processor import prepare_balance, prepare_transaction

BANK_NAME = "Revolut"
ACCOUNT_UID = "acc-uid-1"


def test_prepare_transaction_field_mapping(raw_transaction_payload):
    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID)

    assert tr.bank_name == BANK_NAME
    assert tr.account_uid == ACCOUNT_UID
    assert tr.entry_reference == "revolut-entry-ref-98765"
    assert tr.amount == Decimal("12.50")
    assert tr.currency == "HUF"
    assert tr.credit_debit_indicator == "DBIT"
    assert tr.booking_date == date(2026, 6, 15)
    assert tr.value_date == date(2026, 6, 15)
    assert tr.remittance_information == "lidl_budapest,_card_payment"
    assert tr.transaction_code == "PMNT"
    assert tr.status == "BOOK"
    assert tr.category is None
    assert tr.ingested_at is not None


def test_sha256_hash_is_deterministic(raw_transaction_payload):
    tr1 = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID)
    tr2 = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID)

    expected = hashlib.sha256(
        f"{BANK_NAME}_{ACCOUNT_UID}_revolut-entry-ref-98765".encode()
    ).hexdigest()

    assert tr1.id == tr2.id == expected


def test_prepare_transaction_value_date_none(raw_transaction_payload):
    raw_transaction_payload["value_date"] = None

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID)

    assert tr.value_date is None
    assert tr.booking_date == date(2026, 6, 15)


def test_prepare_transaction_empty_remittance_information(raw_transaction_payload):
    raw_transaction_payload["remittance_information"] = []

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID)

    assert tr.remittance_information == ""


def test_prepare_transaction_amount_is_decimal_not_float(raw_transaction_payload):
    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID)

    assert isinstance(tr.amount, Decimal)
    assert not isinstance(tr.amount, float)
    assert tr.amount == Decimal("12.50")


def test_prepare_balance_field_mapping(raw_balance_payload):
    bal = prepare_balance(raw_balance_payload, BANK_NAME, ACCOUNT_UID, account_name="Main Account")

    assert bal.bank_name == BANK_NAME
    assert bal.account_uid == ACCOUNT_UID
    assert bal.amount == Decimal("1234.56")
    assert bal.currency == "HUF"
    assert bal.balance_type == "ITAV"
    assert bal.reference_date == date(2026, 7, 1)
    assert bal.retrieved_at is not None


def test_prepare_balance_amount_is_decimal(raw_balance_payload):
    bal = prepare_balance(raw_balance_payload, BANK_NAME, ACCOUNT_UID)

    assert isinstance(bal.amount, Decimal)
    assert not isinstance(bal.amount, float)


def test_prepare_balance_account_name_passed_through(raw_balance_payload):
    bal = prepare_balance(raw_balance_payload, BANK_NAME, ACCOUNT_UID, account_name="Revolut HUF Vault")

    assert bal.account_name == "Revolut HUF Vault"


def test_prepare_balance_account_name_defaults_to_none(raw_balance_payload):
    bal = prepare_balance(raw_balance_payload, BANK_NAME, ACCOUNT_UID)

    assert bal.account_name is None
