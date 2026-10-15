from decimal import Decimal
from pathlib import Path
from datetime import date


from src.auth import (
    build_authorization_url,
    exchange_code_for_token,
)

from src.callback import wait_for_authorization_code

from src.matching import (
    calculate_due_date_window,
    classify_matching_result,
    find_matching_accounts,
    summarize_accounts,
)

from src.tiny_client import (
    get_all_accounts_payable,
    get_account_payable_by_id,
    settle_account_payable,
)

from src.tratoray_transactions_db import (
    engine,
    create_tables,
    find_existing_transaction,
    insert_new_transaction,
    mark_transaction_as_processed,
)

from src.receipt_parser import (
    extract_receipt_data,
)

from src.receipt_hash_extractor import extract_receipt_hash

from src.pdf_text_extractor import extract_text_from_pdf
from src.image_text_extractor import extract_text_from_image


def make_result(
    status: str,
    message: str,
    beneficiary_document: str | None = None,
    payment_date: date | None = None,
    amount: Decimal | None = None,
    transaction_id: int | None = None,
    id_tiny: int | None = None,
    reason: str | None = None,
) -> dict:
    return {
        "status": status,
        "message": message,
        "beneficiary_document": (
            "".join(char for char in beneficiary_document if char.isdigit())
            if beneficiary_document
            else None
        ),
        "payment_date": payment_date,
        "amount": amount,
        "transaction_id": transaction_id,
        "id_tiny": id_tiny,
        "reason": reason,
    }

def is_account_settled(account: dict) -> bool:
    balance = account.get("saldo")

    if balance is None:
        return False

    return (
        account.get("situacao") == "pago"
        and Decimal(str(balance)) == Decimal("0")
    )

def reconcile_existing_transaction(
            existing_transaction: dict,
            access_token: str,
            db_engine,
        ) -> str:

            if existing_transaction["status"] == "processed":
                return "already_processed"

            if existing_transaction["status"] == "processing":
                account_tiny = get_account_payable_by_id(
                    access_token=access_token,
                    id_account=existing_transaction["id_tiny"]
                )

                if account_tiny is None:
                    return "verification_failed"

                account_is_settled = is_account_settled(
                    account=account_tiny
                )

                if not account_is_settled:
                    return "not_settled"

                with db_engine.begin() as db_connection:
                    processed = mark_transaction_as_processed(
                        transaction_id=existing_transaction["id"],
                        db_connection=db_connection,
                    )   
                if not processed:
                    return "local_update_failed"

                return "reconciled"

            if existing_transaction["status"] == "review_required":
                return "review_required"

            return "unexpected_status"


