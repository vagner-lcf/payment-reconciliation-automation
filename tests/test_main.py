from src.main import main, reconcile_existing_transaction
from src import main as main_module
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import date
import pytest


def test_reconcile_existing_transaction_already_processed():
    existing_transaction = {
        "status": "processed",
        "id_tiny": 1,
        "id": 1
    }

    with patch("src.main.get_account_payable_by_id") as mock_get_account:
        result = reconcile_existing_transaction(
            existing_transaction=existing_transaction,
            access_token="fake_token",
            db_engine=None
        )

    assert result == "already_processed"
    mock_get_account.assert_not_called()

def test_reconcile_existing_transaction_processing():  
    existing_transaction = {
        "status": "processing",
        "id_tiny": 1,
        "id": 1
    }

    with patch("src.main.get_account_payable_by_id") as mock_get_account:
        mock_get_account.return_value = None

        result = reconcile_existing_transaction(
            existing_transaction=existing_transaction,
            access_token="fake_token",
            db_engine=None
        )

    assert result == "verification_failed"

    mock_get_account.assert_called_once_with(
    access_token="fake_token",
    id_account=1,
    )  

def test_reconcile_existing_transaction_not_settled():
    existing_transaction = {
        "status": "processing",
        "id_tiny": 1,
        "id": 1
    }

    with patch("src.main.get_account_payable_by_id") as mock_get_account:
        mock_get_account.return_value = {
            "situacao": "aberto",
            "saldo": 100.0
        }

        result = reconcile_existing_transaction(
            existing_transaction=existing_transaction,
            access_token="fake_token",
            db_engine=None
        )

    assert result == "not_settled"

def test_reconcile_existing_transaction_reconciled():
    existing_transaction = {
        "status": "processing",
        "id_tiny": 1,
        "id": 1
    }

    db_engine = MagicMock()
    db_connection = MagicMock()

    db_engine.begin.return_value.__enter__.return_value = db_connection

    with (
        patch("src.main.get_account_payable_by_id") as mock_get_account,
        patch("src.main.mark_transaction_as_processed") as mock_mark_processed
    ):
        mock_get_account.return_value = {
            "situacao": "pago",
            "saldo": 0.0
        }
        mock_mark_processed.return_value = True

        result = reconcile_existing_transaction(
            existing_transaction=existing_transaction,
            access_token="fake_token",
            db_engine=db_engine
        )

    assert result == "reconciled"

    mock_get_account.assert_called_once_with(
        access_token="fake_token",
        id_account=1,
    )

    mock_mark_processed.assert_called_once_with(
        transaction_id=1,
        db_connection=db_connection,
    )

def test_reconcile_existing_transaction_not_reconciled():
    existing_transaction = {
        "status": "processing",
        "id_tiny": 1,
        "id": 1
    }

    db_engine = MagicMock()
    db_connection = MagicMock()

    db_engine.begin.return_value.__enter__.return_value = db_connection

    with (
        patch("src.main.get_account_payable_by_id") as mock_get_account,
        patch("src.main.mark_transaction_as_processed") as mock_mark_processed
    ):
        mock_get_account.return_value = {
            "situacao": "pago",
            "saldo": 0.0
        }
        mock_mark_processed.return_value = False

        result = reconcile_existing_transaction(
            existing_transaction=existing_transaction,
            access_token="fake_token",
            db_engine=db_engine
        )

    assert result == "local_update_failed"

    mock_get_account.assert_called_once_with(
        access_token="fake_token",
        id_account=1,
    )

    mock_mark_processed.assert_called_once_with(
        transaction_id=1,
        db_connection=db_connection,
    )


@pytest.mark.parametrize(
    "status, expected_result",
    [
        ("review_required", "review_required"),
        ("banana", "unexpected_status"),
    ],
)
def test_reconcile_existing_transaction_status_without_reconciliation(
    status,
    expected_result,
):
    existing_transaction = {
        "status": status,
        "id_tiny": 1,
        "id": 1
    }

    with patch("src.main.get_account_payable_by_id") as mock_get_account:
        result = reconcile_existing_transaction(
            existing_transaction=existing_transaction,
            access_token="fake_token",
            db_engine=None
        )

    assert result == expected_result
    mock_get_account.assert_not_called()


