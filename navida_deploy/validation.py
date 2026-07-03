from __future__ import annotations

import math
from numbers import Real
from typing import Any

from .messages import (
    API_VERSION,
    ActionChunk,
    InferenceRequest,
    InferenceResponse,
    LocalWaypoint,
    Observation,
)


ALLOWED_ACTIONS = frozenset({"forward", "turn_left", "turn_right", "stop"})
ALLOWED_COMMAND_TYPES = frozenset({"action_chunks", "local_waypoints"})

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_HISTORY_IMAGES = 16
MAX_WAYPOINTS = 8


class ProtocolError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = dict(details or {})


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def validate_jpeg(data: bytes, field: str) -> None:
    if not isinstance(data, bytes):
        raise ProtocolError(
            "INVALID_IMAGE",
            f"{field} must decode to bytes",
            422,
            {"field": field},
        )

    if len(data) > MAX_IMAGE_BYTES:
        raise ProtocolError(
            "IMAGE_TOO_LARGE",
            f"{field} exceeds the configured image-size limit",
            413,
            {"field": field, "size_bytes": len(data), "limit_bytes": MAX_IMAGE_BYTES},
        )

    if len(data) < 4 or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        raise ProtocolError(
            "INVALID_IMAGE",
            f"{field} is not a supported JPEG byte sequence",
            422,
            {"field": field},
        )


def validate_request(request: InferenceRequest) -> None:
    if not isinstance(request, InferenceRequest):
        raise ProtocolError(
            "INVALID_REQUEST",
            "request must be an InferenceRequest",
            400,
        )

    if request.api_version != API_VERSION:
        raise ProtocolError(
            "UNSUPPORTED_API_VERSION",
            f"api_version must be exactly {API_VERSION!r}",
            400,
            {"field": "api_version", "value": request.api_version},
        )

    if not isinstance(request.session_id, str) or not request.session_id.strip():
        raise ProtocolError(
            "INVALID_REQUEST",
            "session_id must be a non-empty string",
            400,
            {"field": "session_id"},
        )

    if not _is_integer(request.step_index) or request.step_index < 0:
        raise ProtocolError(
            "INVALID_REQUEST",
            "step_index must be a non-negative integer",
            400,
            {"field": "step_index", "value": request.step_index},
        )

    if not isinstance(request.instruction, str) or not request.instruction.strip():
        raise ProtocolError(
            "INVALID_REQUEST",
            "instruction must be a non-empty string",
            400,
            {"field": "instruction"},
        )

    if not isinstance(request.observation, Observation):
        raise ProtocolError(
            "INVALID_REQUEST",
            "observation must be an object",
            400,
            {"field": "observation"},
        )

    if request.observation.image_bytes is None:
        raise ProtocolError(
            "INVALID_REQUEST",
            "observation.image_bytes is required",
            400,
            {"field": "observation.image_bytes"},
        )

    image_bytes = bytes(request.observation.image_bytes)
    validate_jpeg(image_bytes, "observation.image_bytes")

    history = request.observation.history_image_bytes
    if not isinstance(history, list):
        raise ProtocolError(
            "INVALID_REQUEST",
            "observation.history_image_bytes must be an array",
            400,
            {"field": "observation.history_image_bytes"},
        )

    if len(history) > MAX_HISTORY_IMAGES:
        raise ProtocolError(
            "TOO_MANY_HISTORY_IMAGES",
            "observation.history_image_bytes exceeds the configured count limit",
            413,
            {
                "field": "observation.history_image_bytes",
                "count": len(history),
                "limit": MAX_HISTORY_IMAGES,
            },
        )

    for index, item in enumerate(history):
        if not isinstance(item, (bytes, bytearray)):
            raise ProtocolError(
                "INVALID_IMAGE",
                "history image must decode to bytes",
                422,
                {"field": f"observation.history_image_bytes[{index}]"},
            )
        validate_jpeg(
            bytes(item),
            f"observation.history_image_bytes[{index}]",
        )

    if not isinstance(request.observation.metadata, dict):
        raise ProtocolError(
            "INVALID_REQUEST",
            "observation.metadata must be an object",
            400,
            {"field": "observation.metadata"},
        )


def _validate_action_chunk(chunk: ActionChunk, position: int) -> None:
    if not isinstance(chunk, ActionChunk):
        raise ProtocolError(
            "INVALID_ACTION",
            "chunks must contain action objects",
            422,
            {"field": f"chunks[{position}]"},
        )

    if not _is_integer(chunk.index) or chunk.index < 0:
        raise ProtocolError(
            "INVALID_ACTION",
            "action chunk index must be a non-negative integer",
            422,
            {"field": f"chunks[{position}].index", "value": chunk.index},
        )

    if chunk.action not in ALLOWED_ACTIONS:
        raise ProtocolError(
            "INVALID_ACTION",
            f"unsupported action: {chunk.action!r}",
            422,
            {"field": f"chunks[{position}].action", "value": chunk.action},
        )

    if not _is_integer(chunk.repeat) or chunk.repeat <= 0:
        raise ProtocolError(
            "INVALID_ACTION",
            "action repeat must be a positive integer",
            422,
            {"field": f"chunks[{position}].repeat", "value": chunk.repeat},
        )

    if chunk.score is not None:
        if not _is_number(chunk.score) or not math.isfinite(float(chunk.score)):
            raise ProtocolError(
                "INVALID_ACTION",
                "action score must be a finite number or null",
                422,
                {"field": f"chunks[{position}].score", "value": chunk.score},
            )


