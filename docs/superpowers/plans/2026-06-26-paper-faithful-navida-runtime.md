# Paper-Faithful NaVIDA Runtime Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement history-frame NaVIDA inference and action-chunk execution as the default paper-faithful runtime path.

**Architecture:** Extend the request model to carry prior compressed camera frames, make the ROS gateway/controller send a rolling history, make the HF backend prompt NaVIDA with multi-image observations, and make detector fallback opt-in.

**Tech Stack:** Python dataclasses, urllib HTTP codec, ROS 2 Python node, Hugging Face Transformers, pytest.

---

### Task 1: Observation History Payload

**Files:**
- Modify: `navida_deploy/messages.py`
- Modify: `navida_deploy/codec.py`
- Test: `tests/test_message_codec.py`

- [ ] **Step 1: Write the failing codec test**

Add a test that creates `Observation(image_bytes=b"current", history_image_bytes=[b"old1", b"old2"])`, round-trips it through `request_to_dict` and `request_from_dict`, and asserts that current and history bytes survive.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_message_codec.py::test_request_codec_roundtrip_with_history_images`

Expected: FAIL because `history_image_bytes` is not present.

- [ ] **Step 3: Add the minimal data model and codec support**

Add `history_image_bytes: list[bytes] = field(default_factory=list)` to `Observation`, encode it as a list of base64 strings, and decode missing fields as an empty list.

- [ ] **Step 4: Run codec tests**

Run: `PYTHONPATH=. pytest -q tests/test_message_codec.py tests/test_codec.py`

Expected: PASS.

### Task 2: ROS Gateway History

**Files:**
- Modify: `navida_deploy/ros2_bridge.py`
- Test: `tests/test_ros2_bridge.py`

- [ ] **Step 1: Write the failing gateway test**

Add a test that calls `NavidaRos2Gateway.infer(..., history_image_bytes=[b"old"])` and asserts the posted request contains `observation.history_image_bytes == [b"old"]`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_ros2_bridge.py::test_ros2_gateway_posts_history_images`

Expected: FAIL because the gateway does not accept history frames.

- [ ] **Step 3: Add `history_image_bytes` to gateway inference**

Extend `NavidaRos2Gateway.infer` with an optional `history_image_bytes` argument and copy it onto the generated observation.

- [ ] **Step 4: Run bridge tests**

Run: `PYTHONPATH=. pytest -q tests/test_ros2_bridge.py`

Expected: PASS.

### Task 3: HF Backend Multi-Image Prompt and Action Chunks

**Files:**
- Modify: `navida_deploy/hf_backend.py`
- Test: `tests/test_hf_backend.py`

- [ ] **Step 1: Write failing tests**

Add tests that verify:

- `build_navida_messages` includes history frames plus current frame as image content.
- `parse_action_text` accepts JSON object actions with repeat counts.
- detector fallback is not used unless explicitly enabled.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=. pytest -q tests/test_hf_backend.py`

Expected: FAIL on the new behavior.

- [ ] **Step 3: Implement multi-image decoding and parsing**

Add an image-list decoder, update the prompt to reference historical observations, support action objects in JSON, and add `target_detector_fallback: bool = False`.

- [ ] **Step 4: Run HF backend tests**

Run: `PYTHONPATH=. pytest -q tests/test_hf_backend.py`

Expected: PASS.

### Task 4: Remote Controller History Buffer

**Files:**
- Modify: `ros2_ws/src/navida_vehicle/navida_vehicle/remote_controller.py`
- Modify: `ros2_ws/src/navida_vehicle/launch/navida_jetson.launch.py`
- Modify: `ros2_ws/src/navida_vehicle/config/navida_jetson.yaml`
- Test: existing unit tests and import checks

- [ ] **Step 1: Add `history_size` parameter**

Declare `history_size` in the node, launch file, and config.

- [ ] **Step 2: Maintain compressed frame history**

Use the current observation bytes from `ros_image_to_observation`, send a snapshot of prior frames, then append the current compressed bytes to a bounded deque.

- [ ] **Step 3: Preserve fallback behavior**

Keep visual servoing available only when backend metadata contains a visible target.

- [ ] **Step 4: Run ROS-related tests**

Run: `PYTHONPATH=. pytest -q tests/test_ros2_bridge.py tests/test_ros2_node_shell.py tests/test_camera_publisher.py`

Expected: PASS.

### Task 5: CLI, Docs, and Verification

**Files:**
- Modify: `scripts/run_inference_server.py`
- Modify: `README.md`

- [ ] **Step 1: Add server fallback flag**

Add `--target-detector-fallback` with default false and pass it to `HuggingFaceQwen25VLBackend`.

- [ ] **Step 2: Document paper-faithful mode**

Update README commands so the default 4070 service runs NaVIDA action chunks, with object detector fallback clearly labeled optional.

- [ ] **Step 3: Run full test suite**

Run: `PYTHONPATH=. pytest -q`

Expected: PASS.

- [ ] **Step 4: Deploy and smoke test**

Pull the branch on 4070 and Jetson, restart the 4070 service, verify `/health`, and send one Jetson camera request to ensure the service returns an action response.
