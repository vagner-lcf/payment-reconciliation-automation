from datetime import date, timedelta
from decimal import Decimal
import re


def calculate_due_date_window(
    payment_date: date,
    range_days: int = 10,
) -> tuple[str, str]:
    """Calculate the Tiny due-date search window around a payment date.

    The default window is ten calendar days before and after the
    payment date, based on the client's observed payment practices.

    The window limits candidate retrieval but does not guarantee
    a unique match. Ambiguous matches require manual review.

    Args:
        payment_date: Payment date extracted from the receipt.
        range_days: Number of calendar days on each side of the
            payment date. Defaults to 10.

    Returns:
        The initial and final due dates formatted as YYYY-MM-DD.
    """

    initial_due_date = payment_date - timedelta(days=range_days)
    final_due_date = payment_date + timedelta(days=range_days)

    return initial_due_date.strftime("%Y-%m-%d"), final_due_date.strftime("%Y-%m-%d")

def find_matching_accounts(
    accounts_payable_data: dict,
    beneficiary_document: str,
    payment_amount: Decimal
) -> list[dict]:
    """Find payable accounts matching the receipt's beneficiary and amount.

    Normalize CPF/CNPJ identifiers by removing non-digit characters.
    A candidate matches only when its beneficiary document equals the
    receipt's beneficiary document and its outstanding balance equals
    the payment amount.

    The due-date window is applied when retrieving accounts from Tiny,
    not by this function.

    Returns:
        A list of matching payable accounts, possibly empty.
    """

    matching_accounts = []

    normalized_beneficiary_document = re.sub(r"\D", "", beneficiary_document)

    for account in accounts_payable_data.get("itens", []):
        account_beneficiary_document = account.get("cliente", {}).get("cpfCnpj", "")
        account_payment_amount = Decimal(str(account.get("saldo", "0")))

        normalized_account_document = re.sub(r"\D", "", account_beneficiary_document)

        if (
            normalized_beneficiary_document
            and normalized_account_document == normalized_beneficiary_document
            and account_payment_amount == payment_amount
        ):
            matching_accounts.append(account)

    return matching_accounts

def classify_matching_result(
    matching_accounts: list[dict]
) -> str:
    """Classify a matching result based on the number of candidates.

    Returns:
        "unique_match" when exactly one account matches,
        "no_match" when no accounts match, or
        "ambiguous" when multiple accounts match.
    """

    if len(matching_accounts) == 1:
        return "unique_match"

    elif len(matching_accounts) == 0:
        return "no_match"

    else:
        return "ambiguous"

def summarize_accounts(
    matching_accounts: list[dict],
) -> list[dict]:
    """Build a readable summary of matching Tiny payable accounts.

    Extract account identifiers, supplier information, outstanding
    balances, and due dates for diagnostics and manual review.

    Returns:
        A list of dictionaries with Portuguese display labels.
    """

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
