
from unittest.mock import patch
from src.token_manager import get_valid_access_token


@patch("src.token_manager.time.time")
@patch("src.token_manager.load_tokens")
@patch("src.token_manager.refresh_access_token")
def test_reuses_valid_access_token(
    mock_refresh,
    mock_load,
    mock_time,
):
    mock_time.return_value = 1000

    mock_load.return_value = {
        "access_token": "existing_token",
        "refresh_token": "refresh_token",
        "expires_at": 5000,
    }

    result = get_valid_access_token()

    assert result == "existing_token"
    mock_refresh.assert_not_called()


@patch("src.token_manager.time.time")
@patch("src.token_manager.save_tokens")
@patch("src.token_manager.refresh_access_token")
@patch("src.token_manager.load_tokens")
def test_refreshes_expired_access_token(
    mock_load,
    mock_refresh,
    mock_save,
    mock_time,
):
    mock_time.return_value = 1000

    mock_load.return_value = {
        "access_token": "expired_token",
        "refresh_token": "old_refresh_token",
        "expires_at": 900,
    }

    mock_refresh.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 14400,
    }

    result = get_valid_access_token()

    assert result == "new_access_token"

    mock_refresh.assert_called_once_with(
        "old_refresh_token"
    )

    saved_tokens = mock_save.call_args.args[0]

    assert saved_tokens["refresh_token"] == "new_refresh_token"
    assert saved_tokens["expires_at"] == 15400


@patch("src.token_manager.time.time")
@patch("src.token_manager.save_tokens")
@patch("src.token_manager.refresh_access_token")
@patch("src.token_manager.load_tokens")
def test_preserves_refresh_token_when_not_rotated(
    mock_load,
    mock_refresh,
    mock_save,
    mock_time,
):
    mock_time.return_value = 1000

    mock_load.return_value = {
        "access_token": "expired_token",
        "refresh_token": "old_refresh_token",
        "expires_at": 900,
    }

    mock_refresh.return_value = {
        "access_token": "new_access_token",
        "expires_in": 14400,
    }

    result = get_valid_access_token()

    assert result == "new_access_token"

    mock_refresh.assert_called_once_with(
        "old_refresh_token"
    )

    saved_tokens = mock_save.call_args.args[0]

    assert saved_tokens["access_token"] == "new_access_token"
    assert saved_tokens["refresh_token"] == "old_refresh_token"
    assert saved_tokens["expires_at"] == 15400
