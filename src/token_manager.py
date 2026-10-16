
import time
from src.auth import refresh_access_token
from src.token_store import load_tokens, save_tokens


EXPIRATION_MARGIN_SECONDS = 60


def store_token_response(token_data: dict) -> None:
    """Store OAuth tokens with their expiration timestamp."""

    stored_tokens = {
        **token_data,
        "expires_at": time.time() + int(token_data["expires_in"]),
    }

    save_tokens(stored_tokens)


def get_valid_access_token() -> str | None:
    """Return a valid access token or attempt automatic renewal."""

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