@pytest.mark.parametrize(
    "status",
    ["processed", "processing", "review_required"],
)
def test_main_blocks_identity_conflict_before_tiny(status):
    existing_transaction = {
        "id": 1,
        "status": status,
        "identity_conflict": True,
    }

    receipt_data = {
        "provider": "mercado_pago",
        "provider_transaction_id": "TX002",
        "pix_transaction_id": "PIX001",
    }

    with (
        patch("src.main.engine") as mock_engine,
        patch("src.main.create_tables"),
        patch("src.main.extract_text_from_pdf", return_value="texto"),
        patch("src.main.extract_receipt_data", return_value=receipt_data),
        patch("src.main.extract_receipt_hash", return_value="hash_novo"),
        patch(
            "src.main.find_existing_transaction",
            return_value=existing_transaction,
        ),
        patch(
            "src.main.get_valid_access_token",
        ) as mock_get_token,
        patch("src.main.get_all_accounts_payable") as mock_get_accounts,
        patch("src.main.settle_account_payable") as mock_settle,
        patch("src.main.reconcile_existing_transaction") as mock_reconcile,
    ):
        result = main(
            file_path="data/input/comprovante_teste.pdf",
            settlement_enabled=False,
        )

    mock_get_token.assert_not_called()
    mock_get_accounts.assert_not_called()
    mock_settle.assert_not_called()
    mock_reconcile.assert_not_called()

    assert result["status"] == "review_required"
    assert result["reason"] == "identity_conflict"


@pytest.mark.parametrize(
    "receipt_layout, amount_matches_barcode",
    [
        ("mp_pix_tra", None),
        ("unknown", None),
        ("mp_pag_bol", False),
        ("mp_pag_bol", None),
        ("mp_pix_bol", False),
        ("mp_pix_bol", None),
    ],
)
def test_main_blocks_ineligible_images_before_tiny(
    receipt_layout,
    amount_matches_barcode,
):
    receipt_data = {
        "provider": "mercado_pago",
        "provider_transaction_id": None,
        "pix_transaction_id": None,
        "receipt_layout": receipt_layout,
        "amount_matches_barcode": amount_matches_barcode,
        "beneficiary_document": "12345678901",
        "amount": Decimal("150.00"),
        "payment_date": date(2026, 10, 14),
    }

    with (
        patch("src.main.engine"),
        patch("src.main.create_tables"),
        patch("src.main.extract_text_from_image", return_value="texto OCR"),
        patch("src.main.extract_receipt_data", return_value=receipt_data),
        patch("src.main.extract_receipt_hash", return_value="hash_imagem"),
        patch("src.main.find_existing_transaction", return_value=None),
        patch(
            "src.main.get_valid_access_token",
        ) as mock_get_token,
        patch("src.main.get_all_accounts_payable") as mock_get_accounts,
        patch("src.main.settle_account_payable") as mock_settle,
        patch(
            "src.main.insert_new_transaction",
            return_value=42,
        ) as mock_insert,
    ):
        result = main(
            file_path="data/input/comprovante_teste.jpeg",
            settlement_enabled=False,
        )

    mock_get_token.assert_not_called()
    mock_get_accounts.assert_not_called()
    mock_settle.assert_not_called()
    mock_insert.assert_called_once()

    transaction_data = mock_insert.call_args.kwargs["transaction_data"]

    assert transaction_data["status"] == "review_required"
    assert transaction_data["file_hash"] == "hash_imagem"
    assert result["status"] == "review_required"
    assert result["transaction_id"] == 42


@pytest.mark.parametrize(
    "missing_field",
    [
        "beneficiary_document",
        "amount",
        "payment_date",
    ],
)
def test_main_blocks_missing_required_data_before_tiny(missing_field):
    receipt_data = {
        "provider": "mercado_pago",
        "provider_transaction_id": "TX001",
        "pix_transaction_id": None,
        "receipt_layout": "mp_pag_bol",
        "amount_matches_barcode": True,
        "beneficiary_document": "12345678901",
        "amount": Decimal("150.00"),
        "payment_date": date(2026, 10, 14),
    }

    receipt_data[missing_field] = None

    with (
        patch("src.main.engine"),
        patch("src.main.create_tables"),
        patch("src.main.extract_text_from_image", return_value="texto OCR"),
        patch("src.main.extract_receipt_data", return_value=receipt_data),
        patch("src.main.extract_receipt_hash", return_value="hash_imagem"),
        patch("src.main.find_existing_transaction", return_value=None),
        patch(
            "src.main.insert_new_transaction",
            return_value=42,
        ) as mock_insert,
        patch(
            "src.main.get_valid_access_token",
        ) as mock_get_token,
        patch("src.main.get_all_accounts_payable") as mock_get_accounts,
        patch("src.main.settle_account_payable") as mock_settle,
    ):
        main(
            file_path="data/input/comprovante_teste.jpeg",
            settlement_enabled=False,
        )

    mock_insert.assert_called_once()

    transaction_data = mock_insert.call_args.kwargs["transaction_data"]

    assert transaction_data["status"] == "review_required"

    mock_get_token.assert_not_called()
    mock_get_accounts.assert_not_called()
    mock_settle.assert_not_called()


