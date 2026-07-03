from __future__ import annotations

from .codec import response_to_dict
from .messages import InferenceRequest, Observation
from .server import run_mock_inference


MINIMAL_JPEG = b"\xff\xd8\xff\xd9"


def build_request(
    session_id: str,
    step_index: int,
    instruction: str,
    image_path: str | None = None,
    observation: Observation | None = None,
    image_bytes: bytes | None = None,
) -> InferenceRequest:
    obs = observation or Observation(
        image_path=image_path,
        image_bytes=image_bytes,
    )
    return InferenceRequest(
        session_id=session_id,
        step_index=step_index,
        observation=obs,
        instruction=instruction,
    )


def demo_roundtrip() -> dict:
    request = build_request(
        "demo-session",
        0,
        "go forward then turn left",
        observation=Observation(
            image_bytes=MINIMAL_JPEG,
            metadata={"camera": "demo"},
        ),
    )
    response = run_mock_inference(request)
    return response_to_dict(response)
