from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .codec import request_from_dict, response_to_dict
from .server import run_mock_inference


class InferenceHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/infer":
            self.send_error(404, "not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        request = request_from_dict(payload)
        response = run_mock_inference(request)
        body = json.dumps(response_to_dict(response)).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def create_server(address: tuple[str, int]) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(address, InferenceHandler)

