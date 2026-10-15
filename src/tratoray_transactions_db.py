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

    # ---------------------------------------------------------
    # 1. HASH DO ARQUIVO — PRIMEIRA BARREIRA
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
    # 2. IDENTIFICADORES FINANCEIROS
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

    # Busca pelo ID Pix
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

    # Busca pelo ID do provedor, independentemente do Pix
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

    # Nenhum identificador encontrado
    if pix_row is None and provider_row is None:
        return None

    # ---------------------------------------------------------
    # 3. IDENTIFICAÇÃO DE CONFLITOS
    # ---------------------------------------------------------

    existing = dict(
        pix_row if pix_row is not None else provider_row
    )

    identity_conflict = False

    # Caso A:
    # Pix e ID do provedor apontam para registros diferentes.
    if pix_row is not None and provider_row is not None:
        if pix_row["id"] != provider_row["id"]:
            identity_conflict = True

    # Caso B:
    # ID Pix informado diverge do ID Pix armazenado.
    if (
        pix_transaction_id
        and existing["pix_transaction_id"]
    ):
        if pix_transaction_id != existing["pix_transaction_id"]:
            identity_conflict = True

    # Caso C:
    # Identidade do provedor informada diverge da armazenada.
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

    # Campo calculado, não persistido no SQLite
    existing["identity_conflict"] = identity_conflict

    return existing

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
        .where(tb_tratoray_transactions.c.status == "processing")
        .values(status="processed")
    )

    result = db_connection.execute(update_stmt)

    return result.rowcount == 1

def find_pending_transaction_by_tiny_id(
    id_tiny: int,
    db_connection: Connection,
) -> dict | None:
    """Find an inconclusive settlement linked to a Tiny account."""
    stmt = (
        select(tb_tratoray_transactions)
        .where(tb_tratoray_transactions.c.id_tiny == id_tiny)
        .where(tb_tratoray_transactions.c.status == "processing")
    )

    row = db_connection.execute(stmt).mappings().first()

    return dict(row) if row is not None else None

