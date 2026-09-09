import hashlib
import json
from datetime import date
from decimal import Decimal

from config import settings
from processor import (
    get_own_account_identifiers,
    identify_internal_transfer,
    prepare_balance,
    prepare_transaction,
)

BANK_NAME = "Revolut"
ACCOUNT_UID = "acc-uid-1"
NO_OWN_ACCOUNTS: set[str] = set()


def test_prepare_transaction_field_mapping(raw_transaction_payload):
    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=NO_OWN_ACCOUNTS)

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
    assert tr.is_topup is False
    assert tr.category is None
    assert tr.creditor_iban is None
    assert tr.creditor_bban is None
    assert tr.debtor_iban is None
    assert tr.debtor_bban is None
    assert tr.ingested_at is not None


def test_sha256_hash_is_deterministic(raw_transaction_payload):
    tr1 = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=NO_OWN_ACCOUNTS)
    tr2 = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=NO_OWN_ACCOUNTS)

    expected = hashlib.sha256(
        f"{BANK_NAME}_{ACCOUNT_UID}_revolut-entry-ref-98765".encode()
    ).hexdigest()

    assert tr1.id == tr2.id == expected


def test_prepare_transaction_value_date_none(raw_transaction_payload):
    raw_transaction_payload["value_date"] = None

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=NO_OWN_ACCOUNTS)

    assert tr.value_date is None
    assert tr.booking_date == date(2026, 6, 15)


def test_prepare_transaction_empty_remittance_information(raw_transaction_payload):
    raw_transaction_payload["remittance_information"] = []

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=NO_OWN_ACCOUNTS)

    assert tr.remittance_information == ""


def test_prepare_transaction_amount_is_decimal_not_float(raw_transaction_payload):
    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=NO_OWN_ACCOUNTS)

    assert isinstance(tr.amount, Decimal)
    assert not isinstance(tr.amount, float)
    assert tr.amount == Decimal("12.50")


def test_prepare_transaction_extracts_creditor_iban(raw_transaction_payload, own_accounts):
    raw_transaction_payload["creditor_account"] = {"iban": "HU00000000000000000000000000"}

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=own_accounts)

    assert tr.creditor_iban == "HU00000000000000000000000000"
    assert tr.creditor_bban is None


def test_prepare_transaction_extracts_creditor_bban_when_no_iban(raw_transaction_payload, own_accounts):
    raw_transaction_payload["creditor_account"] = {"other": {"identification": "11702016111110180000000"}}

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=own_accounts)

    assert tr.creditor_iban is None
    assert tr.creditor_bban == "11702016111110180000000"


def test_prepare_transaction_extracts_debtor_iban_and_bban(raw_transaction_payload, own_accounts):
    raw_transaction_payload["credit_debit_indicator"] = "CRDT"
    raw_transaction_payload["debtor_account"] = {
        "iban": "HU00000000000000000000000001",
        "other": {"identification": "some-bban"},
    }

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=own_accounts)

    assert tr.debtor_iban == "HU00000000000000000000000001"
    assert tr.debtor_bban == "some-bban"


def test_prepare_transaction_marks_internal_transfer_on_dbit_creditor_match(raw_transaction_payload, own_accounts):
    raw_transaction_payload["credit_debit_indicator"] = "DBIT"
    raw_transaction_payload["creditor_account"] = {"iban": "HU12117020161111101800000000"}

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=own_accounts)

    assert tr.category == "Internal Transfer"


def test_prepare_transaction_marks_currency_exchange_regardless_of_accounts(raw_transaction_payload):
    raw_transaction_payload["bank_transaction_code"] = {"code": "EXCHANGE"}

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=NO_OWN_ACCOUNTS)

    assert tr.category == "Currency Exchange"


def test_prepare_transaction_leaves_category_none_when_no_match(raw_transaction_payload, own_accounts):
    raw_transaction_payload["creditor_account"] = {"iban": "HU99999999999999999999999999"}

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=own_accounts)

    assert tr.category is None


def test_prepare_transaction_marks_is_topup_for_topup_code(raw_transaction_payload):
    raw_transaction_payload["bank_transaction_code"] = {"code": "TOPUP"}

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=NO_OWN_ACCOUNTS)

    assert tr.is_topup is True
    assert tr.category is None


def test_prepare_transaction_is_topup_false_for_non_topup_code(raw_transaction_payload):
    raw_transaction_payload["bank_transaction_code"] = {"code": "CARD_PAYMENT"}

    tr = prepare_transaction(raw_transaction_payload, BANK_NAME, ACCOUNT_UID, own_accounts=NO_OWN_ACCOUNTS)

    assert tr.is_topup is False


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


