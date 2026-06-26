from navida_deploy.codec import request_from_dict, request_to_dict
from navida_deploy.messages import InferenceRequest, Observation


def test_request_codec_roundtrip_with_instruction_and_bytes():
    original = InferenceRequest(
        session_id="s1",
        step_index=7,
        observation=Observation(image_bytes=b"\x00\x01", metadata={"camera": "front"}),
        instruction="go to the kitchen and stop by the chair",
    )
    payload = request_to_dict(original)
    restored = request_from_dict(payload)

    assert restored == original


def test_request_codec_roundtrip_with_history_images():
    original = InferenceRequest(
        session_id="s-history",
        step_index=3,
        observation=Observation(
            image_bytes=b"current",
            history_image_bytes=[b"old-1", b"old-2"],
            metadata={"camera": "front"},
        ),
        instruction="follow the instruction history",
    )

    payload = request_to_dict(original)
    restored = request_from_dict(payload)

    assert payload["observation"]["history_image_bytes"] == ["b2xkLTE=", "b2xkLTI="]
    assert restored == original
