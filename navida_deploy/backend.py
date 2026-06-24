from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .chunking import chunk_atomic_actions
from .messages import ActionChunk, InferenceRequest, InferenceResponse


class InferenceBackend(Protocol):
    def infer(self, request: InferenceRequest) -> InferenceResponse:
        raise NotImplementedError


@dataclass
class MockNaVIDABackend:
    default_actions: tuple[str, ...] = ("forward", "turn_left")

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        chunks = chunk_atomic_actions(
            self.default_actions,
            merge_probability=1.0,
            rng=lambda: 0.0,
        )
        return InferenceResponse(
            session_id=request.session_id,
            step_index=request.step_index,
            chunks=chunks,
            final=True,
        )

