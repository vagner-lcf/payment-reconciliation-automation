from unittest.mock import patch, call
from src.tiny_client import get_all_accounts_payable


def test_pagination_single_page():
    accounts = [{"id": i} for i in range(1, 36)]

    with patch(
        "src.tiny_client.get_accounts_payable",
        return_value={
            "itens": accounts,
            "paginacao": {"total": 35},
        },
    ) as mock_get_page:

        result = get_all_accounts_payable(
            access_token="fake_token",
            status="aberto",
            limit=100,
        )

    assert result == {"itens": accounts}
    assert mock_get_page.call_count == 1
    assert mock_get_page.call_args.kwargs["offset"] == 0

def test_pagination_multiple_pages():
    first_page = [{"id": i} for i in range(1, 101)]
    second_page = [{"id": i} for i in range(101, 136)]

    with patch(
        "src.tiny_client.get_accounts_payable",
        side_effect=[
            {
                "itens": first_page,
                "paginacao": {"total": 135},
            },
            {
                "itens": second_page,
                "paginacao": {"total": 135},
            },
        ],
    ) as mock_get_page:

        result = get_all_accounts_payable(
            access_token="fake_token",
            status="aberto",
            limit=100,
        )

    assert result is not None
    assert result["itens"] == first_page + second_page

    assert mock_get_page.call_args_list == [
        call(
            access_token="fake_token",
            status="aberto",
            initial_due_date=None,
            final_due_date=None,
            limit=100,
            offset=0,
        ),
        call(
            access_token="fake_token",
            status="aberto",
            initial_due_date=None,
            final_due_date=None,
            limit=100,
            offset=100,
        ),
    ]

def test_pagination_failure_on_second_page():
    first_page = [{"id": i} for i in range(1, 101)]

    with patch(
        "src.tiny_client.get_accounts_payable",
        side_effect=[
            {
                "itens": first_page,
                "paginacao": {"total": 135},
            },
            None,
        ],
    ) as mock_get_page:

        result = get_all_accounts_payable(
            access_token="fake_token",
            limit=100,
        )

    assert result is None
    assert mock_get_page.call_count == 2