def test_main_eligible_image_reaches_matching_without_settlement():
    receipt_data = {
        "provider": "mercado_pago",
        "provider_transaction_id": "TX001",
        "pix_transaction_id": None,
        "receipt_layout": "mp_pag_bol",
        "amount_matches_barcode": True,
        "beneficiary_document": "12345678901",
        "amount": Decimal("150.00"),
        "payment_date": date(2026, 10, 14),
    }

    matching_account = {
        "id": 123,
    }

    with (
        patch("src.main.engine"),
        patch("src.main.create_tables"),
        patch("src.main.extract_text_from_image", return_value="texto OCR"),
        patch("src.main.extract_receipt_data", return_value=receipt_data),
        patch("src.main.extract_receipt_hash", return_value="hash_imagem"),
        patch("src.main.find_existing_transaction", return_value=None),

        patch(
            "src.main.get_valid_access_token",
            return_value="token_teste",
        ) as mock_get_token,

        patch(
            "src.main.calculate_due_date_window",
            return_value=("2026-09-29", "2026-10-29"),
        ),

        patch(
            "src.main.get_all_accounts_payable",
            return_value=[{"id": 123}],
        ) as mock_get_accounts,

        patch(
            "src.main.find_matching_accounts",
            return_value=[matching_account],
        ) as mock_matching,

        patch(
            "src.main.classify_matching_result",
            return_value="unique",
        ),

        patch(
            "src.main.summarize_accounts",
            return_value="Conta de teste",
        ),

        patch("src.main.insert_new_transaction") as mock_insert,
        patch("src.main.settle_account_payable") as mock_settle,
        patch(
            "src.main.find_pending_transaction_by_tiny_id",
            return_value=None,
        ),
    ):
        result = main(
            file_path="data/input/comprovante_teste.jpeg",
            settlement_enabled=False,
        )

    # Eligible images must request a valid access token.
    mock_get_token.assert_called_once_with()

    # The application must retrieve accounts payable.
    mock_get_accounts.assert_called_once()

    # Matching must use the extracted receipt data.
    mock_matching.assert_called_once()

    assert mock_matching.call_args.args[1:] == (
        "12345678901",
        Decimal("150.00"),
    )

    assert result["status"] == "dry_run"
    assert result["id_tiny"] == 123
    assert result["beneficiary_document"] == "12345678901"
    assert result["amount"] == Decimal("150.00")
    assert result["payment_date"] == date(2026, 10, 14)

    # Dry-run mode must not create a processing transaction.
    mock_insert.assert_not_called()

    # No financial settlement must occur.
    mock_settle.assert_not_called()


def test_unknown_provider_requires_manual_review(monkeypatch):
    payment = {
        "provider": "unknown",
        "payment_type": "boleto",
        "receipt_layout": "unknown",
        "amount": Decimal("7772.22"),
        "payment_date": date(2026, 10, 9),
        "beneficiary_document": "11222333000181",
        "provider_transaction_id": None,
        "pix_transaction_id": None,
        "barcode": None,
        "barcode_amount": None,
        "amount_matches_barcode": None,
    }

    monkeypatch.setattr(
        main_module,
        "extract_text_from_pdf",
        lambda file_path: "Simulated Itaú PDF",
    )

    monkeypatch.setattr(
        main_module,
        "extract_receipt_data",
        lambda text, source_type: payment,
    )

    monkeypatch.setattr(
        main_module,
        "extract_receipt_hash",
        lambda file_path: "hash_teste_provider_unknown",
    )

    # Prevent the test from accessing the production database.
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    monkeypatch.setattr(main_module, "engine", test_engine)

    # Any attempt to authenticate or access Tiny must fail the test.
    def unexpected_tiny_call(*args, **kwargs):
        raise AssertionError(
            "An unsupported provider attempted to access Tiny."
        )

    monkeypatch.setattr(
        main_module,
        "get_valid_access_token",
        unexpected_tiny_call,
    )

    monkeypatch.setattr(
        main_module,
        "get_all_accounts_payable",
        unexpected_tiny_call,
    )

    monkeypatch.setattr(
        main_module,
        "settle_account_payable",
        unexpected_tiny_call,
    )

    result = main_module.main(
        file_path="itau_teste.pdf",
        settlement_enabled=True,
    )

    assert result["status"] == "review_required"
    assert result["beneficiary_document"] == "11222333000181"
    assert result["payment_date"] == date(2026, 10, 9)
    assert result["amount"] == Decimal("7772.22")
    assert result["transaction_id"] is not None

    from sqlalchemy import inspect, text

    table_names = inspect(test_engine).get_table_names()

    assert len(table_names) == 1, (
        f"Expected one transaction table, found: {table_names}"
    )

    with test_engine.connect() as connection:
        status = connection.execute(
            text(f'SELECT status FROM "{table_names[0]}"')
        ).scalar_one()

    assert status == "review_required"


