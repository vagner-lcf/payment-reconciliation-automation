from pathlib import Path
from sqlalchemy import (
    create_engine,
    MetaData, 
    Table, 
    Column, 
    Integer, 
    String, 
    DateTime, 
    CheckConstraint, 
    UniqueConstraint, 
    func, 
    insert, 
    select,
    update,
    Engine,
    Connection,
    )


ROOT_DIR = Path(__file__).resolve().parent.parent
DB_FOLDER = ROOT_DIR / "data" / "database"
DB_FOLDER.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_FOLDER / "tratoray_transactions.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


metadata = MetaData()

tb_tratoray_transactions = Table(
    "tratoray_transactions",
    metadata,
    Column("id",            Integer,            primary_key=True),
    Column("file_hash",     String,             nullable=False,             unique=True),
    Column("provider",     String),
    Column("provider_transaction_id",     String),
    Column("pix_transaction_id",     String,          unique=True),
    Column("authentication_code",     String),
    Column("amount",     Integer),
    Column("id_tiny",     Integer),
    Column("status",     String,            nullable=False),
    Column("created_at",     DateTime,          nullable=False,         server_default=func.current_timestamp()),

    CheckConstraint(
        "status IN ('processing','processed', 'review_required')",
        name="ck_tratoray_transactions_status"
    ),
    UniqueConstraint(
        "provider",
        "provider_transaction_id",
        name="uq_tratoray_transactions_provider_transaction_id"
    )
)


def create_tables(db_engine) -> None:
    metadata.create_all(db_engine)

def find_existing_transaction(
    transaction_data: dict,
    db_connection: Connection
) -> dict | None:

    file_hash = transaction_data.get("file_hash")

    file_hash_stmt = (
        select(tb_tratoray_transactions)
        .where(tb_tratoray_transactions.c.file_hash == file_hash)
    )
    file_hash_result = db_connection.execute(file_hash_stmt)
    file_hash_row = file_hash_result.fetchone()

    if file_hash_row is not None:
        return dict(file_hash_row._mapping)

    if transaction_data.get("pix_transaction_id"):
        pix_transaction_id = transaction_data.get("pix_transaction_id")

        pix_transaction_stmt = (
            select(tb_tratoray_transactions)
            .where(
                tb_tratoray_transactions.c.pix_transaction_id
                == pix_transaction_id
            )
        )
        pix_transaction_result = db_connection.execute(pix_transaction_stmt)
        pix_transaction_row = pix_transaction_result.fetchone()

        if pix_transaction_row is not None:
            return dict(pix_transaction_row._mapping)

    elif (
        transaction_data.get("provider")
        and transaction_data.get("provider_transaction_id")
    ):
        provider = transaction_data.get("provider")
        provider_transaction_id = transaction_data.get(
            "provider_transaction_id"
        )

        provider_transaction_stmt = (
            select(tb_tratoray_transactions)
            .where(tb_tratoray_transactions.c.provider == provider)
            .where(
                tb_tratoray_transactions.c.provider_transaction_id
                == provider_transaction_id
            )
        )
        provider_transaction_result = db_connection.execute(
            provider_transaction_stmt
        )
        provider_transaction_row = provider_transaction_result.fetchone()

        if provider_transaction_row is not None:
            return dict(provider_transaction_row._mapping)

    return None

def insert_new_transaction(
    transaction_data: dict,
    db_connection: Connection,
) -> int:
    insert_stmt = insert(tb_tratoray_transactions).values(transaction_data)
    
    result = db_connection.execute(insert_stmt)
    
    transaction_id = result.inserted_primary_key[0]

    return transaction_id

def mark_transaction_as_processed(
    transaction_id: int,
    db_connection: Connection,
) -> bool:
    update_stmt = (
        update(tb_tratoray_transactions)
        .where(tb_tratoray_transactions.c.id == transaction_id)
        .values(status="processed")
    )
    
    result = db_connection.execute(update_stmt)
    
    return result.rowcount == 1


