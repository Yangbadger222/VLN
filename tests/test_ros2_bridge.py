from types import SimpleNamespace

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
    assert captured["request"].observation.image_bytes == b"\xaa\xbb"
    assert response.chunks[0].action == "forward"

