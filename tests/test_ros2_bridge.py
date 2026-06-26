from types import SimpleNamespace

import navida_deploy.ros2_bridge as ros2_bridge
from navida_deploy.messages import ActionChunk, InferenceResponse
from navida_deploy.ros2_bridge import NavidaRos2Gateway, ros_image_to_observation


def test_ros_image_to_observation_extracts_bytes_and_metadata():
    image_msg = SimpleNamespace(
        data=b"\x01\x02",
        height=480,
        width=640,
        encoding="rgb8",
        step=1920,
    )

    observation = ros_image_to_observation(image_msg)

    assert observation.image_bytes == b"\x01\x02"
    assert observation.metadata["height"] == 480
    assert observation.metadata["width"] == 640
    assert observation.metadata["encoding"] == "rgb8"


def test_ros_image_to_observation_coerces_sequence_data_to_bytes():
    image_msg = SimpleNamespace(
        data=[1, 2, 255],
        height=1,
        width=1,
        encoding="custom8",
        step=3,
    )

    observation = ros_image_to_observation(image_msg)

    assert observation.image_bytes == b"\x01\x02\xff"


def test_ros_image_to_observation_prefers_compressed_transport_bytes():
    image_msg = SimpleNamespace(
        data=b"\x00\x01\x02\x03\x04\x05",
        height=1,
        width=2,
        encoding="bgr8",
        step=6,
    )

    original_encoder = ros2_bridge._encode_compressed_image
    ros2_bridge._encode_compressed_image = lambda msg: b"jpeg-bytes"
    try:
        observation = ros_image_to_observation(image_msg)
    finally:
        ros2_bridge._encode_compressed_image = original_encoder

    assert observation.image_bytes == b"jpeg-bytes"
    assert observation.metadata["transport_encoding"] == "jpeg"


def test_ros2_gateway_posts_instruction_and_image_message():
    captured = {}

    def fake_post(url, request):
        captured["url"] = url
        captured["request"] = request
        return InferenceResponse(
            session_id=request.session_id,
            step_index=request.step_index,
            chunks=[ActionChunk(index=0, action="forward", repeat=1)],
            final=True,
        )

    gateway = NavidaRos2Gateway("http://127.0.0.1:50051/v1/infer", post=fake_post)
    image_msg = SimpleNamespace(
        data=b"\xaa\xbb",
        height=1,
        width=2,
        encoding="mono8",
        step=2,
    )

    response = gateway.infer(
        session_id="session-1",
        step_index=4,
        instruction="go forward",
        image_msg=image_msg,
    )

    assert captured["url"] == "http://127.0.0.1:50051/v1/infer"
    assert captured["request"].instruction == "go forward"
    assert captured["request"].observation.image_bytes.startswith(b"\xff\xd8")
    assert captured["request"].observation.metadata["transport_encoding"] == "jpeg"
    assert response.chunks[0].action == "forward"
