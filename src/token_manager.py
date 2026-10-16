
import time
from src.auth import refresh_access_token
from src.token_store import load_tokens, save_tokens


EXPIRATION_MARGIN_SECONDS = 60


def store_token_response(token_data: dict) -> None:
    """Persist an OAuth token response with its expiration timestamp.

    Calculate expires_at using the current Unix timestamp and the
    expires_in duration returned by Tiny.

    Args:
        token_data: OAuth response containing expires_in and token data.
    """

    stored_tokens = {
        **token_data,
        "expires_at": time.time() + int(token_data["expires_in"]),
    }

    save_tokens(stored_tokens)


def get_valid_access_token() -> str | None:
    """Retrieve a usable access token, refreshing it when necessary.

    Reuse the stored access token while it remains valid, allowing a
    60-second safety margin before expiration.

    If renewal is required, request new tokens and persist them.
    Preserve the previous refresh token when the response does not
    include a replacement.

    Returns:
        A usable access token, or None if authentication is unavailable.
    """

    token_data = load_tokens()

    if not token_data:
        return None

    access_token = token_data.get("access_token")
    expires_at = token_data.get("expires_at", 0)

    if (
        access_token
        and time.time() < expires_at - EXPIRATION_MARGIN_SECONDS
    ):
        return access_token

    refresh_token = token_data.get("refresh_token")

    if not refresh_token:
        return None

    refreshed_tokens = refresh_access_token(refresh_token)

    if not refreshed_tokens:
        return None

    # Preserve the previous refresh token if no replacement is returned.
    if not refreshed_tokens.get("refresh_token"):
        refreshed_tokens["refresh_token"] = refresh_token

    store_token_response(refreshed_tokens)

    return refreshed_tokens["access_token"]
