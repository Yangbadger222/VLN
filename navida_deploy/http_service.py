from __future__ import annotations

import json
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .backend import InferenceBackend, MockNaVIDABackend
from .codec import request_from_dict, response_to_dict
from .validation import (
    ProtocolError,
    error_payload,
    normalize_response,
)


MAX_REQUEST_BODY_BYTES = 32 * 1024 * 1024


def _backend_identifier(backend: InferenceBackend) -> str:
    model_id = getattr(backend, "model_id", None)
    if isinstance(model_id, str) and model_id.strip():
        return model_id

    if isinstance(backend, MockNaVIDABackend):
        return "mock"

    return backend.__class__.__name__


def _correlation(payload: Any) -> tuple[str | None, int | None]:
    if not isinstance(payload, dict):
        return None, None

    session_id = payload.get("session_id")
    if not isinstance(session_id, str):
        session_id = None

    step_index = payload.get("step_index")
    if not isinstance(step_index, int) or isinstance(step_index, bool):
        step_index = None

    return session_id, step_index


class InferenceHandler(BaseHTTPRequestHandler):
    backend: InferenceBackend = MockNaVIDABackend()

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_protocol_error(
        self,
        error: ProtocolError,
        session_id: str | None = None,
        step_index: int | None = None,
    ) -> None:
        self.log_error(
            "%s: %s details=%s",
            error.code,
            error.message,
            error.details,
        )
        self._send_json(
            error.status,
            error_payload(
                error,
                session_id=session_id,
                step_index=step_index,
            ),
        )

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self._send_protocol_error(
                ProtocolError(
                    "INVALID_REQUEST",
                    "endpoint not found",
                    404,
                    {"path": self.path},
                )
            )
            return

        self._send_json(200, {"status": "ok"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/infer":
            self._send_protocol_error(
                ProtocolError(
                    "INVALID_REQUEST",
                    "endpoint not found",
                    404,
                    {"path": self.path},
                )
            )
            return

        payload: Any = None
        session_id: str | None = None
        step_index: int | None = None

        try:
            content_type = self.headers.get("Content-Type", "")
            media_type = content_type.split(";", 1)[0].strip().lower()
            if media_type != "application/json":
                raise ProtocolError(
                    "INVALID_REQUEST",
                    "Content-Type must be application/json",
                    400,
                    {"header": "Content-Type", "value": content_type},
                )

            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ProtocolError(
                    "INVALID_REQUEST",
                    "Content-Length header is required",
                    400,
                    {"header": "Content-Length"},
                )

            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ProtocolError(
                    "INVALID_REQUEST",
                    "Content-Length must be an integer",
                    400,
                    {"header": "Content-Length", "value": raw_length},
                ) from exc

            if length < 0:
                raise ProtocolError(
                    "INVALID_REQUEST",
                    "Content-Length must be non-negative",
                    400,
                    {"header": "Content-Length", "value": length},
                )

            if length > MAX_REQUEST_BODY_BYTES:
                raise ProtocolError(
                    "IMAGE_TOO_LARGE",
                    "request body exceeds the configured size limit",
                    413,
                    {
                        "size_bytes": length,
                        "limit_bytes": MAX_REQUEST_BODY_BYTES,
                    },
                )

            raw_body = self.rfile.read(length)

            try:
                payload = json.loads(raw_body)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProtocolError(
                    "INVALID_JSON",
                    "request body is not valid JSON",
                    400,
                    {
                        "line": getattr(exc, "lineno", None),
                        "column": getattr(exc, "colno", None),
                    },
                ) from exc

            session_id, step_index = _correlation(payload)
            request = request_from_dict(payload)

            started = time.perf_counter()
            response = self.backend.infer(request)
            elapsed_ms = (time.perf_counter() - started) * 1000.0

            response = normalize_response(
                response,
                backend_name=_backend_identifier(self.backend),
                inference_ms=elapsed_ms,
            )

            if response.session_id != request.session_id:
                raise ProtocolError(
                    "BACKEND_ERROR",
                    "backend response session_id does not match the request",
                    500,
                    {
                        "request_session_id": request.session_id,
                        "response_session_id": response.session_id,
                    },
                )

            if response.step_index != request.step_index:
                raise ProtocolError(
                    "BACKEND_ERROR",
                    "backend response step_index does not match the request",
                    500,
                    {
                        "request_step_index": request.step_index,
                        "response_step_index": response.step_index,
                    },
                )

            self._send_json(200, response_to_dict(response))

        except ProtocolError as exc:
            self._send_protocol_error(
                exc,
                session_id=session_id,
                step_index=step_index,
            )

        except Exception as exc:  # pragma: no cover - defensive boundary
            traceback.print_exc()
            self._send_protocol_error(
                ProtocolError(
                    "INTERNAL_ERROR",
                    "unexpected internal server error",
                    500,
                    {"exception_type": type(exc).__name__},
                ),
                session_id=session_id,
                step_index=step_index,
            )

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        message = format % args
        sys.stderr.write(
            f"[http] {self.client_address[0]} "
            f"[{self.log_date_time_string()}] {message}\n"
        )
        sys.stderr.flush()


class InferenceHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        backend: InferenceBackend | None = None,
    ):
        self.backend = backend or MockNaVIDABackend()
        super().__init__(server_address, InferenceHandler)


def create_server(
    address: tuple[str, int],
    backend: InferenceBackend | None = None,
) -> ThreadingHTTPServer:
    server = InferenceHTTPServer(address, backend=backend)
    InferenceHandler.backend = server.backend
    return server
