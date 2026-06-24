from threading import Thread

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

