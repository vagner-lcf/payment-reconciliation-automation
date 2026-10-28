import os
import urllib.parse
import logging

import requests
from dotenv import load_dotenv


load_dotenv()

BASE_URL = "https://accounts.tiny.com.br/realms/tiny/protocol/openid-connect/auth"
TOKEN_URL = "https://accounts.tiny.com.br/realms/tiny/protocol/openid-connect/token"

OLIST_CLIENT_ID = os.getenv("OLIST_CLIENT_ID")
OLIST_CLIENT_SECRET = os.getenv("OLIST_CLIENT_SECRET")
OLIST_REDIRECT_URI = os.getenv("OLIST_REDIRECT_URI")


logger = logging.getLogger("payment_reconciliation")


class TinyAuthTemporaryError(Exception):
    """Transitionary error during OAuth renewal of Tiny."""


def build_authorization_url() -> str:
    """Build the Tiny OAuth authorization URL.

    Use the configured client ID and redirect URI to initiate the
    authorization code flow.

    Returns:
        The URL used to request interactive user authorization.
    """

    params = {
        "client_id": OLIST_CLIENT_ID,
        "redirect_uri": OLIST_REDIRECT_URI,
        "scope": "openid",
        "response_type": "code",
    }

    return BASE_URL + "?" + urllib.parse.urlencode(params)


def exchange_code_for_token(
    authorization_code: str,
) -> dict | None:
    """Exchange an OAuth authorization code for Tiny tokens.

    Args:
        authorization_code: Code received through the OAuth callback.

    Returns:
        The decoded token response, or None if the HTTP request fails.

    Note:
        The returned JSON is not currently validated by this function.
    """

    data = {
        "grant_type": "authorization_code",
        "client_id": OLIST_CLIENT_ID,
        "client_secret": OLIST_CLIENT_SECRET,
        "redirect_uri": OLIST_REDIRECT_URI,
        "code": authorization_code,
    }

    try:
        response = requests.post(TOKEN_URL, data=data, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print("Erro ao trocar o código por token:", e)
        return None

    return response.json()


def refresh_access_token(refresh_token: str) -> dict | None:
    """Renew tokens OAuth, distinguishing temporary failures.

    Returns None when authorization is rejected or response is invalid.
    Raises TinyAuthTemporaryError for temporary network failures or server unavailability.
    """

    data = {
        "grant_type": "refresh_token",
        "client_id": OLIST_CLIENT_ID,
        "client_secret": OLIST_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }

    try:
        response = requests.post(
            TOKEN_URL,
            data=data,
            timeout=10,
        )
        response.raise_for_status()
        token_data = response.json()

    except (requests.ConnectionError, requests.Timeout) as exc:
        logger.warning(
            "tiny_oauth_refresh_failed category=network"
        )
        raise TinyAuthTemporaryError(
            "Falha temporária de conexão com o Tiny."
        ) from exc

    except requests.HTTPError as exc:
        status_code = (
            exc.response.status_code
            if exc.response is not None
            else None
        )

        if (
            status_code in (408, 429)
            or (status_code is not None and status_code >= 500)
        ):
            logger.warning(
                "tiny_oauth_refresh_failed category=http_temporary "
                "http_status=%s",
                status_code,
            )
            raise TinyAuthTemporaryError(
                "Serviço de autenticação do Tiny indisponível."
            ) from exc

        logger.warning(
            "tiny_oauth_refresh_failed category=http_rejected "
            "http_status=%s",
            status_code,
        )
        return None

    except (requests.RequestException, ValueError):
        logger.warning(
            "tiny_oauth_refresh_failed category=invalid_response"
        )
        return None

    if not isinstance(token_data, dict):
        return None

    if not token_data.get("access_token"):
        return None

    return token_data
