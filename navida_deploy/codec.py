from __future__ import annotations

import base64

from .messages import ActionChunk, InferenceRequest, InferenceResponse, Observation


def _encode_bytes(data: bytes | None) -> str | None:
    if data is None:
        return None
    return base64.b64encode(data).decode("ascii")


def _decode_bytes(data: str | None) -> bytes | None:
    if data is None:
        return None
    return base64.b64decode(data.encode("ascii"))


def request_to_dict(request: InferenceRequest) -> dict:
    return {
        "session_id": request.session_id,
        "step_index": request.step_index,
        "instruction": request.instruction,
        "observation": {
            "image_path": request.observation.image_path,
            "image_bytes": _encode_bytes(request.observation.image_bytes),
            "metadata": request.observation.metadata,
        },
    }


def request_from_dict(payload: dict) -> InferenceRequest:
    observation = payload["observation"]
    return InferenceRequest(
        session_id=payload["session_id"],
        step_index=payload["step_index"],
        instruction=payload.get("instruction", ""),
        observation=Observation(
            image_path=observation.get("image_path"),
            image_bytes=_decode_bytes(observation.get("image_bytes")),
            metadata=dict(observation.get("metadata") or {}),
        ),
    )


def response_to_dict(response: InferenceResponse) -> dict:
    return {
        "session_id": response.session_id,
        "step_index": response.step_index,
        "chunks": [
            {
                "index": chunk.index,
                "action": chunk.action,
                "repeat": chunk.repeat,
                "score": chunk.score,
            }
            for chunk in response.chunks
        ],
        "final": response.final,
        "metadata": response.metadata,
    }


def response_from_dict(payload: dict) -> InferenceResponse:
    return InferenceResponse(
        session_id=payload["session_id"],
        step_index=payload["step_index"],
        chunks=[
            ActionChunk(
                index=chunk["index"],
                action=chunk["action"],
                repeat=chunk.get("repeat", 1),
                score=chunk.get("score"),
            )
            for chunk in payload.get("chunks", [])
        ],
        final=payload.get("final", True),
        metadata=dict(payload.get("metadata") or {}),
    )
