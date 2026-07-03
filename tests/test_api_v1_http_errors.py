import base64
import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from navida_deploy.http_service import create_server


JPEG_B64 = base64.b64encode(b"\xff\xd8\xff\xd9").decode("ascii")


def _start_server():
    server = create_server(("127.0.0.1", 0))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _post_raw(url: str, body: bytes):
    request = Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _valid_payload():
    return {
        "api_version": "1.0",
        "session_id": "api-v1-test",
        "step_index": 0,
        "instruction": "go forward",
        "observation": {
            "image_bytes": JPEG_B64,
            "history_image_bytes": [],
            "metadata": {},
        },
    }


def test_malformed_json_returns_structured_400_and_server_survives():
    server, thread = _start_server()

    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/infer"
        status, payload = _post_raw(url, b"{invalid-json")

        assert status == 400
        assert payload["api_version"] == "1.0"
        assert payload["error"]["code"] == "INVALID_JSON"

        with urlopen(
            f"http://127.0.0.1:{server.server_port}/health",
            timeout=5,
        ) as response:
            health = json.loads(response.read())

        assert health == {"status": "ok"}

    finally:
        server.shutdown()
        thread.join()


def test_missing_observation_returns_invalid_request():
    server, thread = _start_server()

    try:
        payload = _valid_payload()
        del payload["observation"]

        status, response = _post_raw(
            f"http://127.0.0.1:{server.server_port}/v1/infer",
            json.dumps(payload).encode("utf-8"),
        )

        assert status == 400
        assert response["session_id"] == "api-v1-test"
        assert response["step_index"] == 0
        assert response["error"]["code"] == "INVALID_REQUEST"

    finally:
        server.shutdown()
        thread.join()


def test_unsupported_api_version_returns_structured_error():
    server, thread = _start_server()

    try:
        payload = _valid_payload()
        payload["api_version"] = "0.9"

        status, response = _post_raw(
            f"http://127.0.0.1:{server.server_port}/v1/infer",
            json.dumps(payload).encode("utf-8"),
        )

        assert status == 400
        assert response["error"]["code"] == "UNSUPPORTED_API_VERSION"

    finally:
        server.shutdown()
        thread.join()


def test_invalid_base64_returns_structured_error():
    server, thread = _start_server()

    try:
        payload = _valid_payload()
        payload["observation"]["image_bytes"] = "not-valid-base64!"

        status, response = _post_raw(
            f"http://127.0.0.1:{server.server_port}/v1/infer",
            json.dumps(payload).encode("utf-8"),
        )

        assert status == 400
        assert response["error"]["code"] == "INVALID_BASE64"

    finally:
        server.shutdown()
        thread.join()


def test_valid_request_returns_full_api_v1_shape():
    server, thread = _start_server()

    try:
        status, response = _post_raw(
            f"http://127.0.0.1:{server.server_port}/v1/infer",
            json.dumps(_valid_payload()).encode("utf-8"),
        )

        assert status == 200
        assert response["api_version"] == "1.0"
        assert response["command_type"] == "action_chunks"
        assert response["waypoints"] == []
        assert response["stop"] is False
        assert response["metadata"]["backend"] == "mock"
        assert response["metadata"]["inference_ms"] >= 0
        assert "final" not in response

    finally:
        server.shutdown()
        thread.join()
