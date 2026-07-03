from navida_deploy.codec import (
    request_from_dict,
    request_to_dict,
    response_from_dict,
    response_to_dict,
)
from navida_deploy.messages import (
    ActionChunk,
    InferenceRequest,
    InferenceResponse,
    LocalWaypoint,
    Observation,
)


JPEG = b"\xff\xd8\xff\xd9"


def test_request_codec_roundtrip_with_bytes():
    original = InferenceRequest(
        session_id="s1",
        step_index=7,
        observation=Observation(
            image_bytes=JPEG,
            metadata={"camera": "front"},
        ),
        instruction="go forward",
    )

    payload = request_to_dict(original)
    restored = request_from_dict(payload)

    assert payload["api_version"] == "1.0"
    assert "image_path" not in payload["observation"]
    assert restored == original


def test_response_codec_roundtrip_with_target_metadata():
    original = InferenceResponse(
        session_id="s1",
        step_index=8,
        chunks=[ActionChunk(index=0, action="forward")],
        metadata={
            "backend": "test",
            "inference_ms": 1.25,
            "target": {
                "visible": True,
                "center_x": 0.5,
                "area": 0.2,
                "confidence": 0.9,
            },
        },
    )

    payload = response_to_dict(original)
    restored = response_from_dict(payload)

    assert payload["api_version"] == "1.0"
    assert payload["command_type"] == "action_chunks"
    assert payload["waypoints"] == []
    assert payload["stop"] is False
    assert "final" not in payload
    assert restored == original


def test_local_waypoint_response_roundtrip():
    original = InferenceResponse(
        session_id="waypoint-session",
        step_index=2,
        command_type="local_waypoints",
        chunks=[],
        waypoints=[
            LocalWaypoint(x=0.5, y=0.1, yaw=0.2),
            LocalWaypoint(x=1.0, y=0.0, yaw=0.0),
        ],
        stop=False,
        metadata={
            "backend": "waypoint-test",
            "inference_ms": 2.0,
        },
    )

    restored = response_from_dict(response_to_dict(original))

    assert restored == original


def test_legacy_response_can_still_be_read():
    restored = response_from_dict(
        {
            "session_id": "legacy-session",
            "step_index": 0,
            "chunks": [
                {
                    "index": 0,
                    "action": "forward",
                    "repeat": 1,
                }
            ],
            "final": True,
        }
    )

    assert restored.api_version == "1.0"
    assert restored.command_type == "action_chunks"
    assert restored.stop is False
    assert restored.final is True
    assert restored.metadata["backend"] == "legacy"
