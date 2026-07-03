from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .codec import request_to_dict, response_from_dict
from .messages import InferenceRequest, InferenceResponse


class InferenceHTTPError(RuntimeError):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(f"HTTP {status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.details = dict(details or {})


def _decode_json_body(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("inference endpoint returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("inference endpoint returned a non-object JSON body")

    return payload


def post_inference(
    url: str,
    request: InferenceRequest,
    timeout_s: float = 20.0,
) -> InferenceResponse:
    payload = json.dumps(
        request_to_dict(request),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    http_request = Request(url, data=payload, method="POST")
    http_request.add_header("Content-Type", "application/json")
    http_request.add_header("Accept", "application/json")

    try:
        with urlopen(http_request, timeout=timeout_s) as response:
            body = response.read()
    except HTTPError as exc:
        body = exc.read()

        try:
            error_payload = _decode_json_body(body)
            error = error_payload.get("error") or {}
            code = str(error.get("code") or "HTTP_ERROR")
            message = str(error.get("message") or exc.reason)
            details = error.get("details")
            if not isinstance(details, dict):
                details = {}
        except RuntimeError:
            code = "HTTP_ERROR"
            message = str(exc.reason)
            details = {}

        raise InferenceHTTPError(
            status=exc.code,
            code=code,
            message=message,
            details=details,
        ) from exc

    response = response_from_dict(_decode_json_body(body))

    if response.session_id != request.session_id:
        raise RuntimeError(
            "inference response session_id does not match the request"
        )

    if response.step_index != request.step_index:
        raise RuntimeError(
            "inference response step_index does not match the request"
        )

    return response
