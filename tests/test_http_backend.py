import json
from threading import Thread

import navida_deploy.http_client as http_client
from navida_deploy.http_client import post_inference
from navida_deploy.http_service import create_server
from navida_deploy.messages import ActionChunk, InferenceRequest, InferenceResponse, Observation


class EchoBackend:
    def infer(self, request: InferenceRequest) -> InferenceResponse:
        return InferenceResponse(
            session_id=request.session_id,
            step_index=request.step_index,
            chunks=[ActionChunk(index=0, action=request.instruction or "forward", repeat=1)],
            final=True,
        )


def test_http_service_uses_injected_backend():
    server = create_server(("127.0.0.1", 0), backend=EchoBackend())
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = InferenceRequest(
            session_id="demo",
            step_index=3,
            observation=Observation(image_path="sample.jpg"),
            instruction="turn right",
        )
        response = post_inference(f"http://127.0.0.1:{server.server_port}/v1/infer", request)
        assert response.session_id == "demo"
        assert response.chunks[0].action == "turn right"
    finally:
        server.shutdown()
        thread.join()


def test_post_inference_uses_configured_timeout():
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "session_id": "demo",
                    "step_index": 0,
                    "chunks": [{"index": 0, "action": "forward", "repeat": 1}],
                    "final": True,
                }
            ).encode("utf-8")

    original_urlopen = http_client.urlopen

    def fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        return FakeResponse()

    http_client.urlopen = fake_urlopen
    try:
        response = post_inference(
            "http://127.0.0.1:50051/v1/infer",
            InferenceRequest(
                session_id="demo",
                step_index=0,
                observation=Observation(image_bytes=b"raw"),
            ),
            timeout_s=12.5,
        )
    finally:
        http_client.urlopen = original_urlopen

    assert captured["timeout"] == 12.5
    assert response.session_id == "demo"
