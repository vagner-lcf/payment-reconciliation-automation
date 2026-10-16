
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, insert, select
from unittest.mock import patch

from src.main import main
from src.tratoray_transactions_db import (
    create_tables,
    tb_tratoray_transactions,
)


def test_new_receipt_cannot_settle_account_with_pending_transaction(
    tmp_path,
):
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'test_transactions.db'}"
    )
    create_tables(test_engine)

    # A previous receipt has an inconclusive settlement.
    with test_engine.begin() as connection:
        connection.execute(
            insert(tb_tratoray_transactions).values(
                file_hash="hash_receipt_A",
                provider="mercado_pago",
                provider_transaction_id="TX_A",
                pix_transaction_id=None,
                amount=15000,
                id_tiny=123,
                status="processing",
            )
        )

    receipt_b = {
        "provider": "mercado_pago",
        "provider_transaction_id": "TX_B",
        "pix_transaction_id": None,
        "receipt_layout": "mp_pag_bol",
        "amount_matches_barcode": True,
        "beneficiary_document": "12345678901",
        "amount": Decimal("150.00"),
        "payment_date": date(2026, 10, 14),
    }

    try:
        with (
            patch("src.main.engine", test_engine),
            patch(
                "src.main.extract_text_from_image",
                return_value="simulated receipt",
            ),
            patch(
                "src.main.extract_receipt_data",
                return_value=receipt_b,
            ),
            patch(
                "src.main.extract_receipt_hash",
                return_value="hash_receipt_B",
            ),
            patch(
                "src.main.get_valid_access_token",
                return_value="fake_token",
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
                "src.main.settle_account_payable",
                return_value=True,
            ) as mock_settle,
            patch(
                "src.main.get_account_payable_by_id",
                return_value={"situacao": "pago", "saldo": 0},
            ),
        ):
            result = main(
                file_path="receipt_B.jpeg",
                settlement_enabled=True,
            )

        # A pending transaction must prevent a second settlement.
        assert result["status"] == "review_required"
        assert result["reason"] == "account_has_pending_transaction"
        mock_settle.assert_not_called()

        with test_engine.connect() as connection:
            rows = connection.execute(
                select(tb_tratoray_transactions)
            ).mappings().all()

        assert len(rows) == 1
        assert rows[0]["status"] == "processing"
        assert rows[0]["id_tiny"] == 123

    finally:
        test_engine.dispose()


def test_new_receipt_can_settle_account_without_pending_transaction(
    tmp_path,
):
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'test_no_pending.db'}"
    )
    create_tables(test_engine)

    receipt = {
        "provider": "mercado_pago",
        "provider_transaction_id": "TX_NEW",
        "pix_transaction_id": None,
        "receipt_layout": "mp_pag_bol",
        "amount_matches_barcode": True,
        "beneficiary_document": "12345678901",
        "amount": Decimal("150.00"),
        "payment_date": date(2026, 10, 14),
    }

    try:
        with (
            patch("src.main.engine", test_engine),
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
                return_value="hash_new_receipt",
            ),
            patch(
                "src.main.get_valid_access_token",
                return_value="fake_token",
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
                "src.main.settle_account_payable",
                return_value=True,
            ) as mock_settle,
            patch(
                "src.main.get_account_payable_by_id",
                return_value={"situacao": "pago", "saldo": 0},
            ),
        ):
            result = main(
                file_path="receipt_new.jpeg",
                settlement_enabled=True,
            )

        assert result["status"] == "processed"
        assert result["id_tiny"] == 123

        mock_settle.assert_called_once_with(
            access_token="fake_token",
            id_account=123,
            payment_date=date(2026, 10, 14),
            amount=Decimal("150.00"),
        )

        with test_engine.connect() as connection:
            rows = connection.execute(
                select(tb_tratoray_transactions)
            ).mappings().all()

        assert len(rows) == 1
        assert rows[0]["status"] == "processed"
        assert rows[0]["id_tiny"] == 123

    finally:
        test_engine.dispose()
