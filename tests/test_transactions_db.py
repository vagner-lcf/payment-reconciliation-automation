from src.tratoray_transactions_db import (
    insert_new_transaction, mark_transaction_as_processed, metadata, tb_tratoray_transactions
    )
from sqlalchemy import create_engine, select
import pytest

@pytest.fixture
def db_connection():
    test_engine = create_engine("sqlite:///:memory:")
    metadata.create_all(test_engine)

    with test_engine.begin() as conn:
        yield conn

def test_insert_new_transaction(db_connection):
    transaction_data = {
        "file_hash": "hash_test_001",
        "provider": "mercado_pago",
        "provider_transaction_id": "TX001",
        "amount": 1500,
        "id_tiny": 1234,
        "status": "processing"
    }

    transaction_id = insert_new_transaction(
        transaction_data=transaction_data, db_connection=db_connection
    )

    assert transaction_id == 1

    id_stmt = (
        select(tb_tratoray_transactions)
        .where(tb_tratoray_transactions.c.id == transaction_id)
    )
    id_result = db_connection.execute(id_stmt)
    id_row = id_result.fetchone()

    assert id_row is not None

    stored_transaction = dict(id_row._mapping)

    assert stored_transaction["id"] == transaction_id
    assert stored_transaction["amount"] == transaction_data["amount"]
    assert stored_transaction["status"] == transaction_data["status"]
    assert stored_transaction["id_tiny"] == transaction_data["id_tiny"]

def test_mark_transaction_as_processed(db_connection):
    transaction_data = {
        "file_hash": "hash_test_001",
        "provider": "mercado_pago",
        "provider_transaction_id": "TX001",
        "amount": 1500,
        "id_tiny": 1234,
        "status": "processing"
    }

    transaction_id = insert_new_transaction(
        transaction_data=transaction_data, db_connection=db_connection
    )

    assert transaction_id == 1

    transaction_status = mark_transaction_as_processed(
        transaction_id=transaction_id, db_connection=db_connection
    )

    assert transaction_status is True

    status_stmt = (
        select(tb_tratoray_transactions)
        .where(tb_tratoray_transactions.c.id == transaction_id)
    )
    status_result = db_connection.execute(status_stmt)
    status_row = status_result.fetchone()

    stored_transaction = dict(status_row._mapping)

    assert stored_transaction["status"] == "processed"

def test_transaction_not_found_for_marking(db_connection):
    transaction_status = mark_transaction_as_processed(
        transaction_id=999, db_connection=db_connection
    )

    assert transaction_status is False