def _validate_waypoint(waypoint: LocalWaypoint, position: int) -> None:
    if not isinstance(waypoint, LocalWaypoint):
        raise ProtocolError(
            "INVALID_WAYPOINT",
            "waypoints must contain waypoint objects",
            422,
            {"field": f"waypoints[{position}]"},
        )

    for field in ("x", "y", "yaw"):
        value = getattr(waypoint, field)
        if not _is_number(value) or not math.isfinite(float(value)):
            raise ProtocolError(
                "INVALID_WAYPOINT",
                f"waypoint {field} must be a finite number",
                422,
                {"field": f"waypoints[{position}].{field}", "value": value},
            )


def validate_response(response: InferenceResponse) -> None:
    if not isinstance(response, InferenceResponse):
        raise ProtocolError(
            "BACKEND_ERROR",
            "backend did not return an InferenceResponse",
            500,
        )

    if response.api_version != API_VERSION:
        raise ProtocolError(
            "UNSUPPORTED_API_VERSION",
            f"response api_version must be exactly {API_VERSION!r}",
            422,
            {"field": "api_version", "value": response.api_version},
        )

    if not isinstance(response.session_id, str) or not response.session_id.strip():
        raise ProtocolError(
            "INVALID_REQUEST",
            "response session_id must be a non-empty string",
            422,
            {"field": "session_id"},
        )

    if not _is_integer(response.step_index) or response.step_index < 0:
        raise ProtocolError(
            "INVALID_REQUEST",
            "response step_index must be a non-negative integer",
            422,
            {"field": "step_index", "value": response.step_index},
        )

    if response.command_type not in ALLOWED_COMMAND_TYPES:
        raise ProtocolError(
            "INVALID_REQUEST",
            "command_type must be action_chunks or local_waypoints",
            422,
            {"field": "command_type", "value": response.command_type},
        )

    if not isinstance(response.chunks, list):
        raise ProtocolError(
            "INVALID_ACTION",
            "chunks must be an array",
            422,
            {"field": "chunks"},
        )

    if not isinstance(response.waypoints, list):
        raise ProtocolError(
            "INVALID_WAYPOINT",
            "waypoints must be an array",
            422,
            {"field": "waypoints"},
        )

    if response.command_type == "action_chunks" and response.waypoints:
        raise ProtocolError(
            "INVALID_WAYPOINT",
            "waypoints must be empty for action_chunks responses",
            422,
            {"field": "waypoints"},
        )

    if response.command_type == "local_waypoints" and response.chunks:
        raise ProtocolError(
            "INVALID_WAYPOINT",
            "chunks must be empty for local_waypoints responses",
            422,
            {"field": "chunks"},
        )

    if len(response.waypoints) > MAX_WAYPOINTS:
        raise ProtocolError(
            "INVALID_WAYPOINT",
            "a response may contain at most 8 local waypoints",
            422,
            {"field": "waypoints", "count": len(response.waypoints), "limit": MAX_WAYPOINTS},
        )

    for index, chunk in enumerate(response.chunks):
        _validate_action_chunk(chunk, index)

    for index, waypoint in enumerate(response.waypoints):
        _validate_waypoint(waypoint, index)

    if not isinstance(response.stop, bool):
        raise ProtocolError(
            "INVALID_REQUEST",
            "stop must be a boolean",
            422,
            {"field": "stop", "value": response.stop},
        )

    if not isinstance(response.metadata, dict):
        raise ProtocolError(
            "INVALID_REQUEST",
            "metadata must be an object",
            422,
            {"field": "metadata"},
        )

    backend = response.metadata.get("backend")
    if not isinstance(backend, str) or not backend.strip():
        raise ProtocolError(
            "INVALID_REQUEST",
            "metadata.backend must be a non-empty string",
            422,
            {"field": "metadata.backend"},
        )

    inference_ms = response.metadata.get("inference_ms")
    if (
        not _is_number(inference_ms)
        or not math.isfinite(float(inference_ms))
        or float(inference_ms) < 0
    ):
        raise ProtocolError(
            "INVALID_REQUEST",
            "metadata.inference_ms must be a non-negative finite number",
            422,
            {"field": "metadata.inference_ms", "value": inference_ms},
        )


def normalize_response(
    response: InferenceResponse,
    backend_name: str,
    inference_ms: float,
) -> InferenceResponse:
    if not isinstance(response, InferenceResponse):
        raise ProtocolError(
            "BACKEND_ERROR",
            "backend did not return an InferenceResponse",
            500,
        )

    response.api_version = API_VERSION

    metadata = dict(response.metadata or {})
    metadata["backend"] = str(metadata.get("backend") or backend_name)
    metadata["inference_ms"] = round(max(0.0, float(inference_ms)), 3)
    response.metadata = metadata

    validate_response(response)
    return response


def error_payload(
    error: ProtocolError,
    session_id: str | None = None,
    step_index: int | None = None,
) -> dict[str, Any]:
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "step_index": step_index,
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
        },
    }
