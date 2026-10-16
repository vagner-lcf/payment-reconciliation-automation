import pytest
from unittest.mock import Mock, patch

from requests.exceptions import JSONDecodeError

from src.tiny_client import (
    get_accounts_payable,
    get_account_payable_by_id,
    get_account_payable_payments,
    get_all_accounts_payable,
)


def test_get_accounts_payable_returns_none_on_invalid_json():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = JSONDecodeError(
        "Expecting value",
        "invalid",
        0,
    )

    with patch(
        "src.tiny_client.requests.get",
        return_value=response,
    ) as mock_get:
        result = get_accounts_payable(
            access_token="fake_token",
        )

    assert result is None
    mock_get.assert_called_once()


@pytest.mark.parametrize(
    "get_function",
    [
        get_account_payable_by_id,
        get_account_payable_payments,
    ],
)
def test_get_by_id_returns_none_on_invalid_json(get_function):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = JSONDecodeError(
        "Expecting value",
        "invalid",
        0,
    )

    with patch(
        "src.tiny_client.requests.get",
        return_value=response,
    ) as mock_get:
        result = get_function(
            access_token="fake_token",
            id_account=123,
        )

    assert result is None
    mock_get.assert_called_once()


def test_get_all_accounts_payable_rejects_invalid_items():
    invalid_response = {
        "itens": [None],
        "paginacao": {"total": 1},
    }

    with patch(
        "src.tiny_client.get_accounts_payable",
        return_value=invalid_response,
    ):
        result = get_all_accounts_payable(
            access_token="fake_token",
        )

    assert result is None
