from src.matching import summarize_accounts


def test_summarize_one_account():
    matching_accounts = [
        {
            "id": 123456789,
            "dataVencimento": "2026-09-08",
            "saldo": 150.75,
            "cliente": {
                "nome": "FORNECEDOR TESTE LTDA",
                "cpfCnpj": "12.345.678/0001-90"
            }
        }
    ]

    account_data = summarize_accounts(matching_accounts=matching_accounts)

    assert account_data == [{
        "ID": 123456789,
        "Fornecedor": "FORNECEDOR TESTE LTDA",
        "CPF/CNPJ": "12.345.678/0001-90",
        "Saldo": 150.75,
        "Data Vencimento": "2026-09-08"
    }]

def test_summarize_multiple_accounts():
    matching_accounts = [
        {
            "id": 123456789,
            "dataVencimento": "2026-09-08",
            "saldo": 150.75,
            "cliente": {
                "nome": "FORNECEDOR TESTE LTDA",
                "cpfCnpj": "12.345.678/0001-90"
            }
        },
        {
            "id": 987654321,
            "dataVencimento": "2026-09-15",
            "saldo": 150.75,
            "cliente": {
                "nome": "FORNECEDOR TESTE LTDA",
                "cpfCnpj": "12.345.678/0001-90"
            }
        }        
    ]

    accounts_data = summarize_accounts(matching_accounts=matching_accounts)

    assert accounts_data == [
        {
        "ID": 123456789,
        "Fornecedor": "FORNECEDOR TESTE LTDA",
        "CPF/CNPJ": "12.345.678/0001-90",
        "Saldo": 150.75,
        "Data Vencimento": "2026-09-08"
        },
        {
        "ID": 987654321,
        "Fornecedor": "FORNECEDOR TESTE LTDA",
        "CPF/CNPJ": "12.345.678/0001-90",
        "Saldo": 150.75,
        "Data Vencimento": "2026-09-15"
        }
    ]

