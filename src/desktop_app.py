from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer

import webview

from ui_server import Handler


HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"


def _serve(server: ThreadingHTTPServer) -> None:
    server.serve_forever(poll_interval=0.2)


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    thread = threading.Thread(target=_serve, args=(server,), daemon=True)
    thread.start()

    try:
        webview.create_window(
            "local-RAG",
            URL,
            width=1280,
            height=900,
            min_size=(960, 700),
        )
        webview.start()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
