from navida_deploy.codec import request_from_dict, request_to_dict
from navida_deploy.messages import InferenceRequest, Observation


JPEG_CURRENT = b"\xff\xd8current\xff\xd9"
JPEG_OLD_1 = b"\xff\xd8old-1\xff\xd9"
JPEG_OLD_2 = b"\xff\xd8old-2\xff\xd9"


def test_request_codec_roundtrip_with_instruction_and_bytes():
    original = InferenceRequest(
        session_id="s1",
        step_index=7,
        observation=Observation(
            image_bytes=JPEG_CURRENT,
            metadata={"camera": "front"},
        ),
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
            image_bytes=JPEG_CURRENT,
            history_image_bytes=[JPEG_OLD_1, JPEG_OLD_2],
            metadata={"camera": "front"},
        ),
        instruction="follow the instruction history",
    )

    payload = request_to_dict(original)
    restored = request_from_dict(payload)

    assert len(payload["observation"]["history_image_bytes"]) == 2
    assert restored == original
