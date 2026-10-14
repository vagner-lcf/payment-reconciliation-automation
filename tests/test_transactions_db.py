from src.tratoray_transactions_db import (
    insert_new_transaction,
    mark_transaction_as_processed,
    find_existing_transaction,
    metadata,
    tb_tratoray_transactions,
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

def test_find_existing_transaction_prioritizes_file_hash(db_connection):
    transaction_id = insert_new_transaction(
        transaction_data={
            "file_hash": "hash_original",
            "provider": "mercado_pago",
            "provider_transaction_id": "TX001",
            "pix_transaction_id": "PIX001",
            "amount": 1500,
            "status": "processed",
        },
        db_connection=db_connection,
    )

    result = find_existing_transaction(
        transaction_data={
            "file_hash": "hash_original",
            "provider": "mercado_pago",
            "provider_transaction_id": "TX_DIFFERENT",
            "pix_transaction_id": "PIX_DIFFERENT",
        },
        db_connection=db_connection,
    )

    assert result is not None
    assert result["id"] == transaction_id
    assert result["status"] == "processed"

def test_find_existing_transaction_falls_back_to_provider_id(db_connection):
    transaction_id = insert_new_transaction(
        transaction_data={
            "file_hash": "hash_original",
            "provider": "mercado_pago",
            "provider_transaction_id": "TX001",
            "pix_transaction_id": "PIX001",
            "amount": 1500,
            "status": "processed",
        },
        db_connection=db_connection,
    )

    result = find_existing_transaction(
        transaction_data={
            "file_hash": "hash_novo",
            "provider": "mercado_pago",
            "provider_transaction_id": "TX001",
            "pix_transaction_id": "PIX_NOVO",
        },
        db_connection=db_connection,
    )

    assert result is not None
    assert result["id"] == transaction_id

def test_review_required_cannot_be_marked_as_processed(db_connection):
    transaction_id = insert_new_transaction(
        transaction_data={
            "file_hash": "hash_review_required",
            "status": "review_required",
        },
        db_connection=db_connection,
    )

    result = mark_transaction_as_processed(
        transaction_id=transaction_id,
        db_connection=db_connection,
    )

    assert result is False

    stmt = (
        select(tb_tratoray_transactions.c.status)
        .where(tb_tratoray_transactions.c.id == transaction_id)
    )

    stored_status = db_connection.execute(stmt).scalar_one()

    assert stored_status == "review_required"

def test_find_existing_transaction_detects_conflicting_ids(db_connection):
    insert_new_transaction(
        transaction_data={
            "file_hash": "hash_a",
            "provider": "mercado_pago",
            "provider_transaction_id": "TX001",
            "pix_transaction_id": "PIX001",
            "status": "processed",
        },
        db_connection=db_connection,
    )

    insert_new_transaction(
        transaction_data={
            "file_hash": "hash_b",
            "provider": "mercado_pago",
            "provider_transaction_id": "TX002",
            "pix_transaction_id": "PIX002",
            "status": "processed",
        },
        db_connection=db_connection,
    )

    result = find_existing_transaction(
        transaction_data={
            "file_hash": "hash_novo",
            "provider": "mercado_pago",
            "provider_transaction_id": "TX002",
            "pix_transaction_id": "PIX001",
        },
        db_connection=db_connection,
    )

    assert result is not None
    assert result["identity_conflict"] is True
