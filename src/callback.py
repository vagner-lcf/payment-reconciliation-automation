from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse


class CallbackHandler(BaseHTTPRequestHandler):
    """Handle the local HTTP callback used during Tiny authorization."""

    def do_GET(self) -> None:
        """Capture an authorization code from a valid callback request.

        Accept requests to /callback containing a code query parameter.
        Return an HTML response indicating success or failure.
        """

        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        code = query_params.get("code")

        if parsed_url.path == "/callback" and code:
            self.server.authorization_code = code[0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            message = "Autorização bem-sucedida! Você pode fechar esta janela."
            self.wfile.write(message.encode("utf-8"))
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            message = "Erro: Código de autorização não encontrado."
            self.wfile.write(message.encode("utf-8"))


def wait_for_authorization_code() -> str | None:
    """Wait for one Tiny OAuth callback on localhost port 8000.

    Start a temporary HTTP server, handle a single request, and close
    the server afterward. The configured request timeout is 120 seconds.

    Returns:
        The received authorization code, or None if no valid code
        is captured.
    """

    server = HTTPServer(("localhost", 8000), CallbackHandler)
    server.authorization_code = None
    server.timeout = 120

    try:
        print("Aguardando autorização do Tiny...")
        server.handle_request()
        return server.authorization_code
    finally:
        server.server_close()


if __name__ == "__main__":
    authorization_code = wait_for_authorization_code()
    print("Código capturado:", authorization_code is not None)
