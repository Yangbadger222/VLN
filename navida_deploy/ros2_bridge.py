from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Any

from .client import build_request
from .http_client import post_inference
from .messages import Observation, InferenceResponse


def ros_image_to_observation(image_msg: Any) -> Observation:
    metadata = {
        "height": getattr(image_msg, "height", None),
        "width": getattr(image_msg, "width", None),
        "encoding": getattr(image_msg, "encoding", None),
        "step": getattr(image_msg, "step", None),
    }
    data = getattr(image_msg, "data", None)
    return Observation(image_bytes=_coerce_image_bytes(data), metadata=metadata)


def _coerce_image_bytes(data: Any) -> bytes | None:
    if data is None:
        return None
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    try:
        return bytes(data)
    except TypeError:
        return None


@dataclass
class NavidaRos2Gateway:
    infer_url: str
    post: Callable[..., InferenceResponse] = post_inference

    def infer(
        self,
        session_id: str,
        step_index: int,
        instruction: str,
        image_msg: Any,
    ) -> InferenceResponse:
        observation = ros_image_to_observation(image_msg)
        request = build_request(
            session_id=session_id,
            step_index=step_index,
            instruction=instruction,
            observation=observation,
        )
        return self.post(self.infer_url, request)


class Ros2NodeProtocol(Protocol):
    def publish_response(self, response: InferenceResponse) -> None:
        raise NotImplementedError
