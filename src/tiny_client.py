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
        response = requests.get(accounts_payable_url, headers=headers, params=query_params, timeout=10)
        response.raise_for_status()

    except requests.RequestException as e:
        print("Erro ao buscar contas a pagar:", e)
        return None

    accounts_payable_data = response.json()

    return accounts_payable_data

def get_all_accounts_payable(
    access_token: str,
    status: str | None = None,
    initial_due_date: str | None = None,
    final_due_date: str | None = None,
    limit: int = 100,
) -> dict | None:
    """Busca todas as páginas de contas a pagar do Tiny."""

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
        id_account: int) -> list[dict] | None:

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    account_payable_by_id_url = (
        f"https://api.tiny.com.br/public-api/v3/contas-pagar/{id_account}"
        )

    try:
        response = requests.get(account_payable_by_id_url, headers=headers, timeout=10)
        response.raise_for_status()

    except requests.RequestException as e:
        print("Erro ao buscar conta a pagar pelo ID:", e)
        return None

    account_payable_data_by_id = response.json()

    return account_payable_data_by_id

def get_account_payable_payments(
        access_token,
        id_account: int) -> list[dict] | None:
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    account_payable_payments_url = (
        f"https://api.tiny.com.br/public-api/v3/contas-pagar/{id_account}/recebimentos"
        )

    try:
        response = requests.get(account_payable_payments_url, headers=headers, timeout=10)
        response.raise_for_status()

    except requests.RequestException as e:
        print("Erro ao buscar conta a pagar pelo ID:", e)
        return None

    account_payable_payments = response.json()

    return account_payable_payments

def settle_account_payable(
    access_token: str,
    id_account: int,
    payment_date: date,
    amount: Decimal,
) -> bool:
    
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

