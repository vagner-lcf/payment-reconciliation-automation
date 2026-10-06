from src.main import reconcile_existing_transaction
from unittest.mock import MagicMock, patch
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