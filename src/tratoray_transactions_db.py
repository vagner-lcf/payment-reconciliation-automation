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
    """Create the local transaction tables if they do not exist."""

    metadata.create_all(db_engine)

def find_existing_transaction(
    transaction_data: dict,
    db_connection: Connection
) -> dict | None:
    """Find a transaction by file hash or financial identifiers.

    The file hash is checked first. If no matching file is found,
    Pix and provider transaction identifiers are checked independently.

    Conflicting financial identifiers are flagged with the calculated
    identity_conflict field. This field is not stored in SQLite.

    Returns:
        The existing transaction as a dictionary, optionally including
        identity_conflict, or None when no transaction is found.
    """
    # ---------------------------------------------------------
    # 1. FILE HASH — FIRST IDEMPOTENCY CHECK
    # ---------------------------------------------------------

    file_hash = transaction_data.get("file_hash")

    if file_hash:
        file_hash_stmt = (
            select(tb_tratoray_transactions)
            .where(tb_tratoray_transactions.c.file_hash == file_hash)
        )

        file_hash_row = db_connection.execute(
            file_hash_stmt
        ).mappings().first()

        if file_hash_row is not None:
            return dict(file_hash_row)

    # ---------------------------------------------------------
    # 2. FINANCIAL IDENTIFIERS
    # ---------------------------------------------------------

    pix_transaction_id = transaction_data.get(
        "pix_transaction_id"
    )

    provider = transaction_data.get("provider")

    provider_transaction_id = transaction_data.get(
        "provider_transaction_id"
    )

    pix_row = None
    provider_row = None

    # Look up the Pix transaction ID.
    if pix_transaction_id:
        pix_stmt = (
            select(tb_tratoray_transactions)
            .where(
                tb_tratoray_transactions.c.pix_transaction_id
                == pix_transaction_id
            )
        )

        pix_row = db_connection.execute(
            pix_stmt
        ).mappings().first()

    # Look up the provider transaction ID independently of Pix.
    if provider and provider_transaction_id:
        provider_stmt = (
            select(tb_tratoray_transactions)
            .where(
                tb_tratoray_transactions.c.provider == provider
            )
            .where(
                tb_tratoray_transactions.c.provider_transaction_id
                == provider_transaction_id
            )
        )

        provider_row = db_connection.execute(
            provider_stmt
        ).mappings().first()

    # No matching financial identifier was found.
    if pix_row is None and provider_row is None:
        return None

    # ---------------------------------------------------------
    # 3. IDENTITY CONFLICT DETECTION
    # ---------------------------------------------------------

    existing = dict(
        pix_row if pix_row is not None else provider_row
    )

    identity_conflict = False

    # Case A:
    # Pix and provider identifiers point to different records.
    if pix_row is not None and provider_row is not None:
        if pix_row["id"] != provider_row["id"]:
            identity_conflict = True

    # Case B:
    # The incoming Pix ID differs from the stored Pix ID.
    if (
        pix_transaction_id
        and existing["pix_transaction_id"]
    ):
        if pix_transaction_id != existing["pix_transaction_id"]:
            identity_conflict = True

    # Case C:
    # The incoming provider identity differs from the stored identity.
    if provider and provider_transaction_id:
        if (
            existing["provider"]
            and existing["provider_transaction_id"]
        ):
            if (
                provider != existing["provider"]
                or provider_transaction_id
                != existing["provider_transaction_id"]
            ):
                identity_conflict = True

    # Calculated field; not persisted in SQLite.
    existing["identity_conflict"] = identity_conflict

    return existing

def insert_new_transaction(
    transaction_data: dict,
    db_connection: Connection,
) -> int:
    """Insert a transaction and return its generated local ID.

    The caller is responsible for managing the database transaction.
    Database constraint violations are propagated to the caller.
    """

    insert_stmt = insert(tb_tratoray_transactions).values(transaction_data)
    
    result = db_connection.execute(insert_stmt)
    
    transaction_id = result.inserted_primary_key[0]

    return transaction_id

def mark_transaction_as_processed(
    transaction_id: int,
    db_connection: Connection,
) -> bool:
    """Mark a transaction as processed only if it is still processing.

    Returns:
        True if exactly one transaction was updated; otherwise False.
    """

    update_stmt = (
        update(tb_tratoray_transactions)
        .where(tb_tratoray_transactions.c.id == transaction_id)
        .where(tb_tratoray_transactions.c.status == "processing")
        .values(status="processed")
    )

    result = db_connection.execute(update_stmt)

    return result.rowcount == 1

def find_pending_transaction_by_tiny_id(
    id_tiny: int,
    db_connection: Connection,
) -> dict | None:
    """Find a processing transaction associated with a Tiny account.

    A pending transaction must be investigated before another settlement
    can be requested for the same account.

    Returns:
        The pending transaction as a dictionary, or None if not found.
    """

    stmt = (
        select(tb_tratoray_transactions)
        .where(tb_tratoray_transactions.c.id_tiny == id_tiny)
        .where(tb_tratoray_transactions.c.status == "processing")
    )

    row = db_connection.execute(stmt).mappings().first()

    return dict(row) if row is not None else None
