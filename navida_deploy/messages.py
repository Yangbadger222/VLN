from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Observation:
    image_path: str | None = None
    image_bytes: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceRequest:
    session_id: str
    step_index: int
    observation: Observation


@dataclass
class ActionChunk:
    index: int
    action: str
    score: float | None = None


@dataclass
class InferenceResponse:
    session_id: str
    step_index: int
    chunks: list[ActionChunk]
    final: bool = True
