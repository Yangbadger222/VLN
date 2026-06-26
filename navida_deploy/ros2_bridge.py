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
    compressed = _encode_compressed_image(image_msg)
    if compressed is not None:
        metadata["transport_encoding"] = "jpeg"
        return Observation(image_bytes=compressed, metadata=metadata)

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


def _encode_compressed_image(image_msg: Any) -> bytes | None:
    raw_bytes = _coerce_image_bytes(getattr(image_msg, "data", None))
    height = getattr(image_msg, "height", None)
    width = getattr(image_msg, "width", None)
    step = getattr(image_msg, "step", None)
    encoding = str(getattr(image_msg, "encoding", "") or "").lower()

    if raw_bytes is None or not isinstance(height, int) or not isinstance(width, int):
        return None
    if height <= 0 or width <= 0:
        return None

    channels = {"mono8": 1, "rgb8": 3, "bgr8": 3}.get(encoding)
    if channels is None:
        return None

    expected_step = width * channels
    stride = int(step) if isinstance(step, int) and step >= expected_step else expected_step
    expected_size = height * stride
    if len(raw_bytes) < expected_size:
        return None

    try:
        import cv2
        import numpy as np
    except ImportError:
        return None

    buffer = np.frombuffer(raw_bytes[:expected_size], dtype=np.uint8).reshape((height, stride))
    if channels == 1:
        image = buffer[:, :width]
    else:
        image = buffer[:, : expected_step].reshape((height, width, channels))
        if encoding == "rgb8":
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return None
    return encoded.tobytes()


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
        target_label: str = "",
    ) -> InferenceResponse:
        observation = ros_image_to_observation(image_msg)
        if target_label:
            observation.metadata["target_label"] = target_label
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
