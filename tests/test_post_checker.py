from decimal import Decimal
from datetime import date
from unittest.mock import patch
import requests

from src.tiny_client import settle_account_payable


def test_settle_account_payable_success():
    with patch("src.tiny_client.requests.post") as mock_post:
        result = settle_account_payable(
            access_token="fake_token",
            id_account=1234,
            payment_date=date(2026, 9, 20),
            amount=Decimal("1.00"),
        )

        assert result is True

        mock_post.assert_called_once_with(
            "https://api.tiny.com.br/public-api/v3/contas-pagar/1234/baixar",
            headers={"Authorization": "Bearer fake_token"},
            json={
                "data": "20/09/2026",
                "valorPago": 1.0,
            },
            timeout=10,
        )


def test_settle_account_payable_request_error():
    with patch("src.tiny_client.requests.post") as mock_post:
        mock_post.side_effect = requests.RequestException("Test error")

        result = settle_account_payable(
            access_token="fake_token",
            id_account=1234,
            payment_date=date(2026, 9, 20),
            amount=Decimal("1.00"),
        )

        assert result is False

        mock_post.assert_called_once_with(
            "https://api.tiny.com.br/public-api/v3/contas-pagar/1234/baixar",
            headers={"Authorization": "Bearer fake_token"},
            json={
                "data": "20/09/2026",
                "valorPago": 1.0,
            },
            timeout=10,
        )