from datetime import date, timedelta
from decimal import Decimal


def calculate_due_date_window(payment_date: date, range_days: int = 15) -> tuple[str, str]:
    initial_due_date = payment_date - timedelta(days=range_days)
    final_due_date = payment_date + timedelta(days=range_days)

    return initial_due_date.strftime("%Y-%m-%d"), final_due_date.strftime("%Y-%m-%d")

def find_matching_accounts(
        accounts_payable_data: dict,
        beneficiary_document: str,
        payment_amount: Decimal) -> list[dict]:
    
    matching_accounts = []

    for account in accounts_payable_data.get("itens", []):
        account_beneficiary_document = account.get("cliente", {}).get("cpfCnpj", "")
        account_payment_amount = Decimal(str(account.get("saldo", "0")))

        if account_beneficiary_document and account_beneficiary_document == beneficiary_document and account_payment_amount == payment_amount:
                matching_accounts.append(account)       

    return matching_accounts

def classify_matching_result(
        matching_accounts: list[dict]
        ) -> str:
    if len(matching_accounts) == 1:
        return "unique_match"

    elif len(matching_accounts) == 0:
        return "no_match"

    else:
        return "ambiguous"

def summarize_accounts(
        matching_accounts: list[dict],
        ) -> list[dict]:    
    accounts_data = []
    for account in matching_accounts:
        account_id = account.get("id")

        name = account.get("cliente", {}).get("nome")

        beneficiary_document = account.get("cliente", {}).get("cpfCnpj")

        amount = account.get("saldo")

        due_date = account.get("dataVencimento")

        account_data_dict = {
            "ID": account_id,
            "Fornecedor": name,
            "CPF/CNPJ": beneficiary_document,
            "Saldo": amount,
            "Data Vencimento": due_date
            }

        accounts_data.append(account_data_dict)

    return accounts_data

