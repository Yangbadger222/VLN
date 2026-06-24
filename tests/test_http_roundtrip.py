from threading import Thread

from navida_deploy.http_client import post_inference
from navida_deploy.http_service import create_server
from navida_deploy.messages import InferenceRequest, Observation


def test_http_roundtrip_returns_chunks():
    server = create_server(("127.0.0.1", 0))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = InferenceRequest(
            session_id="demo",
            step_index=0,
            observation=Observation(image_path="sample.jpg"),
            instruction="go forward",
        )
        response = post_inference(f"http://127.0.0.1:{server.server_port}/v1/infer", request)
        assert response.session_id == "demo"
        assert response.chunks
    finally:
        server.shutdown()
        thread.join()
