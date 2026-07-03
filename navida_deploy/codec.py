from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Any

from .messages import (
    API_VERSION,
    ActionChunk,
    InferenceRequest,
    InferenceResponse,
    LocalWaypoint,
    Observation,
)
from .validation import (
    MAX_HISTORY_IMAGES,
    ProtocolError,
    validate_jpeg,
    validate_request,
    validate_response,
)


def _encode_bytes(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _decode_jpeg(data: Any, field: str) -> bytes:
    if not isinstance(data, str) or not data:
        raise ProtocolError(
            "INVALID_REQUEST",
            f"{field} must be a non-empty Base64 string",
            400,
            {"field": field},
        )

    try:
        decoded = base64.b64decode(data.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise ProtocolError(
            "INVALID_BASE64",
            f"{field} is not valid Base64",
            400,
            {"field": field},
        ) from exc

    validate_jpeg(decoded, field)
    return decoded


def _current_image_bytes(request: InferenceRequest) -> bytes | None:
    image_bytes = request.observation.image_bytes
    if image_bytes is not None:
        return bytes(image_bytes)

    image_path = request.observation.image_path
    if not image_path:
        return None

    try:
        return Path(image_path).read_bytes()
    except OSError as exc:
        raise ProtocolError(
            "INVALID_IMAGE",
            "unable to read observation image_path",
            422,
            {"field": "observation.image_path", "value": image_path},
        ) from exc


def request_to_dict(request: InferenceRequest) -> dict[str, Any]:
    image_bytes = _current_image_bytes(request)

    wire_request = InferenceRequest(
        session_id=request.session_id,
        step_index=request.step_index,
        instruction=request.instruction,
        observation=Observation(
            image_bytes=image_bytes,
            history_image_bytes=[
                bytes(item) for item in request.observation.history_image_bytes
            ],
            metadata=dict(request.observation.metadata),
        ),
        api_version=request.api_version,
    )
    validate_request(wire_request)

    return {
        "api_version": wire_request.api_version,
        "session_id": wire_request.session_id,
        "step_index": wire_request.step_index,
        "instruction": wire_request.instruction,
        "observation": {
            "image_bytes": _encode_bytes(wire_request.observation.image_bytes or b""),
            "history_image_bytes": [
                _encode_bytes(item)
                for item in wire_request.observation.history_image_bytes
            ],
            "metadata": wire_request.observation.metadata,
        },
    }


def request_from_dict(payload: dict[str, Any]) -> InferenceRequest:
    if not isinstance(payload, dict):
        raise ProtocolError(
            "INVALID_REQUEST",
            "request body must be a JSON object",
            400,
        )

    api_version = payload.get("api_version")
    if api_version != API_VERSION:
        raise ProtocolError(
            "UNSUPPORTED_API_VERSION",
            f"api_version must be exactly {API_VERSION!r}",
            400,
            {"field": "api_version", "value": api_version},
        )

    session_id = payload.get("session_id")
    step_index = payload.get("step_index")
    instruction = payload.get("instruction")
    observation_payload = payload.get("observation")

    if not isinstance(observation_payload, dict):
        raise ProtocolError(
            "INVALID_REQUEST",
            "observation must be an object",
            400,
            {"field": "observation"},
        )

    if "image_bytes" not in observation_payload:
        raise ProtocolError(
            "INVALID_REQUEST",
            "observation.image_bytes is required",
            400,
            {"field": "observation.image_bytes"},
        )

    if "history_image_bytes" not in observation_payload:
        raise ProtocolError(
            "INVALID_REQUEST",
            "observation.history_image_bytes is required",
            400,
            {"field": "observation.history_image_bytes"},
        )

    if "metadata" not in observation_payload:
        raise ProtocolError(
            "INVALID_REQUEST",
            "observation.metadata is required",
            400,
            {"field": "observation.metadata"},
        )

    history_payload = observation_payload["history_image_bytes"]
    if not isinstance(history_payload, list):
        raise ProtocolError(
            "INVALID_REQUEST",
            "observation.history_image_bytes must be an array",
            400,
            {"field": "observation.history_image_bytes"},
        )

    if len(history_payload) > MAX_HISTORY_IMAGES:
        raise ProtocolError(
            "TOO_MANY_HISTORY_IMAGES",
            "observation.history_image_bytes exceeds the configured count limit",
            413,
            {
                "field": "observation.history_image_bytes",
                "count": len(history_payload),
                "limit": MAX_HISTORY_IMAGES,
            },
        )

    metadata = observation_payload["metadata"]
    if not isinstance(metadata, dict):
        raise ProtocolError(
            "INVALID_REQUEST",
            "observation.metadata must be an object",
            400,
            {"field": "observation.metadata"},
        )

    request = InferenceRequest(
        api_version=api_version,
        session_id=session_id,
        step_index=step_index,
        instruction=instruction,
        observation=Observation(
            image_bytes=_decode_jpeg(
                observation_payload["image_bytes"],
                "observation.image_bytes",
            ),
            history_image_bytes=[
                _decode_jpeg(
                    item,
                    f"observation.history_image_bytes[{index}]",
                )
                for index, item in enumerate(history_payload)
            ],
            metadata=dict(metadata),
        ),
    )

    validate_request(request)
    return request


def response_to_dict(response: InferenceResponse) -> dict[str, Any]:
    validate_response(response)

    return {
        "api_version": response.api_version,
        "session_id": response.session_id,
        "step_index": response.step_index,
        "command_type": response.command_type,
        "chunks": [
            {
                "index": chunk.index,
                "action": chunk.action,
                "repeat": chunk.repeat,
                "score": chunk.score,
            }
            for chunk in response.chunks
        ],
        "waypoints": [
            {
                "x": waypoint.x,
                "y": waypoint.y,
                "yaw": waypoint.yaw,
            }
            for waypoint in response.waypoints
        ],
        "stop": response.stop,
        "metadata": response.metadata,
    }


def response_from_dict(payload: dict[str, Any]) -> InferenceResponse:
    if not isinstance(payload, dict):
        raise ProtocolError(
            "INVALID_REQUEST",
            "response body must be a JSON object",
            422,
        )

    legacy = "api_version" not in payload

    api_version = payload.get("api_version", API_VERSION)
    command_type = payload.get("command_type", "action_chunks")
    chunks_payload = payload.get("chunks", [])
    waypoints_payload = payload.get("waypoints", [])
    stop = payload.get("stop", False)

    if not isinstance(chunks_payload, list):
        raise ProtocolError(
            "INVALID_ACTION",
            "chunks must be an array",
            422,
            {"field": "chunks"},
        )

    if not isinstance(waypoints_payload, list):
        raise ProtocolError(
            "INVALID_WAYPOINT",
            "waypoints must be an array",
            422,
            {"field": "waypoints"},
        )

    chunks: list[ActionChunk] = []
    for index, raw_chunk in enumerate(chunks_payload):
        if not isinstance(raw_chunk, dict):
            raise ProtocolError(
                "INVALID_ACTION",
                "chunks must contain objects",
                422,
                {"field": f"chunks[{index}]"},
            )

        try:
            chunk = ActionChunk(
                index=raw_chunk["index"],
                action=raw_chunk["action"],
                repeat=raw_chunk.get("repeat", 1),
                score=raw_chunk.get("score"),
            )
        except KeyError as exc:
            raise ProtocolError(
                "INVALID_ACTION",
                "action chunk is missing a required field",
                422,
                {"field": f"chunks[{index}].{exc.args[0]}"},
            ) from exc

        chunks.append(chunk)

    waypoints: list[LocalWaypoint] = []
    for index, raw_waypoint in enumerate(waypoints_payload):
        if not isinstance(raw_waypoint, dict):
            raise ProtocolError(
                "INVALID_WAYPOINT",
                "waypoints must contain objects",
                422,
                {"field": f"waypoints[{index}]"},
            )

        try:
            waypoint = LocalWaypoint(
                x=raw_waypoint["x"],
                y=raw_waypoint["y"],
                yaw=raw_waypoint["yaw"],
            )
        except KeyError as exc:
            raise ProtocolError(
                "INVALID_WAYPOINT",
                "waypoint is missing a required field",
                422,
                {"field": f"waypoints[{index}].{exc.args[0]}"},
            ) from exc

        waypoints.append(waypoint)

    metadata_payload = payload.get("metadata", {})
    if not isinstance(metadata_payload, dict):
        raise ProtocolError(
            "INVALID_REQUEST",
            "metadata must be an object",
            422,
            {"field": "metadata"},
        )

    metadata = dict(metadata_payload)
    if legacy:
        metadata.setdefault("backend", "legacy")
        metadata.setdefault("inference_ms", 0.0)

    response = InferenceResponse(
        api_version=api_version,
        session_id=payload.get("session_id"),
        step_index=payload.get("step_index"),
        command_type=command_type,
        chunks=chunks,
        waypoints=waypoints,
        stop=stop,
        metadata=metadata,
        final=payload.get("final"),
    )

    validate_response(response)
    return response