def test_main_returns_processed_after_confirmed_settlement():
    receipt_data = {
        "provider": "mercado_pago",
        "provider_transaction_id": "TX_SUCCESS",
        "pix_transaction_id": None,
        "receipt_layout": "mp_pag_bol",
        "amount_matches_barcode": True,
        "beneficiary_document": "12345678901",
        "amount": Decimal("150.00"),
        "payment_date": date(2026, 10, 14),
    }

    with (
        patch("src.main.engine"),
        patch("src.main.create_tables"),
        patch("src.main.extract_text_from_image", return_value="texto OCR"),
        patch("src.main.extract_receipt_data", return_value=receipt_data),
        patch("src.main.extract_receipt_hash", return_value="hash_success"),
        patch("src.main.find_existing_transaction", return_value=None),
        patch(
            "src.main.get_valid_access_token",
            return_value="token_teste",
        ),
        patch(
            "src.main.calculate_due_date_window",
            return_value=("2026-09-29", "2026-10-29"),
        ),
        patch("src.main.get_all_accounts_payable", return_value=[{"id": 123}]),
        patch(
            "src.main.find_matching_accounts",
            return_value=[{"id": 123}],
        ),
        patch("src.main.classify_matching_result", return_value="unique"),
        patch("src.main.summarize_accounts", return_value="Conta de teste"),
        patch("src.main.insert_new_transaction", return_value=42) as mock_insert,
        patch("src.main.settle_account_payable", return_value=True) as mock_settle,
        patch(
            "src.main.get_account_payable_by_id",
            return_value={"situacao": "pago", "saldo": 0},
        ) as mock_get_account,
        patch(
            "src.main.mark_transaction_as_processed",
            return_value=True,
        ) as mock_mark_processed,
        patch(
            "src.main.find_pending_transaction_by_tiny_id",
            return_value=None,
        ),
    ):
        result = main(
            file_path="comprovante_teste.jpeg",
            settlement_enabled=True,
        )

    assert result["status"] == "processed"
    assert result["reason"] is None
    assert result["transaction_id"] == 42
    assert result["id_tiny"] == 123
    assert result["beneficiary_document"] == "12345678901"
    assert result["amount"] == Decimal("150.00")
    assert result["payment_date"] == date(2026, 10, 14)

    transaction_data = mock_insert.call_args.kwargs["transaction_data"]
    assert transaction_data["status"] == "processing"

    mock_settle.assert_called_once()
    mock_get_account.assert_called_once()
    mock_mark_processed.assert_called_once()


def test_main_returns_verification_pending_when_settlement_fails():
    receipt_data = {
        "provider": "mercado_pago",
        "provider_transaction_id": "TX_FAILED",
        "pix_transaction_id": None,
        "receipt_layout": "mp_pag_bol",
        "amount_matches_barcode": True,
        "beneficiary_document": "12345678901",
        "amount": Decimal("150.00"),
        "payment_date": date(2026, 10, 14),
    }

    with (
        patch("src.main.engine"),
        patch("src.main.create_tables"),
        patch("src.main.extract_text_from_image", return_value="texto OCR"),
        patch("src.main.extract_receipt_data", return_value=receipt_data),
        patch("src.main.extract_receipt_hash", return_value="hash_failed"),
        patch("src.main.find_existing_transaction", return_value=None),
        patch(
            "src.main.get_valid_access_token",
            return_value="token_teste",
        ),
        patch(
            "src.main.calculate_due_date_window",
            return_value=("2026-09-29", "2026-10-29"),
        ),
        patch("src.main.get_all_accounts_payable", return_value=[{"id": 123}]),
        patch(
            "src.main.find_matching_accounts",
            return_value=[{"id": 123}],
        ),
        patch("src.main.classify_matching_result", return_value="unique"),
        patch("src.main.summarize_accounts", return_value="Conta de teste"),
        patch("src.main.insert_new_transaction", return_value=42) as mock_insert,
        patch("src.main.settle_account_payable", return_value=False) as mock_settle,
        patch("src.main.get_account_payable_by_id") as mock_get_account,
        patch("src.main.mark_transaction_as_processed") as mock_mark_processed,
        patch(
            "src.main.find_pending_transaction_by_tiny_id",
            return_value=None,
        ),
    ):
        result = main(
            file_path="comprovante_teste.jpeg",
            settlement_enabled=True,
        )

    assert result["status"] == "verification_pending"
    assert result["reason"] == "settlement_request_failed"
    assert result["transaction_id"] == 42
    assert result["id_tiny"] == 123

    transaction_data = mock_insert.call_args.kwargs["transaction_data"]
    assert transaction_data["status"] == "processing"

    mock_settle.assert_called_once()
    mock_get_account.assert_not_called()
    mock_mark_processed.assert_not_called()