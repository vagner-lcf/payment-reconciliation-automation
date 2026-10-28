from unittest.mock import Mock, patch
import pytest

import requests

from src.auth import refresh_access_token
from src import auth


@patch("src.auth.requests.post")
def test_refresh_access_token_success(mock_post):
    token_data = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 14400,
    }

    response = Mock()
    response.json.return_value = token_data
    mock_post.return_value = response

    result = refresh_access_token("old_refresh_token")

    assert result == token_data

    assert mock_post.call_args.kwargs["data"]["grant_type"] == "refresh_token"
    assert (
        mock_post.call_args.kwargs["data"]["refresh_token"]
        == "old_refresh_token"
    )


@patch("src.auth.requests.post")
def test_refresh_access_token_http_error(mock_post):
    mock_post.side_effect = requests.HTTPError("401 Unauthorized")

    result = refresh_access_token("invalid_refresh_token")

    assert result is None


@pytest.mark.parametrize(
    "network_error",
    [
        requests.ConnectionError("DNS indisponível"),
        requests.Timeout("Tempo de conexão excedido"),
    ],
)
@patch("src.auth.requests.post")
def test_refresh_classifies_network_failure_as_temporary(
    mock_post,
    network_error,
):
    mock_post.side_effect = network_error

    with pytest.raises(auth.TinyAuthTemporaryError):
        auth.refresh_access_token("fake_refresh_token")


@patch("src.auth.requests.post")
def test_refresh_classifies_http_503_as_temporary(mock_post):
    response = Mock()
    response.status_code = 503
    response.raise_for_status.side_effect = requests.HTTPError(
        response=response
    )
    mock_post.return_value = response

    with pytest.raises(auth.TinyAuthTemporaryError):
        auth.refresh_access_token("fake_refresh_token")


@patch("src.auth.requests.post")
def test_refresh_invalid_grant_still_requires_authorization(mock_post):
    response = Mock()
    response.status_code = 400
    response.raise_for_status.side_effect = requests.HTTPError(
        response=response
    )
    mock_post.return_value = response

    result = auth.refresh_access_token("fake_refresh_token")

    assert result is None
