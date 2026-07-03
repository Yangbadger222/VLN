from threading import Thread

from navida_deploy.http_client import post_inference
from navida_deploy.http_service import create_server
from navida_deploy.messages import InferenceRequest, Observation


JPEG = b"\xff\xd8\xff\xd9"


def test_http_roundtrip_returns_api_v1_chunks():
    server = create_server(("127.0.0.1", 0))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        request = InferenceRequest(
            session_id="demo",
            step_index=0,
            observation=Observation(
                image_bytes=JPEG,
                metadata={"camera": "test"},
            ),
            instruction="go forward",
        )

        response = post_inference(
            f"http://127.0.0.1:{server.server_port}/v1/infer",
            request,
        )

        assert response.api_version == "1.0"
        assert response.session_id == "demo"
        assert response.command_type == "action_chunks"
        assert response.chunks
        assert response.waypoints == []
        assert response.stop is False
        assert response.metadata["backend"] == "mock"
        assert response.metadata["inference_ms"] >= 0

    finally:
        server.shutdown()
        thread.join()
