from __future__ import annotations

from typing import Iterable

from .messages import ActionChunk, InferenceRequest, InferenceResponse
from .codec import response_to_dict


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
def stream_mock_chunks(response: InferenceResponse) -> Iterable[ActionChunk]:
    yield from response.chunks
