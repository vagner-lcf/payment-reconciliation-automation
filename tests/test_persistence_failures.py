from datetime import date
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from src.main import main
from contextlib import ExitStack


def test_database_insert_failure_prevents_tiny_settlement():
    receipt = {
        "provider": "mercado_pago",
        "provider_transaction_id": "TX_DB_FAILURE",
        "pix_transaction_id": None,
        "receipt_layout": "mp_pag_bol",
        "amount_matches_barcode": True,
        "beneficiary_document": "12345678901",
        "amount": Decimal("150.00"),
        "payment_date": date(2026, 10, 14),
    }

    database_error = OperationalError(
        "INSERT INTO tratoray_transactions ...",
        {},
        Exception("database is locked"),
    )

    with (
        patch("src.main.engine"),
        patch("src.main.create_tables"),
        patch(
            "src.main.extract_text_from_image",
            return_value="simulated receipt",
        ),
        patch(
            "src.main.extract_receipt_data",
            return_value=receipt,
        ),
        patch(
            "src.main.extract_receipt_hash",
            return_value="hash_db_failure",
        ),
        patch(
            "src.main.find_existing_transaction",
            return_value=None,
        ),
        patch(
            "src.main.build_authorization_url",
            return_value="https://example.test",
        ),
        patch(
            "src.main.wait_for_authorization_code",
            return_value="fake_code",
        ),
        patch(
            "src.main.exchange_code_for_token",
            return_value={"access_token": "fake_token"},
        ),
        patch(
            "src.main.calculate_due_date_window",
            return_value=("2026-09-29", "2026-10-29"),
        ),
        patch(
            "src.main.get_all_accounts_payable",
            return_value=[{"id": 123}],
        ),
        patch(
            "src.main.find_matching_accounts",
            return_value=[{"id": 123}],
        ),
        patch(
            "src.main.classify_matching_result",
            return_value="unique",
        ),
        patch(
            "src.main.summarize_accounts",
            return_value="Account 123",
        ),
        patch(
            "src.main.find_pending_transaction_by_tiny_id",
            return_value=None,
        ),
        patch(
            "src.main.insert_new_transaction",
            side_effect=database_error,
        ),
        patch(
            "src.main.settle_account_payable",
        ) as mock_settle,
    ):
        try:
            result = main(
                file_path="receipt.jpeg",
                settlement_enabled=True,
            )
        except OperationalError:
            result = None

    mock_settle.assert_not_called()

    # Desired behavior: a controlled, structured failure.
    assert result is not None
    assert result["status"] == "error"
    assert result["reason"] == "database_insert_failed"


def test_database_update_failure_after_confirmed_settlement():
    receipt = {
        "provider": "mercado_pago",
        "provider_transaction_id": "TX_UPDATE_FAILURE",
        "pix_transaction_id": None,
        "receipt_layout": "mp_pag_bol",
        "amount_matches_barcode": True,
        "beneficiary_document": "12345678901",
        "amount": Decimal("150.00"),
        "payment_date": date(2026, 10, 14),
    }

    database_error = OperationalError(
        "UPDATE tratoray_transactions ...",
        {},
        Exception("database is locked"),
    )


    with ExitStack() as stack:
        stack.enter_context(patch("src.main.engine"))
        stack.enter_context(patch("src.main.create_tables"))
        stack.enter_context(
            patch(
                "src.main.extract_text_from_image",
                return_value="simulated receipt",
            )
        )
        stack.enter_context(
            patch("src.main.extract_receipt_data", return_value=receipt)
        )
        stack.enter_context(
            patch("src.main.extract_receipt_hash", return_value="hash_update_failure")
        )
        stack.enter_context(
            patch("src.main.find_existing_transaction", return_value=None)
        )
        stack.enter_context(
            patch("src.main.build_authorization_url", return_value="https://example.test")
        )
        stack.enter_context(
            patch("src.main.wait_for_authorization_code", return_value="fake_code")
        )
        stack.enter_context(
            patch(
                "src.main.exchange_code_for_token",
                return_value={"access_token": "fake_token"},
            )
        )
        stack.enter_context(
            patch(
                "src.main.calculate_due_date_window",
                return_value=("2026-09-29", "2026-10-29"),
            )
        )
        stack.enter_context(
            patch("src.main.get_all_accounts_payable", return_value=[{"id": 123}])
        )
        stack.enter_context(
            patch("src.main.find_matching_accounts", return_value=[{"id": 123}])
        )
        stack.enter_context(
            patch("src.main.classify_matching_result", return_value="unique")
        )
        stack.enter_context(
            patch("src.main.summarize_accounts", return_value="Account 123")
        )
        stack.enter_context(
            patch(
                "src.main.find_pending_transaction_by_tiny_id",
                return_value=None,
            )
        )
        stack.enter_context(
            patch("src.main.insert_new_transaction", return_value=42)
        )

        mock_settle = stack.enter_context(
            patch("src.main.settle_account_payable", return_value=True)
        )

        stack.enter_context(
            patch(
                "src.main.get_account_payable_by_id",
                return_value={"situacao": "pago", "saldo": 0},
            )
        )
        stack.enter_context(
            patch(
                "src.main.mark_transaction_as_processed",
                side_effect=database_error,
            )
        )

        result = main(
            file_path="receipt.jpeg",
            settlement_enabled=True,
        )

    mock_settle.assert_called_once()
    assert result is not None
    assert result["status"] == "verification_pending"
    assert result["reason"] == "local_update_failed"


