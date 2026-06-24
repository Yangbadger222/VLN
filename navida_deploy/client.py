from __future__ import annotations

from .messages import InferenceRequest, Observation
from .server import run_mock_inference, response_to_dict


def build_request(session_id: str, step_index: int, image_path: str | None = None) -> InferenceRequest:
    return InferenceRequest(
        session_id=session_id,
        step_index=step_index,
        observation=Observation(image_path=image_path),
    )


def demo_roundtrip() -> dict:
    request = build_request("demo-session", 0, image_path="sample.jpg")
    response = run_mock_inference(request)
    return response_to_dict(response)

