# Week 1 Integration Plan

## 1. Purpose

This document defines the Week 1 integration procedure for the shared VLN HTTP API v1 system.

The integration path is:

```text
B: ROS 2 vehicle bridge
          \
           -> A: API v1 inference server
          /
C: Habitat or batch client
```

The Mock server is used for the Week 1 protocol and connectivity demonstration.

Real NaVIDA GPU inference is a separate backend validation task.

## 2. Repository baseline

| Item | Value |
|---|---|
| Date | 2026-07-03 |
| Official base branch | `codex/navida-deploy-scaffold` |
| Current A working branch | `week1/protocol-integration` |
| Base commit before local changes | `0dbf28bd888c6bcf11f868a65ded253879ea0ab5` |
| API contract | `docs/interface_v1.md` |
| API version | `1.0` |
| Server port | `50051` |

After the API v1 implementation PR is merged, all members must synchronize from the official base branch before joint integration.

Recommended synchronization command:

```bash
cd ~/SURF/VLN
git fetch upstream
git switch codex/navida-deploy-scaffold
git pull --ff-only upstream codex/navida-deploy-scaffold
```

## 3. Environment setup

```bash
cd ~/SURF/VLN

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -U "pip>=24" "setuptools>=68,<80" wheel
python -m pip install --no-build-isolation -e ".[dev]"
```

Test command:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Current expected result:

```text
57 passed
```

## 4. Mock server startup

A starts the server with:

```bash
cd ~/SURF/VLN
source .venv/bin/activate

PYTHONUNBUFFERED=1 python scripts/run_inference_server.py \
  --backend mock \
  --host 0.0.0.0 \
  --port 50051
```

Local health check:

```bash
curl http://127.0.0.1:50051/health
```

Expected response:

```json
{"status":"ok"}
```

## 5. Network address

Detected LAN address candidate:

```text
192.168.162.129:50051
```

This address is provisional until B and C verify connectivity.

B and C should test:

```bash
ping 192.168.162.129
curl http://192.168.162.129:50051/health
```

If the Ubuntu virtual machine is using NAT and is unreachable from other machines, use one of these options:

1. change the VM network mode to bridged networking;
2. run the server on a directly reachable Linux host;
3. configure explicit host-to-VM port forwarding.

The integration server endpoint is:

```text
http://SERVER_IP:50051/v1/infer
```

B and C must not use `127.0.0.1` unless the server is on the same machine.

## 6. Frozen request requirements

Every API v1 request must contain:

```text
api_version = "1.0"
session_id
step_index
instruction
observation.image_bytes
observation.history_image_bytes
observation.metadata
```

Request rules:

- every new navigation episode uses a new `session_id`;
- every new episode resets `step_index` to `0`;
- each subsequent control step increments `step_index`;
- the current image is sent as Base64 JPEG;
- history images are ordered oldest to newest;
- metadata is always a JSON object, even when empty.

## 7. Frozen response requirements

Clients must validate:

```text
api_version
session_id
step_index
command_type
chunks
waypoints
stop
metadata.backend
metadata.inference_ms
```

Clients must reject:

- mismatched `session_id`;
- mismatched `step_index`;
- unsupported actions;
- invalid waypoint values;
- inconsistent `command_type`;
- malformed JSON responses;
- stale responses from earlier steps.

API v1 clients must use top-level `stop`.

Clients must not infer episode completion from:

- zero velocity;
- an individual `action="stop"` chunk;
- the legacy `final` field.

## 8. B integration checklist

B is responsible for the ROS 2 vehicle bridge.

Required checks:

- ROS image messages are converted to JPEG bytes;
- image colour and orientation are correct;
- history images are ordered correctly;
- instruction text reaches the server;
- `session_id` and `step_index` are correct;
- only the first action chunk is executed;
- every motion pulse is followed by zero velocity;
- timeout produces zero velocity;
- connection failure produces zero velocity;
- malformed or stale responses are rejected;
- `stop=true` terminates the episode;
- no old action is reused after an HTTP failure.

Expected B evidence:

```text
docs/week1/ros2_test.md
logs/week1/ros2_node.log
logs/week1/cmd_vel.log
```

