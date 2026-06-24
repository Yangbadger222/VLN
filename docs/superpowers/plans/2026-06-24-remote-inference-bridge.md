# Remote Inference Bridge Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repo able to send NaVIDA navigation requests from a Jetson-side client to a remote inference service and receive chunked action responses.

**Architecture:** Keep model-free scaffolding in `navida_deploy/` with three layers: message dataclasses, JSON-safe serialization, and a small stdlib HTTP transport. The mock inference logic stays isolated from transport so the same client can later call a real 4070-backed service without changing the robot-side code.

**Tech Stack:** Python 3.9, standard library HTTP server/client, `pytest`.

---

### Chunk 1: JSON-safe message codec

**Files:**
- Create: `navida_deploy/codec.py`
- Modify: `navida_deploy/messages.py`
- Test: `tests/test_codec.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_codec.py -q`
Expected: import error or missing module failure

- [ ] **Step 3: Write minimal implementation**

Implement base64 encoding for `image_bytes` and plain dict conversion for the remaining fields.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_codec.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add navida_deploy/messages.py navida_deploy/codec.py tests/test_codec.py
git commit -m "add json codec for inference messages"
```

### Chunk 2: HTTP transport

**Files:**
- Create: `navida_deploy/http_service.py`
- Create: `navida_deploy/http_client.py`
- Modify: `navida_deploy/server.py`
- Test: `tests/test_http_roundtrip.py`

- [ ] **Step 1: Write the failing test**

```python
from threading import Thread
from navida_deploy.http_client import post_inference
from navida_deploy.http_service import create_server
from navida_deploy.messages import InferenceRequest, Observation


def test_http_roundtrip_returns_chunks():
    server = create_server(("127.0.0.1", 0))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = InferenceRequest("demo", 0, Observation(image_path="sample.jpg"))
        response = post_inference(f"http://127.0.0.1:{server.server_port}/v1/infer", request)
        assert response.session_id == "demo"
        assert response.chunks
    finally:
        server.shutdown()
        thread.join()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_http_roundtrip.py -q`
Expected: module import failure before implementation

- [ ] **Step 3: Write minimal implementation**

Wire a `BaseHTTPRequestHandler` to the existing mock inference function and return JSON.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_http_roundtrip.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add navida_deploy/http_service.py navida_deploy/http_client.py navida_deploy/server.py tests/test_http_roundtrip.py
git commit -m "add http inference bridge"
```

### Chunk 3: Operator entrypoints and docs

**Files:**
- Create: `scripts/run_mock_server.py`
- Create: `scripts/run_http_client.py`
- Modify: `README.md`

- [ ] **Step 1: Add runnable entrypoints**
- [ ] **Step 2: Document the local smoke test**
- [ ] **Step 3: Run the smoke test**
- [ ] **Step 4: Commit**

