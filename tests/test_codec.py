from navida_deploy.codec import request_from_dict, request_to_dict
from navida_deploy.messages import InferenceRequest, Observation


def test_request_codec_roundtrip_with_bytes():
    original = InferenceRequest(
        session_id="s1",
        step_index=7,
        observation=Observation(image_bytes=b"\x00\x01", metadata={"camera": "front"}),
    )
    payload = request_to_dict(original)
    restored = request_from_dict(payload)

    assert restored == original

