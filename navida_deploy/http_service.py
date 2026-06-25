from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .backend import InferenceBackend, MockNaVIDABackend
from .codec import request_from_dict, response_to_dict


class InferenceHandler(BaseHTTPRequestHandler):
    backend: InferenceBackend = MockNaVIDABackend()

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_error(404, "not found")
            return
        body = json.dumps({"status": "ok"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/infer":
            self.send_error(404, "not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        request = request_from_dict(payload)
        response = self.backend.infer(request)
        body = json.dumps(response_to_dict(response)).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class InferenceHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], backend: InferenceBackend | None = None):
        self.backend = backend or MockNaVIDABackend()
        super().__init__(server_address, InferenceHandler)


def create_server(
    address: tuple[str, int],
    backend: InferenceBackend | None = None,
) -> ThreadingHTTPServer:
    server = InferenceHTTPServer(address, backend=backend)
    InferenceHandler.backend = server.backend
    return server
