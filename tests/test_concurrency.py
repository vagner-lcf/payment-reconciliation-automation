
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError

from src.tratoray_transactions_db import (
    create_tables,
    insert_new_transaction,
    tb_tratoray_transactions,
)


def test_duplicate_transaction_cannot_be_inserted(tmp_path):
    db_path = tmp_path / "transactions.db"
    test_engine = create_engine(f"sqlite:///{db_path}")

    create_tables(test_engine)

    transaction = {
        "file_hash": "same_receipt_hash",
        "provider": "mercado_pago",
        "provider_transaction_id": "TX123",
        "pix_transaction_id": None,
        "status": "processing",
    }

    with test_engine.begin() as connection:
        insert_new_transaction(transaction, connection)

    with pytest.raises(IntegrityError):
        with test_engine.begin() as connection:
            insert_new_transaction(transaction, connection)

    test_engine.dispose()


def test_distinct_receipts_can_reference_same_tiny_account(tmp_path):
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'transactions.db'}"
    )

    try:
        create_tables(test_engine)

        first_receipt = {
            "file_hash": "receipt_hash_A",
            "provider": "mercado_pago",
            "provider_transaction_id": "TX_A",
            "pix_transaction_id": None,
            "amount": 15000,
            "id_tiny": 123,
            "status": "processed",
        }

        second_receipt = {
            "file_hash": "receipt_hash_B",
            "provider": "mercado_pago",
            "provider_transaction_id": "TX_B",
            "pix_transaction_id": None,
            "amount": 15000,
            "id_tiny": 123,
            "status": "processing",
        }

        with test_engine.begin() as connection:
            insert_new_transaction(first_receipt, connection)

        with test_engine.begin() as connection:
            insert_new_transaction(second_receipt, connection)

        with test_engine.connect() as connection:
            rows = connection.execute(
                select(tb_tratoray_transactions).where(
                    tb_tratoray_transactions.c.id_tiny == 123
                )
            ).mappings().all()

        assert len(rows) == 2
        assert {row["status"] for row in rows} == {
            "processed",
            "processing",
        }

    finally:
        test_engine.dispose()