def test_settlement_timeout_keeps_transaction_pending():
    receipt = {
        "provider": "mercado_pago",
        "provider_transaction_id": "TX_UPDATE_FAILURE",
        "pix_transaction_id": None,
        "receipt_layout": "mp_pag_bol",
        "amount_matches_barcode": True,
        "beneficiary_document": "12345678901",
        "amount": Decimal("150.00"),
        "payment_date": date(2026, 10, 14),
    }

    database_error = OperationalError(
        "UPDATE tratoray_transactions ...",
        {},
        Exception("database is locked"),
    )


    with ExitStack() as stack:
        stack.enter_context(patch("src.main.engine"))
        stack.enter_context(patch("src.main.create_tables"))
        stack.enter_context(
            patch(
                "src.main.extract_text_from_image",
                return_value="simulated receipt",
            )
        )
        stack.enter_context(
            patch("src.main.extract_receipt_data", return_value=receipt)
        )
        stack.enter_context(
            patch("src.main.extract_receipt_hash", return_value="hash_update_failure")
        )
        stack.enter_context(
            patch("src.main.find_existing_transaction", return_value=None)
        )
        stack.enter_context(
            patch("src.main.build_authorization_url", return_value="https://example.test")
        )
        stack.enter_context(
            patch("src.main.wait_for_authorization_code", return_value="fake_code")
        )
        stack.enter_context(
            patch(
                "src.main.exchange_code_for_token",
                return_value={"access_token": "fake_token"},
            )
        )
        stack.enter_context(
            patch(
                "src.main.calculate_due_date_window",
                return_value=("2026-09-29", "2026-10-29"),
            )
        )
        stack.enter_context(
            patch("src.main.get_all_accounts_payable", return_value=[{"id": 123}])
        )
        stack.enter_context(
            patch("src.main.find_matching_accounts", return_value=[{"id": 123}])
        )
        stack.enter_context(
            patch("src.main.classify_matching_result", return_value="unique")
        )
        stack.enter_context(
            patch("src.main.summarize_accounts", return_value="Account 123")
        )
        stack.enter_context(
            patch(
                "src.main.find_pending_transaction_by_tiny_id",
                return_value=None,
            )
        )
        stack.enter_context(
            patch("src.main.insert_new_transaction", return_value=42)
        )

        mock_settle = stack.enter_context(
            patch("src.main.settle_account_payable", return_value=False)
        )

        mock_get_account = stack.enter_context(
            patch("src.main.get_account_payable_by_id")
        )

        mock_mark_processed = stack.enter_context(
            patch("src.main.mark_transaction_as_processed")
        )

        stack.enter_context(
            patch(
                "src.main.get_account_payable_by_id",
                return_value={"situacao": "pago", "saldo": 0},
            )
        )
        stack.enter_context(
            patch(
                "src.main.mark_transaction_as_processed",
                side_effect=database_error,
            )
        )

        result = main(
            file_path="receipt.jpeg",
            settlement_enabled=True,
        )

    mock_settle.assert_called_once()
    mock_get_account.assert_not_called()
    mock_mark_processed.assert_not_called()

    assert result["status"] == "verification_pending"
    assert result["reason"] == "settlement_request_failed"