def main(file_path: str, settlement_enabled: bool = False):
    # ---------------------------------------------------------
    # PREPARAÇÃO DO BANCO LOCAL
    # ---------------------------------------------------------
    create_tables(engine)

    # ---------------------------------------------------------
    # EXTRAÇÃO DE TEXTO POR TIPO DE ARQUIVO
    # ---------------------------------------------------------

    file_extension = Path(file_path).suffix.lower()

    if file_extension == ".pdf":
        source_type = "pdf"
        text = extract_text_from_pdf(file_path)

    elif file_extension in (".png", ".jpg", ".jpeg"):
        source_type = "image"
        text = extract_text_from_image(file_path)

    else:
        raise ValueError(
            f"Formato de comprovante não suportado: {file_extension}"
        )

    receipt_data = extract_receipt_data(
        text,
        source_type=source_type,
    )

    file_hash = extract_receipt_hash(file_path)

    payment = receipt_data | {
        "file_hash": file_hash,
    }

    def finish(
        status: str,
        message: str,
        transaction_id: int | None = None,
        id_tiny: int | None = None,
        reason: str | None = None,
    ) -> dict:
        print(message)

        return make_result(
            status=status,
            message=message,
            beneficiary_document=payment.get("beneficiary_document"),
            payment_date=payment.get("payment_date"),
            amount=payment.get("amount"),
            transaction_id=transaction_id,
            id_tiny=id_tiny,
            reason=reason,
        )

    # ---------------------------------------------------------
    # IDENTIDADE / IDEMPOTÊNCIA LOCAL
    # ---------------------------------------------------------
    transaction_identity = {
        "file_hash": payment["file_hash"],
        "provider": payment["provider"],
        "provider_transaction_id": payment["provider_transaction_id"],
        "pix_transaction_id": payment["pix_transaction_id"],
    }

    with engine.begin() as db_connection:
        existing_transaction = find_existing_transaction(
            transaction_data=transaction_identity,
            db_connection=db_connection,
        )

    # ---------------------------------------------------------
    # ESTADOS QUE PODEM SER RESOLVIDOS LOCALMENTE
    # ---------------------------------------------------------
    if existing_transaction is not None:

        if existing_transaction.get("identity_conflict", False):
            return finish(
                status="review_required",
                message=(
                    "Conflito entre identificadores financeiros. "
                    "Operação bloqueada para revisão manual. "
                    "Nenhuma consulta ou baixa será realizada no Tiny."
                ),
                reason="identity_conflict",
            )

        existing_status = existing_transaction["status"]

        if existing_status == "processed":
            return finish(
                status="already_processed",
                message="Transação já processada.",
                transaction_id=existing_transaction["id"],
            )

        if existing_status == "review_required":
            return finish(
                status="already_in_review",
                message=(
                    "Transação já registrada para revisão manual. "
                    "Nenhuma baixa automática será realizada."
                ),
                transaction_id=existing_transaction["id"],
            )

    # ---------------------------------------------------------
    # ELEGIBILIDADE PARA PROCESSAMENTO AUTOMÁTICO
    # ---------------------------------------------------------

    # Avaliação apenas de transações novas.
    # Transações existentes seguem as regras de idempotência
    # e reconciliação já implementadas.

    if existing_transaction is None:

        image_ineligible = (
            source_type == "image"
            and (
                payment["receipt_layout"] not in (
                    "mp_pag_bol",
                    "mp_pix_bol",
                )
                or payment["amount_matches_barcode"] is not True
            )
        )

        missing_required_data = (
            payment["provider"] != "mercado_pago"
            or payment["beneficiary_document"] is None
            or payment["amount"] is None
            or payment["payment_date"] is None
        )

        if image_ineligible or missing_required_data:

            transaction_data = {
                "file_hash": payment["file_hash"],
                "provider": payment["provider"],
                "provider_transaction_id": payment[
                    "provider_transaction_id"
                ],
                "pix_transaction_id": payment["pix_transaction_id"],
                "amount": (
                    int(payment["amount"] * 100)
                    if payment["amount"] is not None
                    else None
                ),
                "status": "review_required",
            }

            with engine.begin() as db_connection:
                transaction_id = insert_new_transaction(
                    transaction_data=transaction_data,
                    db_connection=db_connection,
                )

            return finish(
                status="review_required",
                message=(
                    "Comprovante não elegível para baixa automática. "
                    "Transação registrada para revisão manual. "
                    f"ID local: {transaction_id}"
                ),
                transaction_id=transaction_id,
            )

    # ---------------------------------------------------------
    # GERAÇÃO DE TOKEN DE ACESSO E AUTENTICAÇÃO
    # ---------------------------------------------------------
    # Só chegamos ao OAuth quando realmente precisamos consultar
    # ou alterar alguma informação no Tiny.
    authorization_url = build_authorization_url()

    print(
        f"Acesse o seguinte URL para autorizar o aplicativo:\n"
        f"{authorization_url}"
    )

    authorization_code = wait_for_authorization_code()

    if authorization_code is None:
        return finish(
            status="error",
            message="Falha ao obter o código de autorização.",
            reason="authorization_code_missing",
        )

    token_data = exchange_code_for_token(authorization_code)

    if token_data is None:
        return finish(
            status="error",
            message="Falha ao obter o token de acesso.",
            reason="token_exchange_failed",
        )

    access_token = token_data.get("access_token")

    if access_token is None:
        return finish(
            status="error",
            message="Falha ao obter o access token.",
            reason="access_token_missing",
        )

    # ---------------------------------------------------------
    # CAMINHO 1: TRANSAÇÃO EXISTENTE EM PROCESSING
    # ---------------------------------------------------------
    # processed e review_required já foram tratados localmente.
    # Uma transação existente que chegou até aqui precisa de
    # reconciliação com o Tiny.
    if existing_transaction is not None:
        reconciliation_result = reconcile_existing_transaction(
            existing_transaction=existing_transaction,
            access_token=access_token,
            db_engine=engine,
        )

        reconciliation_messages = {
            "already_processed": (
                "Transação já processada."
            ),
            "reconciled": (
                "Baixa já confirmada no Tiny. "
                "Transação reconciliada como processed."
            ),
            "verification_failed": (
                "Não foi possível verificar o estado da conta no Tiny. "
                "Transação permanece como processing."
            ),
            "not_settled": (
                "A conta ainda não consta como liquidada no Tiny. "
                "Retry automático não autorizado. "
                "Transação permanece como processing."
            ),
            "local_update_failed": (
                "Baixa confirmada no Tiny, mas não foi possível atualizar "
                "o estado local. A transação deve ser verificada."
            ),
            "review_required": (
                "Transação marcada para revisão manual. "
                "Nenhuma baixa automática será realizada."
            ),
            "unexpected_status": (
                "Status local inesperado. "
                "A transação não será processada."
            ),
        }
        reconciliation_status = {
            "already_processed": "already_processed",
            "reconciled": "processed",
            "verification_failed": "verification_pending",
            "not_settled": "verification_pending",
            "local_update_failed": "verification_pending",
            "review_required": "review_required",
            "unexpected_status": "error",
        }

        return finish(
            status=reconciliation_status[reconciliation_result],
            message=reconciliation_messages[reconciliation_result],
            transaction_id=existing_transaction["id"],
            id_tiny=existing_transaction.get("id_tiny"),
            reason=reconciliation_result,
        )

    # ---------------------------------------------------------
    # BUSCA DE CANDIDATOS NO TINY
    # ---------------------------------------------------------
    initial_due_date, final_due_date = calculate_due_date_window(
        payment["payment_date"]
    )

    accounts_payable_data = get_all_accounts_payable(
        access_token,
        status="aberto",
        initial_due_date=initial_due_date,
        final_due_date=final_due_date,
    )

    if accounts_payable_data is None:
        return finish(
            status="error",
            message="Falha ao obter dados das contas a pagar.",
            reason="accounts_fetch_failed",
        )

    # ---------------------------------------------------------
    # MATCHING
    # ---------------------------------------------------------
    matching_accounts = find_matching_accounts(
        accounts_payable_data,
        payment["beneficiary_document"],
        payment["amount"],
    )

    classification = classify_matching_result(
        matching_accounts=matching_accounts,
    )

    if classification == "no_match":
        return finish(
            status="no_match",
            message=(
                "Nenhuma conta localizada para o comprovante. "
                "Verifique CPF/CNPJ, valor e data no Tiny."
            ),
        )

    accounts_data = summarize_accounts(
        matching_accounts=matching_accounts,
    )

    if classification == "ambiguous":
        return finish(
            status="ambiguous_match",
            message=(
                "Múltiplas contas localizadas para o comprovante. "
                "É necessária conferência manual.\n"
                f"{accounts_data}"
            ),
        )

    # ---------------------------------------------------------
    # UNIQUE MATCH
    # ---------------------------------------------------------
    matched_account = matching_accounts[0]
    id_tiny = matched_account["id"]

    print("Conta correspondente localizada:")
    print(accounts_data)

    # ---------------------------------------------------------
    # DADOS PARA PERSISTÊNCIA
    # ---------------------------------------------------------
    transaction_data = {
        "file_hash": payment["file_hash"],
        "provider": payment["provider"],
        "provider_transaction_id": payment[
            "provider_transaction_id"
        ],
        "pix_transaction_id": payment["pix_transaction_id"],
        "amount": int(payment["amount"] * 100),
        "id_tiny": id_tiny,
        "status": "processing",
    }

    # ---------------------------------------------------------
    # BARREIRA DE ESCRITA
    # ---------------------------------------------------------
    if not settlement_enabled:
        return finish(
            status="dry_run",
            message=(
                "Conta correspondente localizada, mas a baixa "
                "automática está desabilitada."
            ),
            id_tiny=id_tiny,
        )

    # ---------------------------------------------------------
    # CAMINHO 2: TRANSAÇÃO NOVA
    # ---------------------------------------------------------
    # Registra processing ANTES de qualquer operação financeira.
    with engine.begin() as db_connection:
        transaction_id = insert_new_transaction(
            transaction_data=transaction_data,
            db_connection=db_connection,
        )

    print(
        "Transação registrada localmente como processing. "
        f"ID local: {transaction_id}"
    )

    # ---------------------------------------------------------
    # ESCRITA NO TINY
    # ---------------------------------------------------------
    success = settle_account_payable(
        access_token=access_token,
        id_account=id_tiny,
        payment_date=payment["payment_date"],
        amount=payment["amount"],
    )

    if not success:
        return finish(
            status="verification_pending",
            message=(
                "Não foi possível confirmar a baixa. "
                "Transação permanece como processing."
            ),
            transaction_id=transaction_id,
            id_tiny=id_tiny,
            reason="settlement_request_failed",
        )

    # ---------------------------------------------------------
    # CONFIRMAÇÃO DA BAIXA NO TINY
    # ---------------------------------------------------------
    account_after_settlement = get_account_payable_by_id(
        access_token=access_token,
        id_account=id_tiny,
    )

    if account_after_settlement is None:
        return finish(
            status="verification_pending",
            message=(
                "Não foi possível consultar o estado da conta após a baixa. "
                "Transação permanece como processing."
            ),
            transaction_id=transaction_id,
            id_tiny=id_tiny,
            reason="post_settlement_fetch_failed",
        )

    settlement_confirmed = is_account_settled(
        account=account_after_settlement,
    )

    if not settlement_confirmed:
        return finish(
            status="verification_pending",
            message=(
                "O Tiny não confirmou a liquidação da conta. "
                "Transação permanece como processing."
            ),
            transaction_id=transaction_id,
            id_tiny=id_tiny,
            reason="settlement_not_confirmed",
        )

    # ---------------------------------------------------------
    # CONFIRMAÇÃO LOCAL
    # ---------------------------------------------------------
    with engine.begin() as db_connection:
        processed = mark_transaction_as_processed(
            transaction_id=transaction_id,
            db_connection=db_connection,
        )

    if not processed:
        return finish(
            status="verification_pending",
            message=(
                "Baixa confirmada no Tiny, mas houve falha ao atualizar "
                "o estado local. A transação deve ser verificada."
            ),
            transaction_id=transaction_id,
            id_tiny=id_tiny,
            reason="local_update_failed",
        )

    return finish(
        status="processed",
        message=(
            "Baixa confirmada no Tiny e transação marcada "
            "localmente como processed."
        ),
        transaction_id=transaction_id,
        id_tiny=id_tiny,
    )

if __name__ == "__main__":
    main(
        file_path="data/input/pag_bol_1.jpeg",
        settlement_enabled=False,
    )


