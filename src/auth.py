import os
import urllib.parse

import requests
from dotenv import load_dotenv


load_dotenv()

BASE_URL = "https://accounts.tiny.com.br/realms/tiny/protocol/openid-connect/auth"
TOKEN_URL = "https://accounts.tiny.com.br/realms/tiny/protocol/openid-connect/token"

OLIST_CLIENT_ID = os.getenv("OLIST_CLIENT_ID")
OLIST_CLIENT_SECRET = os.getenv("OLIST_CLIENT_SECRET")
OLIST_REDIRECT_URI = os.getenv("OLIST_REDIRECT_URI")


def build_authorization_url() -> str:
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

    except (requests.RequestException, ValueError):
        return None

    if not isinstance(token_data, dict):
        return None

    if not token_data.get("access_token"):
        return None

    return token_data
