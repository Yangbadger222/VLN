# Week 1 Server Baseline

## 1. Purpose

This document records the baseline environment, installation issues, test results, and current Mock inference server status for the SURF VLN project.

The current validation scope is:

```text
Mock inference server
        ↓
HTTP client
        ↓
InferenceResponse
```

This stage does not use the real NaVIDA or Qwen-RobotNav backend.

---

## 2. Test Environment

| Item | Value |
|---|---|
| Date | 2026-07-02 |
| Operating system | Ubuntu 22.04 |
| Python | 3.10.12 |
| pip | 26.1.2 |
| pytest | 9.1.1 |
| ROS version | ROS 2 Humble |
| Project directory | `/home/evens/SURF/VLN` |
| Virtual environment | `/home/evens/SURF/VLN/.venv` |
| Backend | `mock` |
| Host | `0.0.0.0` |
| Port | `50051` |
| Health endpoint | `/health` |
| Inference endpoint | `/v1/infer` |

The project package was imported from:

```text
/home/evens/SURF/VLN/navida_deploy/__init__.py
```

---

## 3. Installation Baseline

### 3.1 Initial command

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
```

### 3.2 Initial editable-install failure

The first installation attempt failed with:

```text
Project file:///home/evens/SURF/VLN has a 'pyproject.toml'
and its build backend is missing the 'build_editable' hook.

Since it does not have a 'setup.py' nor a 'setup.cfg',
it cannot be installed in editable mode.
```

Classification:

```text
Environment problem
Dependency problem
```

The initial command used the system Python environment. System and user-level Python packages were mixed, and pip fell back to a user installation because the normal site-packages directory was not writable.

This was not identified as a repository business-logic defect.

### 3.3 Resolution

A project-local virtual environment was created and activated:

```bash
cd ~/SURF/VLN
python3 -m venv .venv
source .venv/bin/activate
```

The packaging tools were upgraded:

```bash
python -m pip install -U "pip>=24" "setuptools>=68,<80" wheel
```

The project was installed in editable mode using the virtual environment:

```bash
python -m pip install --no-build-isolation -e ".[dev]"
```

The project package could then be imported successfully.

---

## 4. Pytest Environment Issue

### 4.1 Failure before test collection

The first pytest run inside `.venv` still failed before collecting repository tests.

The error path was:

```text
pytest
→ automatically loads ROS 2 launch_testing plugin
→ imports ROS 2 launch
→ imports lark
→ ModuleNotFoundError: No module named 'lark'
```

The relevant plugin was loaded from:

```text
/opt/ros/humble/lib/python3.10/site-packages/launch_testing
```

Classification:

```text
Environment problem
Dependency-isolation problem
```

This failure occurred before repository test collection, so it was not counted as a repository test failure.

### 4.2 Resolution

Automatic loading of external pytest plugins was disabled:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

---

## 5. Final Test Result

Final command:

```bash
cd ~/SURF/VLN
source .venv/bin/activate
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Final output:

```text
..................................................                       [100%]
50 passed in 1.37s
```

| Item | Result |
|---|---:|
| Total tests | 50 |
| Passed | 50 |
| Failed | 0 |
| Errors | 0 |
| Execution time | 1.37 s |

Conclusion:

```text
All current Python tests passed.
```

The raw test log is stored at:

```text
logs/week1/pytest.txt
```

Recommended command in a terminal where ROS 2 Humble has already been sourced:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

---

## 6. Mock Server Startup

### 6.1 Start command

```bash
cd ~/SURF/VLN
source .venv/bin/activate
mkdir -p logs/week1

PYTHONUNBUFFERED=1 python scripts/run_inference_server.py \
  --backend mock \
  --host 0.0.0.0 \
  --port 50051 \
  2>&1 | tee logs/week1/server.log
```

### 6.2 Startup output

```text
listening on http://0.0.0.0:50051/v1/infer with backend=mock
```

| Check | Result |
|---|---|
| Server process started | Passed |
| Mock backend selected | Passed |
| Host binding | Passed |
| Port binding | Passed |
| Inference endpoint announced | Passed |

