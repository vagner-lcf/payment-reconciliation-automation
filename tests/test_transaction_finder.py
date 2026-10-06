from src.tratoray_transactions_db import (
    find_existing_transaction, metadata, tb_tratoray_transactions
    )
from sqlalchemy import create_engine, insert
import pytest

@pytest.fixture
def db_connection():
    test_engine = create_engine("sqlite:///:memory:")
    metadata.create_all(test_engine)

    with test_engine.begin() as conn:
        yield conn

def test_find_existing_transaction(db_connection):
    transaction_data = {
        "file_hash": "hash_test_001",
        "provider": "mercado_pago",
        "provider_transaction_id": "TX001",
        "amount": 1500,
        "status": "processed"
    }    

    stmt = insert(tb_tratoray_transactions).values(transaction_data)
    result = db_connection.execute(stmt)

    print(result)
    print(type(result))

    print(result.inserted_primary_key)
    
    existing = find_existing_transaction(transaction_data=transaction_data, db_connection=db_connection)

    assert existing is not None
    assert existing["file_hash"] == "hash_test_001"

def test_find_non_existing_transaction(db_connection):
    transaction_data = {
        "file_hash": "hash_test_001",
        "provider": "mercado_pago",
        "provider_transaction_id": "TX001",
        "amount": 1500,
        "status": "processed",
    }    

    existing = find_existing_transaction(transaction_data=transaction_data, db_connection=db_connection)

    assert existing is None

def test_find_existing_pix_transaction_id(db_connection):
    original_transaction = {
        "file_hash": "hash_original",
        "provider": "mercado_pago",
        "pix_transaction_id": "PIX123",
        "amount": 1500,
        "status": "processed",
    }     
    
    transaction_data = {
        "file_hash": "hash_novo",
        "provider": "mercado_pago",
        "pix_transaction_id": "PIX123",
        "amount": 1500,
        "status": "processed",
    }    

    stmt = insert(tb_tratoray_transactions).values(original_transaction)
    db_connection.execute(stmt)

    existing = find_existing_transaction(transaction_data=transaction_data, db_connection=db_connection)

    assert existing is not None
    assert existing["file_hash"] == "hash_original"

def test_does_not_match_when_pix_transaction_id_is_missing(db_connection):
    original_transaction = {
        "file_hash": "hash_original",
        "provider": "mercado_pago",
        "provider_transaction_id": "TX001",
        "amount": 1500,
        "status": "processed",
    }     
    
    transaction_data = {
        "file_hash": "hash_novo",
        "provider": "mercado_pago",
        "provider_transaction_id": "TX002",
        "amount": 1500,
        "status": "processed",
    }    

    stmt = insert(tb_tratoray_transactions).values(original_transaction)
    db_connection.execute(stmt)

    existing = find_existing_transaction(transaction_data=transaction_data, db_connection=db_connection)

    assert existing is None

def test_find_existing_transaction_by_provider_and_provider_transaction_id(db_connection):    
    original_transaction = {
        "file_hash": "hash_original",
        "provider": "mercado_pago",
        "provider_transaction_id": "TX001",
        "amount": 1500,
        "status": "processed",
    }     
    
    transaction_data = {
        "file_hash": "hash_novo",
        "provider": "mercado_pago",
        "provider_transaction_id": "TX001",
        "amount": 1500,
        "status": "processed",
    }    

    stmt = insert(tb_tratoray_transactions).values(original_transaction)
    db_connection.execute(stmt)

    existing = find_existing_transaction(transaction_data=transaction_data, db_connection=db_connection)

    assert existing is not None
    assert existing["file_hash"] == "hash_original"

