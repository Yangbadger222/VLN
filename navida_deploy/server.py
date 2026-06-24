from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from .messages import ActionChunk, InferenceRequest, InferenceResponse


def run_mock_inference(request: InferenceRequest) -> InferenceResponse:
    chunks = [
        ActionChunk(index=0, action="forward", score=0.92),
        ActionChunk(index=1, action="turn_left", score=0.81),
    ]
    return InferenceResponse(
        session_id=request.session_id,
        step_index=request.step_index,
        chunks=chunks,
        final=True,
    )


def response_to_dict(response: InferenceResponse) -> dict:
    return asdict(response)


def stream_mock_chunks(response: InferenceResponse) -> Iterable[ActionChunk]:
    yield from response.chunks

