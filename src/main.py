from decimal import Decimal

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
    get_accounts_payable,
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


def main(write_enabled: bool = False):
    # ---------------------------------------------------------
    # PREPARAÇÃO DO BANCO LOCAL
    # ---------------------------------------------------------
    create_tables(engine)

    # ---------------------------------------------------------
    # EXTRAÇÃO DE DADOS DO COMPROVANTE
    # ---------------------------------------------------------
    file_path_boleto = (
        "data/input/boleto.pdf"
    )
    file_path_test_1 = (
        "data/input/teste1.pdf"
    )
    file_path_test_2 = (
        "data/input/teste2.pdf"
    )
    file_path_test_3 = (
        "data/input/teste3.pdf"
    )

    file_path = file_path_test_1

    text = extract_text_from_pdf(file_path)
    receipt_data = extract_receipt_data(text)
    file_hash = extract_receipt_hash(file_path)

    payment = receipt_data | {
        "file_hash": file_hash,
    }

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
        existing_status = existing_transaction["status"]

        if existing_status == "processed":
            print("Transação já processada.")
            return

        if existing_status == "review_required":
            print(
                "Transação já registrada para revisão manual. "
                "Nenhuma baixa automática será realizada."
            )
            return

    # ---------------------------------------------------------
    # ELEGIBILIDADE PARA PROCESSAMENTO AUTOMÁTICO
    # ---------------------------------------------------------
    # Sem documento completo do beneficiário, não existe informação
    # suficiente para aplicar o matching determinístico atual.
    if (
        existing_transaction is None
        and payment["beneficiary_document"] is None
    ):
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

        print(
            "Documento do beneficiário indisponível. "
            "Transação registrada para revisão manual. "
            f"ID local: {transaction_id}"
        )
        return

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
        print("Falha ao obter o código de autorização.")
        return

    token_data = exchange_code_for_token(authorization_code)

    if token_data is None:
        return

    access_token = token_data.get("access_token")

    if access_token is None:
        print("Falha ao obter o access token.")
        return

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

        print(reconciliation_messages[reconciliation_result])
        return

    # ---------------------------------------------------------
    # BUSCA DE CANDIDATOS NO TINY
    # ---------------------------------------------------------
    initial_due_date, final_due_date = calculate_due_date_window(
        payment["payment_date"]
    )

    accounts_payable_data = get_accounts_payable(
        access_token,
        status="aberto",
        initial_due_date=initial_due_date,
        final_due_date=final_due_date,
    )

    if accounts_payable_data is None:
        print("Falha ao obter dados das contas a pagar.")
        return

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
        print("Nenhuma conta localizada para o comprovante.")
        return

    accounts_data = summarize_accounts(
        matching_accounts=matching_accounts,
    )

    if classification == "ambiguous":
        print(
            "Múltiplas contas localizadas para o comprovante. "
            "Dados das contas a seguir:"
        )
        print(accounts_data)
        return

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
    if not write_enabled:
        print(
            "Modo somente leitura: nenhuma alteração será realizada "
            "no banco local ou no Tiny."
        )
        return

    # ---------------------------------------------------------
    # TRAVA TEMPORÁRIA PARA TESTE CONTROLADO
    # ---------------------------------------------------------
    allowed_account_id = 123

    if id_tiny != allowed_account_id:
        print(
            "Escrita bloqueada: a conta localizada não é "
            "a conta autorizada para este teste."
        )
        return

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
        print(
            "Não foi possível confirmar a baixa. "
            "Transação permanece como processing."
        )
        return

    # ---------------------------------------------------------
    # CONFIRMAÇÃO DA BAIXA NO TINY
    # ---------------------------------------------------------
    account_after_settlement = get_account_payable_by_id(
        access_token=access_token,
        id_account=id_tiny,
    )

    if account_after_settlement is None:
        print(
            "Não foi possível consultar o estado da conta após a baixa. "
            "Transação permanece como processing."
        )
        return

    settlement_confirmed = is_account_settled(
        account=account_after_settlement,
    )

    if not settlement_confirmed:
        print(
            "O Tiny não confirmou a liquidação da conta. "
            "Transação permanece como processing."
        )
        return

    # ---------------------------------------------------------
    # CONFIRMAÇÃO LOCAL
    # ---------------------------------------------------------
    with engine.begin() as db_connection:
        processed = mark_transaction_as_processed(
            transaction_id=transaction_id,
            db_connection=db_connection,
        )

    if not processed:
        print(
            "Baixa confirmada no Tiny, mas houve falha ao atualizar "
            "o estado local. A transação permanece inconsistente "
            "e deve ser verificada."
        )
        return

    print(
        "Baixa confirmada no Tiny e transação marcada "
        "localmente como processed."
    )

if __name__ == "__main__":
    main()