Local server address:

```text
http://127.0.0.1:50051
```

For later LAN integration, B and C must use the Ubuntu host IP instead of `127.0.0.1`.

---

## 7. Health Check

### 7.1 Command

```bash
curl -i http://127.0.0.1:50051/health
```

### 7.2 Observed response

```text
HTTP/1.0 200 OK
Server: BaseHTTP/0.6 Python/3.10.12
Date: Thu, 02 Jul 2026 10:39:20 GMT
Content-Type: application/json
Content-Length: 16
```

| Check | Result |
|---|---|
| Server reachable | Passed |
| HTTP status | `200 OK` |
| Content type | `application/json` |
| Health endpoint available | Passed |

Conclusion:

```text
GET /health passed.
```

---

## 8. Single Inference Request

### 8.1 Client command

```bash
python scripts/run_http_client.py
```

### 8.2 Observed response

```text
InferenceResponse(
    session_id='demo-session',
    step_index=0,
    chunks=[
        ActionChunk(
            index=0,
            action='forward',
            repeat=1,
            score=None
        ),
        ActionChunk(
            index=1,
            action='turn_left',
            repeat=1,
            score=None
        )
    ],
    final=True,
    metadata={}
)
```

### 8.3 Response validation

| Field | Observed value | Result |
|---|---|---|
| `session_id` | `demo-session` | Valid |
| `step_index` | `0` | Valid |
| First action | `forward` | Valid |
| Second action | `turn_left` | Valid |
| `repeat` | `1` | Valid |
| `final` | `True` | Valid |
| Client parsing | Successful | Passed |

Valid action set:

```text
forward
turn_left
turn_right
stop
```

Both returned actions are valid.

Conclusion:

```text
One normal POST /v1/infer request passed.
```

---

## 9. Current Status

Completed:

- [x] Created a project-local virtual environment
- [x] Installed the project in editable mode
- [x] Resolved the initial packaging-tool conflict
- [x] Identified the ROS 2 pytest plugin conflict
- [x] Ran repository tests with external plugin autoload disabled
- [x] Passed all 50 current Python tests
- [x] Started the Mock inference server
- [x] Verified `GET /health`
- [x] Verified one normal `POST /v1/infer`
- [x] Verified that the HTTP client parses `InferenceResponse`
- [x] Saved the pytest raw log
- [x] Started saving the server runtime log

Pending:

- [x] Send at least 10 consecutive inference requests
- [x] Confirm all 10 requests return valid responses
- [x] Confirm the server remains alive after repeated requests
- [x] Test malformed JSON
- [x] Test missing request fields
- [x] Test an incorrect endpoint
- [x] Check whether errors are clearly logged
- [x] Check whether malformed requests terminate only the request thread or the whole server
- [ ] Confirm the LAN IP to be used by B and C
- [x] Complete the final stability conclusion

---

## 10. Known Issues

### 10.1 Editable installation failed in the initial system environment

| Item | Description |
|---|---|
| Type | Environment / dependency |
| Status | Resolved |
| Cause | Mixed system-level and user-level Python packages |
| Resolution | Used a project-local `.venv` and upgraded packaging tools |
| Demonstration impact | None |

### 10.2 ROS 2 pytest plugin was loaded automatically

| Item | Description |
|---|---|
| Type | Environment / dependency isolation |
| Status | Resolved |
| Cause | `launch_testing` was automatically discovered from the ROS 2 installation |
| Error | `ModuleNotFoundError: No module named 'lark'` |
| Resolution | Set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` |
| Demonstration impact | None |

### 10.3 Server request logging has not yet been fully evaluated

| Item | Description |
|---|---|
| Type | Logging |
| Status | Open |
| Current observation | The startup message is saved in `server.log` |
| Remaining check | Verify logs for normal and malformed requests |
| Demonstration impact | Not currently blocking server startup or inference |

---

## 11. Reproduction Commands

Activate the environment:

```bash
cd ~/SURF/VLN
source .venv/bin/activate
```

Run tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Expected result:

```text
50 passed
```

Start the Mock server:

```bash
PYTHONUNBUFFERED=1 python scripts/run_inference_server.py \
  --backend mock \
  --host 0.0.0.0 \
  --port 50051
