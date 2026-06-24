from __future__ import annotations

from .messages import InferenceRequest, Observation
from .codec import response_to_dict
from .server import run_mock_inference


def build_request(
    session_id: str,
    step_index: int,
    instruction: str,
    image_path: str | None = None,
) -> InferenceRequest:
    return InferenceRequest(
        session_id=session_id,
        step_index=step_index,
        observation=Observation(image_path=image_path),
        instruction=instruction,
    )


def demo_roundtrip() -> dict:
    request = build_request(
        "demo-session",
        0,
        "go forward then turn left",
        image_path="sample.jpg",
    )
    response = run_mock_inference(request)
    return response_to_dict(response)
