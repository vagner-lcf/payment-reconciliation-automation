
import webbrowser

from src.auth import (
    build_authorization_url,
    exchange_code_for_token,
)
from src.callback import wait_for_authorization_code
from src.token_manager import store_token_response


def main() -> None:
    """Run the interactive Tiny OAuth authorization flow."""

    authorization_url = build_authorization_url()

    print("Abrindo a autorização do Tiny no navegador...")

    # Open the browser before waiting for the callback.
    webbrowser.open(authorization_url)

    authorization_code = wait_for_authorization_code()

    if not authorization_code:
        print("Não foi possível concluir a autorização.")
        return

    token_data = exchange_code_for_token(authorization_code)

    if not token_data or not token_data.get("access_token"):
        print("Não foi possível obter os tokens do Tiny.")
        return

    if not token_data.get("refresh_token"):
        print("O Tiny não retornou um token de renovação.")
        return

    store_token_response(token_data)

    print("Autorização do Tiny concluída com sucesso.")


if __name__ == "__main__":
    main()