```

Run the health check:

```bash
curl -i http://127.0.0.1:50051/health
```

Run the existing HTTP client:

```bash
python scripts/run_http_client.py
```

---

## 12. Files

| File | Purpose |
|---|---|
| `logs/week1/pytest.txt` | Environment information and raw pytest output |
| `logs/week1/server.log` | Mock server startup and runtime output |
| `docs/week1/server_baseline.md` | Human-readable server baseline report |

---

## 13. Preliminary Conclusion

The current evidence supports the following conclusions:

1. The project can be installed in an isolated Python 3.10.12 virtual environment.
2. All 50 current Python tests pass.
3. The Mock server starts successfully on port `50051`.
4. The `/health` endpoint returns HTTP 200.
5. The existing HTTP client successfully calls `/v1/infer`.
6. The returned action chunks are valid and are parsed into an `InferenceResponse`.
7. The initial failures were environment and dependency-isolation issues.
8. No code issue currently blocks the single-request Mock inference demonstration.

Current conclusion:

```text
A2 Mock server baseline passed with a known error-handling limitation.
Repeated valid requests are stable, but malformed requests currently receive an empty reply instead of a structured HTTP error response.
```

---

## 14. Final A2 Acceptance Result

### 14.1 Acceptance date

```text
2026-07-02 20:01 CST
```

### 14.2 Acceptance scope

The A2 acceptance test covered:

```text
Mock server startup
→ initial health check
→ 10 consecutive valid inference requests
→ health check after repeated requests
→ incorrect endpoint request
→ malformed JSON request
→ missing required field request
→ final health check
→ server log inspection
```

### 14.3 Initial health check

Request:

```bash
curl -sS -i --max-time 5 \
  http://127.0.0.1:50051/health
```

Observed response:

```text
HTTP/1.0 200 OK
Server: BaseHTTP/0.6 Python/3.10.12
Date: Thu, 02 Jul 2026 12:01:04 GMT
Content-Type: application/json
Content-Length: 16

{"status": "ok"}
```

Result:

```text
PASS
```

### 14.4 Ten-request stability test

Ten consecutive valid requests were sent to:

```text
http://127.0.0.1:50051/v1/infer
```

Observed result:

```text
request=01 step_index=0 actions=['forward', 'turn_left'] final=True status=PASS
request=02 step_index=1 actions=['forward', 'turn_left'] final=True status=PASS
request=03 step_index=2 actions=['forward', 'turn_left'] final=True status=PASS
request=04 step_index=3 actions=['forward', 'turn_left'] final=True status=PASS
request=05 step_index=4 actions=['forward', 'turn_left'] final=True status=PASS
request=06 step_index=5 actions=['forward', 'turn_left'] final=True status=PASS
request=07 step_index=6 actions=['forward', 'turn_left'] final=True status=PASS
request=08 step_index=7 actions=['forward', 'turn_left'] final=True status=PASS
request=09 step_index=8 actions=['forward', 'turn_left'] final=True status=PASS
request=10 step_index=9 actions=['forward', 'turn_left'] final=True status=PASS
SUMMARY: 10/10 requests passed
```

Validation performed for every response:

- `session_id` matched the request;
- `step_index` matched the request;
- `chunks` was not empty;
- all returned actions belonged to the legal action set;
- the response was parsed successfully by the existing HTTP client.

Legal action set:

```text
forward
turn_left
turn_right
stop
```

Result:

```text
10/10 PASS
```

### 14.5 Health after repeated requests

Observed response:

```text
HTTP/1.0 200 OK
Server: BaseHTTP/0.6 Python/3.10.12
Date: Thu, 02 Jul 2026 12:01:04 GMT
Content-Type: application/json
Content-Length: 16

