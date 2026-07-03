from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


API_VERSION = "1.0"


@dataclass
class Observation:
    image_path: str | None = None
    image_bytes: bytes | None = None
    history_image_bytes: list[bytes] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceRequest:
    session_id: str
    step_index: int
    observation: Observation
    instruction: str = ""
    api_version: str = API_VERSION


@dataclass
class ActionChunk:
    index: int
    action: str
    repeat: int = 1
    score: float | None = None


@dataclass
class LocalWaypoint:
    x: float
    y: float
    yaw: float


@dataclass
class InferenceResponse:
    session_id: str
    step_index: int
    chunks: list[ActionChunk] = field(default_factory=list)
    command_type: str = "action_chunks"
    waypoints: list[LocalWaypoint] = field(default_factory=list)
    stop: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    api_version: str = API_VERSION

    # Temporary source-level compatibility only.
    # This field is never emitted in the API v1 HTTP payload.
    final: bool | None = field(default=None, repr=False, compare=False)
