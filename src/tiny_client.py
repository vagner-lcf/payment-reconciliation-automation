import requests
from datetime import date
from decimal import Decimal


def get_accounts_payable(
    access_token,
    status=None,
    initial_due_date=None,
    final_due_date=None,
    limit=100,
    offset=0
) -> dict | None:
    """Fetch one page of payable accounts from Tiny.

    Optional filters restrict results by account status and due-date range.
    The request uses a ten-second timeout.

    Returns:
        The decoded JSON response, or None if the HTTP request fails.

    Note:
        JSON decoding errors are not currently handled by this function.
    """

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    accounts_payable_url = "https://api.tiny.com.br/public-api/v3/contas-pagar"
    query_params = {
        "limit": limit,
        "offset": offset
        }

    if status is not None:
        query_params["situacao"] = status

    if initial_due_date is not None:
        query_params["dataInicialVencimento"] = initial_due_date

    if final_due_date is not None:
        query_params["dataFinalVencimento"] = final_due_date

    try:
        response = requests.get(
            accounts_payable_url,
            headers=headers,
            params=query_params,
            timeout=10,
        )
        response.raise_for_status()
        accounts_payable_data = response.json()

    except requests.RequestException as e:
        print("Erro ao buscar contas a pagar:", e)
        return None

    return accounts_payable_data

def get_all_accounts_payable(
    access_token: str,
    status: str | None = None,
    initial_due_date: str | None = None,
    final_due_date: str | None = None,
    limit: int = 100,
) -> dict | None:
    """Fetch and validate all pages of payable accounts from Tiny.

    Retrieve pages sequentially and validate their item lists and
    pagination metadata before returning the combined result.

    Returns:
        A dictionary containing all accounts under the "itens" key,
        or None if a page fails validation or cannot be retrieved.

    Raises:
        ValueError: If limit is not greater than zero.
    """

    if limit <= 0:
        raise ValueError("limit deve ser maior que zero")

    all_accounts = []
    offset = 0

    while True:
        response = get_accounts_payable(
            access_token=access_token,
            status=status,
            initial_due_date=initial_due_date,
            final_due_date=final_due_date,
            limit=limit,
            offset=offset,
        )

        if not isinstance(response, dict):
            return None

        items = response.get("itens")
        pagination = response.get("paginacao")

        if not isinstance(items, list):
            return None

        if not all(isinstance(item, dict) for item in items):
            return None

        if not isinstance(pagination, dict):
            return None

        total = pagination.get("total")

        if type(total) is not int or total < 0:
            return None

        if len(items) > limit:
            return None

        all_accounts.extend(items)

        if len(all_accounts) >= total:
            if len(all_accounts) != total:
                return None

            return {"itens": all_accounts}

        if not items:
            return None

        offset += len(items)

def get_account_payable_by_id(
    access_token,
    id_account: int
) -> dict | None:
    """Fetch a payable account by its Tiny identifier.

    Returns:
        The account data as a dictionary, or None if the HTTP
        request fails.
    """

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    account_payable_by_id_url = (
        f"https://api.tiny.com.br/public-api/v3/contas-pagar/{id_account}"
        )

    try:
        response = requests.get(
            account_payable_by_id_url,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        account_payable_data_by_id = response.json()

    except requests.RequestException as e:
        print("Erro ao buscar conta a pagar pelo ID:", e)
        return None

    return account_payable_data_by_id

def get_account_payable_payments(
    access_token,
    id_account: int
) -> list[dict] | None:
    """Fetch payment records associated with a Tiny payable account.

    Returns:
        The decoded JSON response, or None if the HTTP request fails.

    Note:
        The response structure is not validated by this function.
    """
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    account_payable_payments_url = (
        f"https://api.tiny.com.br/public-api/v3/contas-pagar/{id_account}/recebimentos"
        )

    try:
        response = requests.get(account_payable_payments_url, headers=headers, timeout=10)
        response.raise_for_status()
        account_payable_payments = response.json()

    except requests.RequestException as e:
        print("Erro ao consultar os pagamentos da conta no Tiny: ", e)
        return None

    return account_payable_payments

def settle_account_payable(
    access_token: str,
    id_account: int,
    payment_date: date,
    amount: Decimal,
) -> bool:
    """Request financial settlement of a Tiny payable account.

    Send the payment date and amount to Tiny's settlement endpoint.
    A successful HTTP response indicates that the request was accepted,
    but does not independently confirm the account's final state.

    The caller must verify settlement through a subsequent account
    lookup before marking the local transaction as processed.

    Args:
        access_token: OAuth access token used for Tiny authentication.
        id_account: Identifier of the payable account.
        payment_date: Date of the payment recorded in the receipt.
        amount: Payment amount represented as Decimal.

    Returns:
        True if the HTTP request completes successfully; otherwise False.

    Warning:
        A failed or timed-out request may still have been applied remotely.
        Never retry settlement automatically without verifying Tiny's state.
    """

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    settle_account_payable_url = (
        f"https://api.tiny.com.br/public-api/v3/"
        f"contas-pagar/{id_account}/baixar"
    )

    formatted_payment_date = payment_date.strftime("%d/%m/%Y")
    formatted_amount = float(amount)

    payment_data = {
        "data": formatted_payment_date,
        "valorPago": formatted_amount,
    }

    try:
        response = requests.post(
            settle_account_payable_url,
            headers=headers,
            json=payment_data,
            timeout=10,
        )
        response.raise_for_status()

    except requests.RequestException as e:
        print("Erro ao liquidar a conta a pagar:", e)
        return False

    return True

