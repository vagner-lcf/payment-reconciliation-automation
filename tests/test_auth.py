from unittest.mock import Mock, patch

import requests

from src.auth import refresh_access_token


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