## 9. C integration checklist

C is responsible for the Habitat or batch client.

Required checks:

- current camera frame is encoded as JPEG;
- image colour and orientation are correct;
- history frames are ordered oldest to newest;
- a new episode clears old history;
- a new episode uses a new `session_id`;
- `step_index` resets to zero and then increments;
- HTTP timeout does not reuse an old action;
- invalid responses do not move the agent;
- stale session or step responses are rejected;
- `stop=true` terminates the episode.

Expected C evidence:

```text
docs/week1/batch_report.md
logs/week1/batch_results.jsonl
logs/week1/failures.jsonl
```

## 10. Joint integration sequence

The recommended joint test order is:

1. A starts the Mock server.
2. A verifies local `GET /health`.
3. B verifies remote `GET /health`.
4. C verifies remote `GET /health`.
5. C sends one valid API v1 request.
6. B sends one valid API v1 request.
7. C sends ten consecutive requests.
8. A confirms the server remains healthy.
9. B executes one bounded action pulse.
10. B confirms a zero-velocity command follows the pulse.
11. A sends malformed JSON.
12. A verifies HTTP 400 `INVALID_JSON`.
13. A sends a request with a missing field.
14. A verifies HTTP 400 `INVALID_REQUEST`.
15. A temporarily stops the server.
16. B verifies safe stop after connection failure.
17. C verifies no stale action is executed.
18. A restarts the server.
19. All members repeat the health check.
20. A records the final integration conclusion.

## 11. Integration evidence directory

Individual development evidence remains in:

```text
logs/week1/
```

One complete joint run should use a dedicated directory:

```text
logs/week1/integration/YYYY-MM-DD-run01/
```

Recommended contents:

```text
server.log
ros2_node.log
cmd_vel.log
batch_results.jsonl
failures.jsonl
notes.md
```

The integration directory is organized by test run, not by member.

## 12. Group-meeting demonstration order

Recommended presentation sequence:

1. Show `docs/interface_v1.md`.
2. Explain that code now conforms to the frozen API.
3. Run the complete Python test suite.
4. Show `57 passed`.
5. Start the Mock server.
6. Show `GET /health`.
7. Run one valid inference request.
8. Show API v1 response fields.
9. Send malformed JSON.
10. Show HTTP 400 `INVALID_JSON`.
11. Send a request with a missing field.
12. Show HTTP 400 `INVALID_REQUEST`.
13. Show that the server remains healthy.
14. Show B's ROS 2 and `/cmd_vel` evidence.
15. Show C's batch or Habitat evidence.
16. Present current limitations and next-step work.

## 13. Blocker criteria

A problem is a Week 1 blocker when it causes one of the following:

- the server terminates after a malformed request;
- the server cannot be reached by B or C;
- a client executes movement after timeout or connection failure;
- a stale response is accepted;
- an unsupported action reaches the execution layer;
- `stop=true` is ignored;
- B or C cannot construct an API v1 request;
- B or C cannot parse an API v1 response;
- a motion command is not followed by zero velocity.

The following are not Week 1 Mock-demo blockers:

- real Qwen-RobotNav weights are unavailable;
- local-waypoint execution is not implemented;
- real NaVIDA CUDA latency has not yet been benchmarked;
- advanced structured logging is incomplete.

## 14. Ownership

| Area | Owner |
|---|---|
| API v1 contract | A |
| Server implementation | A |
| Request and response validation | A |
| Structured HTTP errors | A |
| ROS 2 vehicle bridge | B |
| Vehicle safety stop | A and B |
| Habitat or batch client | C |
| Joint integration report | A |
| Final blocker decision | A |

## 15. Current status

A has completed:

- API v1 implementation;
- structured request validation;
- structured response validation;
- structured HTTP errors;
- Mock server acceptance;
- 57 automated tests;
- protocol status documentation;
- integration plan preparation.

Pending work:

- verify the LAN address from B and C machines;
- merge the API v1 implementation PR;
- synchronize B and C branches;
- complete the joint integration run;
- validate the real NaVIDA backend on the RTX 4070 host;
- write the final integration conclusion.