{"status": "ok"}
```

Result:

```text
PASS
```

The server remained operational after all 10 valid requests.

### 14.6 Incorrect endpoint test

Request:

```text
GET /not-found
```

Observed response:

```text
HTTP/1.0 404 not found
Server: BaseHTTP/0.6 Python/3.10.12
Connection: close
Content-Type: text/html;charset=utf-8
Content-Length: 447
```

Result:

```text
PASS
```

The server correctly rejected an unknown endpoint with HTTP 404.

### 14.7 Malformed JSON test

A malformed JSON body was sent to:

```text
POST /v1/infer
```

Client-side result:

```text
curl: (52) Empty reply from server
```

Server-side log:

```text
json.decoder.JSONDecodeError:
Expecting property name enclosed in double quotes:
line 1 column 2 (char 1)
```

Interpretation:

- the malformed request caused an uncaught exception in the request thread;
- the client received an empty reply;
- the server process did not exit;
- the later health check still returned HTTP 200.

Result:

```text
SERVER SURVIVAL: PASS
STRUCTURED ERROR RESPONSE: FAIL / NOT IMPLEMENTED
```

### 14.8 Missing required field test

A JSON request without the required `observation` field was sent.

Client-side result:

```text
curl: (52) Empty reply from server
```

Server-side log:

```text
KeyError: 'observation'
```

Interpretation:

- the incomplete request caused an uncaught exception in the request thread;
- the client received an empty reply;
- the server process did not exit;
- the later health check still returned HTTP 200.

Result:

```text
SERVER SURVIVAL: PASS
STRUCTURED ERROR RESPONSE: FAIL / NOT IMPLEMENTED
```

### 14.9 Final health check

Observed response:

```text
HTTP/1.0 200 OK
Server: BaseHTTP/0.6 Python/3.10.12
Date: Thu, 02 Jul 2026 12:01:04 GMT
Content-Type: application/json
Content-Length: 16

{"status": "ok"}
```

Result:

```text
PASS
```

The final health check confirms that malformed and incomplete requests did not terminate the server process.

### 14.10 Server log result

The server log contained:

- the server startup message;
- a complete traceback for malformed JSON;
- a complete traceback for the missing `observation` field.

Observed startup line:

```text
listening on http://0.0.0.0:50051/v1/infer with backend=mock
```

Observed malformed JSON exception:

```text
json.decoder.JSONDecodeError
```

Observed missing-field exception:

```text
KeyError: 'observation'
```

Normal successful requests were not individually written to `server.log`.

### 14.11 Known limitation

Malformed or incomplete requests are not currently converted into structured HTTP error responses.

Current behavior:

```text
invalid request
→ uncaught exception in request thread
→ client receives empty reply
→ traceback is written to server log
→ server remains operational
```

Expected future behavior:

```text
invalid request
→ HTTP 400
→ structured JSON error response
→ concise and explicit server log
→ server remains operational
```

This limitation does not block the current Week 1 Mock-server demonstration, but it should be recorded for later server hardening.

### 14.12 Acceptance summary

| Requirement | Result |
|---|---|
| Server starts normally | Passed |
| `/health` is available | Passed |
| `/v1/infer` is available | Passed |
| At least 10 consecutive requests | Passed |
| Ten valid responses | Passed, 10/10 |
| Session and step matching | Passed |
| Legal actions only | Passed |
| Server alive after repeated requests | Passed |
| Incorrect endpoint returns 404 | Passed |
| Malformed request produces a log | Passed |
| Missing-field request produces a log | Passed |
| Malformed request does not terminate server | Passed |
| Missing-field request does not terminate server | Passed |
| Structured HTTP error response | Not implemented |
| Blocks Week 1 demonstration | No |

### 14.13 Final A2 verdict

```text
A2 accepted with one known error-handling limitation.

The Mock server is stable for repeated valid requests.
Malformed or incomplete requests do not terminate the server,
but currently receive an empty reply instead of a structured HTTP 400 response.

There is no blocker for the Week 1 Mock-server demonstration.
```

### 14.14 Acceptance evidence

Raw acceptance outputs are stored at:

```text
logs/week1/server_acceptance.txt
logs/week1/server.log
```
