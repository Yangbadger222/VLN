from navida_deploy.codec import request_from_dict, request_to_dict, response_from_dict, response_to_dict
from navida_deploy.messages import ActionChunk, InferenceRequest, InferenceResponse, Observation


def test_request_codec_roundtrip_with_bytes():
    original = InferenceRequest(
        session_id="s1",
        step_index=7,
        observation=Observation(image_bytes=b"\x00\x01", metadata={"camera": "front"}),
        instruction="",
    )
    payload = request_to_dict(original)
    restored = request_from_dict(payload)

    assert restored == original


def test_response_codec_roundtrip_with_target_metadata():
    original = InferenceResponse(
        session_id="s1",
        step_index=8,
        chunks=[ActionChunk(index=0, action="forward")],
        metadata={"target": {"visible": True, "center_x": 0.5, "area": 0.2, "confidence": 0.9}},
    )

    restored = response_from_dict(response_to_dict(original))

    assert restored == original
