from src.matching import find_matching_accounts, calculate_due_date_window
from decimal import Decimal
from datetime import date


def test_find_one_matching_account():
    # Exemplo de contas a pagar
    contas = {"itens": [
        {
            "id": 1,
            "cliente":{"cpfCnpj": "11.111.111/0001-11"},
            "saldo": 100.0
        },
        {
            "id": 2,
            "cliente":{"cpfCnpj": "22.222.222/0001-22"},
            "saldo": 200.0
        },
        {
            "id": 3,
            "cliente":{"cpfCnpj": "11.111.111/0001-11"},
            "saldo": 100.0
        }]}

    # Exemplo de pagamento a ser verificado
    payment = {
    "payment_date": "2026-09-20",
    "beneficiary_document": "22.222.222/0001-22",
    "amount": Decimal("200.00")
    }

    matching_accounts = find_matching_accounts(contas, payment["beneficiary_document"], payment["amount"])

    assert len(matching_accounts) == 1

    assert matching_accounts[0]["id"] == 2


def test_find_zero_matching_account():
    # Exemplo de contas a pagar
    contas = {"itens": [
        {
            "id": 1,
            "cliente":{"cpfCnpj": "11.111.111/0001-11"},
            "saldo": 100.0
        },
        {
            "id": 2,
            "cliente":{"cpfCnpj": "22.222.222/0001-22"},
            "saldo": 200.0
        },
        {
            "id": 3,
            "cliente":{"cpfCnpj": "11.111.111/0001-11"},
            "saldo": 100.0
        }]}

    # Exemplo de pagamento a ser verificado
    payment = {
    "payment_date": "2026-09-20",
    "beneficiary_document": "22.222.222/0001-22",
    "amount": Decimal("250.00")
    }

    matching_accounts = find_matching_accounts(contas, payment["beneficiary_document"], payment["amount"])

    assert matching_accounts == []


def test_find_multiple_matching_accounts():
    # Exemplo de contas a pagar
    contas = {"itens": [
        {
            "id": 1,
            "cliente":{"cpfCnpj": "11.111.111/0001-11"},
            "saldo": 100.0
        },
        {
            "id": 2,
            "cliente":{"cpfCnpj": "22.222.222/0001-22"},
            "saldo": 200.0
        },
        {
            "id": 3,
            "cliente":{"cpfCnpj": "11.111.111/0001-11"},
            "saldo": 100.0
        }]}

    # Exemplo de pagamento a ser verificado
    payment = {
    "payment_date": "2026-09-20",
    "beneficiary_document": "11.111.111/0001-11",
    "amount": Decimal("100.00")
    }

    matching_accounts = find_matching_accounts(contas, payment["beneficiary_document"], payment["amount"])

    assert len(matching_accounts) == 2
    assert matching_accounts[0]["id"] == 1
    assert matching_accounts[1]["id"] == 3


def test_empty_document_does_not_match():
    # Exemplo de contas a pagar
    contas = {"itens": [
        {
            "id": 1,
            "cliente":{"cpfCnpj": "11.111.111/0001-11"},
            "saldo": 100.0
        },
        {
            "id": 2,
            "cliente":{"cpfCnpj": ""},
            "saldo": 200.0
        },
        {
            "id": 3,
            "cliente":{"cpfCnpj": "11.111.111/0001-11"},
            "saldo": 100.0
        }]}

    # Exemplo de pagamento a ser verificado
    payment = {
    "payment_date": "2026-09-20",
    "beneficiary_document": "",
    "amount": Decimal("200.00")
    }

    matching_accounts = find_matching_accounts(contas, payment["beneficiary_document"], payment["amount"])

    assert matching_accounts == []


def test_find_one_float_matching_account():
    # Exemplo de contas a pagar
    contas = {"itens": [
        {
            "id": 1,
            "cliente":{"cpfCnpj": "22.222.222/0001-22"},
            "saldo": 200.1
        }]}

    # Exemplo de pagamento a ser verificado
    payment = {
    "payment_date": "2026-09-20",
    "beneficiary_document": "22.222.222/0001-22",
    "amount": Decimal("200.10")
    }

    matching_accounts = find_matching_accounts(contas, payment["beneficiary_document"], payment["amount"])

    assert len(matching_accounts) == 1
    assert matching_accounts[0]["id"] == 1


def test_unique_match_with_same_document_and_amount():
    beneficiary_document = "11.111.111/0001-11"

    accounts = {
        "itens": [
            {
                "id": 100001,
                "cliente": {
                    "nome": "Nebula Parts Ltda",
                    "cpfCnpj": beneficiary_document,
                },
                "saldo": 664.28,
            },
            {
                "id": 100002,
                "cliente": {
                    "nome": "Nebula Parts Ltda",
                    "cpfCnpj": beneficiary_document,
                },
                "saldo": 500.00,
            },
        ]
    }

    matching_accounts = find_matching_accounts(
        accounts_payable_data=accounts,
        beneficiary_document=beneficiary_document,
        payment_amount=Decimal("664.28"),
    )

    assert len(matching_accounts) == 1
    assert matching_accounts[0]["id"] == 100001


def test_multiple_accounts_with_same_document_and_amount():
    beneficiary_document = "22.222.222/0001-22"

    accounts = {
        "itens": [
            {
                "id": 200001,
                "cliente": {
                    "nome": "Cosmos Industrial Ltda",
                    "cpfCnpj": beneficiary_document,
                },
                "saldo": 1147.61,
            },
            {
                "id": 200002,
                "cliente": {
                    "nome": "Cosmos Industrial Ltda",
                    "cpfCnpj": beneficiary_document,
                },
                "saldo": 1147.61,
            },
        ]
    }

    matching_accounts = find_matching_accounts(
        accounts_payable_data=accounts,
        beneficiary_document=beneficiary_document,
        payment_amount=Decimal("1147.61"),
    )

    assert len(matching_accounts) == 2
    assert {account["id"] for account in matching_accounts} == {
        200001,
        200002,
    }


def test_different_supplier_names_do_not_prevent_document_match():
    beneficiary_document = "33.333.333/0001-33"

    accounts = {
        "itens": [
            {
                "id": 300001,
                "cliente": {
                    "nome": "Orion Auto Parts Ltda",
                    "cpfCnpj": beneficiary_document,
                },
                "saldo": 1050.00,
            },
        ]
    }

    matching_accounts = find_matching_accounts(
        accounts_payable_data=accounts,
        beneficiary_document=beneficiary_document,
        payment_amount=Decimal("1050.00"),
    )

    assert len(matching_accounts) == 1
    assert matching_accounts[0]["id"] == 300001


def test_find_matching_accounts_with_formatted_cnpj():
    accounts_payable_data = {
        "itens": [
            {
                "id": 123,
                "cliente": {"cpfCnpj": "21.035.489/0001-07"},
                "saldo": "625.95",
            }
        ]
    }

    result = find_matching_accounts(
        accounts_payable_data=accounts_payable_data,
        beneficiary_document="21035489000107",
        payment_amount=Decimal("625.95"),
    )

    assert len(result) == 1
    assert result[0]["id"] == 123


def test_default_due_date_window_is_ten_days():
    result = calculate_due_date_window(date(2026, 10, 16))

    assert result == ("2026-10-06", "2026-10-26")


def test_due_date_window_allows_explicit_override():
    result = calculate_due_date_window(
        date(2026, 10, 16),
        range_days=5,
    )

    assert result == ("2026-10-11", "2026-10-21")


def test_due_date_window_handles_month_boundaries():
    result = calculate_due_date_window(date(2026, 3, 3))

    assert result == ("2026-02-21", "2026-03-13")