class TestIdentifyInternalTransfer:
    """Unit tests for the pure classification logic behind internal-transfer detection."""

    def test_exchange_code_takes_priority_over_everything(self, own_accounts):
        result = identify_internal_transfer(
            transaction_code="EXCHANGE",
            creditor_iban=None,
            debtor_iban=None,
            creditor_bban=None,
            debtor_bban=None,
            credit_debit_indicator="DBIT",
            own_accounts=own_accounts,
        )

        assert result == "Currency Exchange"

    def test_dbit_with_creditor_iban_in_own_accounts(self, own_accounts):
        result = identify_internal_transfer(
            transaction_code="PMNT",
            creditor_iban="HU12117020161111101800000000",
            debtor_iban=None,
            creditor_bban=None,
            debtor_bban=None,
            credit_debit_indicator="DBIT",
            own_accounts=own_accounts,
        )

        assert result == "Internal Transfer"

    def test_dbit_with_creditor_bban_in_own_accounts(self, own_accounts):
        # BBAN is the IBAN with the 4-char country/check-digit prefix stripped.
        bban = "HU12117020161111101800000000"[4:]

        result = identify_internal_transfer(
            transaction_code="PMNT",
            creditor_iban=None,
            debtor_iban=None,
            creditor_bban=bban,
            debtor_bban=None,
            credit_debit_indicator="DBIT",
            own_accounts=own_accounts,
        )

        assert result == "Internal Transfer"

    def test_dbit_with_creditor_not_in_own_accounts_returns_none(self, own_accounts):
        result = identify_internal_transfer(
            transaction_code="PMNT",
            creditor_iban="HU99999999999999999999999999",
            debtor_iban=None,
            creditor_bban=None,
            debtor_bban=None,
            credit_debit_indicator="DBIT",
            own_accounts=own_accounts,
        )

        assert result is None

    def test_dbit_with_no_creditor_info_returns_none(self, own_accounts):
        result = identify_internal_transfer(
            transaction_code="PMNT",
            creditor_iban=None,
            debtor_iban=None,
            creditor_bban=None,
            debtor_bban=None,
            credit_debit_indicator="DBIT",
            own_accounts=own_accounts,
        )

        assert result is None

    def test_crdt_with_debtor_iban_in_own_accounts(self, own_accounts):
        result = identify_internal_transfer(
            transaction_code="PMNT",
            creditor_iban=None,
            debtor_iban="HU34117020161111101800000001",
            creditor_bban=None,
            debtor_bban=None,
            credit_debit_indicator="CRDT",
            own_accounts=own_accounts,
        )

        assert result == "Internal Transfer"

    def test_crdt_with_debtor_bban_in_own_accounts(self, own_accounts):
        bban = "HU34117020161111101800000001"[4:]

        result = identify_internal_transfer(
            transaction_code="PMNT",
            creditor_iban=None,
            debtor_iban=None,
            creditor_bban=None,
            debtor_bban=bban,
            credit_debit_indicator="CRDT",
            own_accounts=own_accounts,
        )

        assert result == "Internal Transfer"

    def test_crdt_with_debtor_not_in_own_accounts_returns_none(self, own_accounts):
        result = identify_internal_transfer(
            transaction_code="PMNT",
            creditor_iban=None,
            debtor_iban="HU99999999999999999999999999",
            creditor_bban=None,
            debtor_bban=None,
            credit_debit_indicator="CRDT",
            own_accounts=own_accounts,
        )

        assert result is None

    def test_crdt_with_no_debtor_info_returns_none(self, own_accounts):
        result = identify_internal_transfer(
            transaction_code="PMNT",
            creditor_iban=None,
            debtor_iban=None,
            creditor_bban=None,
            debtor_bban=None,
            credit_debit_indicator="CRDT",
            own_accounts=own_accounts,
        )

        assert result is None

    def test_unrecognized_credit_debit_indicator_returns_none(self, own_accounts):
        result = identify_internal_transfer(
            transaction_code="PMNT",
            creditor_iban="HU12117020161111101800000000",
            debtor_iban=None,
            creditor_bban=None,
            debtor_bban=None,
            credit_debit_indicator="UNKNOWN",
            own_accounts=own_accounts,
        )

        assert result is None

    def test_empty_own_accounts_never_matches(self):
        result = identify_internal_transfer(
            transaction_code="PMNT",
            creditor_iban="HU12117020161111101800000000",
            debtor_iban=None,
            creditor_bban=None,
            debtor_bban=None,
            credit_debit_indicator="DBIT",
            own_accounts=set(),
        )

        assert result is None


class TestGetOwnAccountIdentifiers:
    """Unit tests for reading own CACC account IBANs out of sessions.json."""

    def test_returns_only_cacc_account_ibans(self, tmp_path, monkeypatch):
        sessions_data = {
            "Erste Bank": {
                "accounts": [
                    {"cash_account_type": "CACC", "account_id": {"iban": "HU111111111111111111111111"}},
                    {"cash_account_type": "SVGS", "account_id": {"iban": "HU222222222222222222222222"}},
                ]
            },
            "Revolut": {
                "accounts": [
                    {"cash_account_type": "CACC", "account_id": {"iban": "HU333333333333333333333333"}},
                ]
            },
        }
        sessions_file = tmp_path / "sessions.json"
        sessions_file.write_text(json.dumps(sessions_data))
        monkeypatch.setattr(settings, "sessions_info_path", str(sessions_file))

        result = get_own_account_identifiers()

        assert result == {"HU111111111111111111111111", "HU333333333333333333333333"}

    def test_returns_empty_set_when_no_cacc_accounts(self, tmp_path, monkeypatch):
        sessions_data = {
            "Erste Bank": {"accounts": [{"cash_account_type": "SVGS", "account_id": {"iban": "HU111111111111111111111111"}}]},
            "Revolut": {"accounts": []},
        }
        sessions_file = tmp_path / "sessions.json"
        sessions_file.write_text(json.dumps(sessions_data))
        monkeypatch.setattr(settings, "sessions_info_path", str(sessions_file))

        result = get_own_account_identifiers()

        assert result == set()
