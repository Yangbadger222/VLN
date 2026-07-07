# NaVIDA Deployment Scaffold Baseline Before Habitat

Captured: 2026-07-08T00:53:34+08:00

## Scope

This baseline validates the existing NaVIDA deployment scaffold in WSL2 before adding Habitat simulation code.

Constraints followed:

- Habitat was not installed.
- Real NaVIDA model dependencies were not installed.
- No model download was started.
- Qwen-RobotNav was not used.
- ROS2 real-vehicle deployment code was not touched.
- Source files were not modified.
- No files were deleted.

## Repository Context

- Branch: `codex/navida-deploy-scaffold`
- Python executable: `/home/evens/SURF/.venv-navida/bin/python`
- Python version: `3.10.12`
- Package metadata: `pyproject.toml`
- Package: `navida_deploy`
- Scripts inspected: `scripts/run_inference_server.py`, `scripts/run_mock_server.py`, `scripts/run_http_client.py`, `scripts/run_ros2_node.py`
- Tests inspected/run: `tests/`

Relevant dependency layout from `pyproject.toml`:

- `dev`: `opencv-python-headless`, `pytest>=8`
- `server`: `accelerate`, `bitsandbytes`, `pillow`, `qwen_vl_utils`, `torch`, `transformers`
- `jetson`: `opencv-python`

This matters because JPEG compression in `navida_deploy/ros2_bridge.py` uses optional `cv2`/`numpy` imports and falls back to raw image bytes when `cv2` is unavailable. The initial baseline failed because the dev install did not include a package providing `cv2`; the follow-up dev dependency patch adds `opencv-python-headless` for local tests without changing ROS2 runtime behavior.

## Baseline Commands

Editable install with dev dependencies:

```bash
python -m pip install -e ".[dev]"
```

Pytest baseline:

```bash
python -m pytest -q
```

Mock inference server command identified:

```bash
python scripts/run_inference_server.py --backend mock --host 127.0.0.1 --port 50051
```

HTTP client smoke command identified:

```bash
python scripts/run_http_client.py
```

The older wrapper `python scripts/run_mock_server.py` also starts the mock service on port `50051`, but binds `0.0.0.0`; the explicit `run_inference_server.py --backend mock --host 127.0.0.1` form is the clearer local WSL2 baseline command.

## CUDA Status

Manual WSL2 terminal CUDA check: pass.

Recorded manual result:

```text
torch: 2.5.1+cu121
cuda_available: True
device: NVIDIA GeForce RTX 4060 Ti
memory_GB: 8.0
```

Codex/sandbox CUDA visibility:

```text
torch: 2.5.1+cu121
cuda_available: False
torch.version.cuda: 12.1
```

Interpretation: do not conclude that CUDA is unavailable from the Codex/sandbox check alone. The manual WSL2 terminal check shows CUDA works in the target environment. The Codex result should be treated as separate sandbox/tool visibility behavior.

## Results

Editable install:

- Command: `python -m pip install -e ".[dev]"`
- Result: passed after approved network access for pip.
- Installed package: `vln-navida-deploy==0.1.0` editable from `/home/evens/SURF/VLN`
- Initial installed dev dependency: `pytest==9.1.1`
- Follow-up dev dependency added: `opencv-python-headless`
- Real model/server dependencies were not installed.

Pytest baseline:

- Command: `python -m pytest -q`
- First sandbox run: not the real baseline; HTTP tests failed with `PermissionError: [Errno 1] Operation not permitted` when creating loopback sockets.
- Rerun with loopback allowed: real baseline result is `1 failed, 56 passed`.
- Follow-up after installing `opencv-python-headless`: `57 passed in 4.36s`, per `logs/habitat/pytest_after_opencv.txt`.
- Final WSL2 baseline: `57 passed in 4.46s`, per `logs/habitat/pytest_final_baseline.txt`.

Real baseline failure:

```text
tests/test_ros2_bridge.py::test_ros2_gateway_posts_instruction_and_image_message
```

Observed assertion:

```text
assert captured["request"].observation.image_bytes.startswith(b"\xff\xd8")
```

Actual behavior:

```text
captured["request"].observation.image_bytes == b"\xaa\xbb"
```

Likely cause: no `cv2` provider was installed in the initial dev baseline. `navida_deploy/ros2_bridge.py` attempts to import `cv2` and `numpy` for JPEG encoding; when `cv2` is missing, `_encode_compressed_image()` returns `None`, and `ros_image_to_observation()` falls back to raw ROS image bytes. This matches the focused repro and the active environment check:

```text
ModuleNotFoundError: No module named 'cv2'
```

Mock server/client smoke:

- Mock inference server: pass.
- Health endpoint: pass; `logs/habitat/mock_health.txt` records `{"status":"ok"}`.
- HTTP client smoke test: pass.
- Mock backend returned API version `1.0` with action chunks `forward` and `turn_left`.
- Server log confirms both `GET /health` and `POST /v1/infer` returned HTTP 200.

## Known Issues

- The initial dev baseline did not install a `cv2` provider, but one ROS2 bridge test expects JPEG-compressed image bytes.
- Manual WSL2 follow-up confirmed that installing `opencv-python-headless` resolves the remaining pytest failure; `logs/habitat/pytest_after_opencv.txt` records `57 passed in 4.36s`.
- Final WSL2 pytest baseline is clean; `logs/habitat/pytest_final_baseline.txt` records `57 passed in 4.46s`.
- `opencv-python` is currently only declared in the `jetson` optional dependency group.
- Codex sandbox loopback restrictions can produce false HTTP test failures; use the loopback-allowed pytest result as the baseline.
- Codex sandbox CUDA visibility reported `False`; manual WSL2 CUDA check passed and should be interpreted separately.

## Recommended Next Step

Before adding Habitat, keep the clean WSL2 scaffold baseline as the reference point:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/run_inference_server.py --backend mock --host 127.0.0.1 --port 50051
python scripts/run_http_client.py
```

Habitat installation should remain a separate step after this scaffold baseline is reviewed.
