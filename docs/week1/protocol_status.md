# Week 1 Protocol Implementation Status

## 1. Purpose

This document records the implementation status of the frozen VLN HTTP API v1 contract.

The protocol authority remains:

```text
docs/interface_v1.md
```

The API document was not modified during this implementation phase. The Python implementation was updated to conform to the existing API v1 contract.

## 2. Baseline

| Item | Value |
|---|---|
| Date | 2026-07-03 |
| Working branch | `week1/protocol-integration` |
| Base commit before local changes | `0dbf28bd888c6bcf11f868a65ded253879ea0ab5` |
| API version | `1.0` |
| Inference endpoint | `POST /v1/infer` |
| Health endpoint | `GET /health` |
| Mock server port | `50051` |
| Python | `3.10.12` |
| Test result before implementation | `50 passed` |
| Test result after implementation | `57 passed` |

## 3. Contract rule

The Week 1 protocol rule is:

```text
docs/interface_v1.md defines the external HTTP contract.
Python code must conform to that contract.
Internal compatibility must not change the API v1 wire format.
```

## 4. Request implementation status

| API v1 request field | Status | Validation |
|---|---|---|
| `api_version` | Implemented | Must equal `"1.0"` |
| `session_id` | Implemented | Required and non-empty |
| `step_index` | Implemented | Non-negative integer |
| `instruction` | Implemented | Required and non-empty |
| `observation.image_bytes` | Implemented | Required Base64 JPEG |
| `observation.history_image_bytes` | Implemented | Required array, oldest to newest |
| `observation.metadata` | Implemented | Required JSON object |

The external HTTP request no longer exposes the internal `image_path` representation.

When a local Python caller supplies an image path, the codec reads the file and serializes the image bytes into `observation.image_bytes`.

## 5. Response implementation status

| API v1 response field | Status | Validation |
|---|---|---|
| `api_version` | Implemented | Must equal `"1.0"` |
| `session_id` | Implemented | Must match the request |
| `step_index` | Implemented | Must match the request |
| `command_type` | Implemented | `action_chunks` or `local_waypoints` |
| `chunks` | Implemented | Valid action objects only |
| `waypoints` | Implemented | Maximum 8 finite waypoints |
| `stop` | Implemented | Boolean |
| `metadata.backend` | Implemented | Non-empty backend identifier |
| `metadata.inference_ms` | Implemented | Non-negative finite number |

## 6. Action validation

Accepted discrete actions:

```text
forward
turn_left
turn_right
stop
```

The validator rejects:

- unsupported action names;
- negative action indices;
- non-positive repeat counts;
- non-finite confidence scores;
- inconsistent command representations.

An `action_chunks` response must have an empty `waypoints` array.

A `local_waypoints` response must have an empty `chunks` array.

## 7. Local waypoint support

API v1 codec and validation now support local waypoints containing:

```text
x
y
yaw
```

Enforced rules:

- maximum of 8 waypoints;
- all waypoint values must be finite;
- distances use metres;
- yaw uses radians;
- coordinates use the vehicle `base_link` frame.

Week 1 provides protocol-level waypoint support only. A real waypoint backend and trajectory controller are outside this change.

## 8. Structured HTTP errors

The server now returns structured API v1 JSON errors instead of terminating the request with an empty reply.

Verified cases:

| Input | HTTP status | Error code |
|---|---:|---|
| Malformed JSON | 400 | `INVALID_JSON` |
| Missing observation | 400 | `INVALID_REQUEST` |
| Unsupported API version | 400 | `UNSUPPORTED_API_VERSION` |
| Invalid Base64 | 400 | `INVALID_BASE64` |

Verified server-survival sequence:

```text
GET /health                         -> HTTP 200
POST malformed JSON                -> HTTP 400 INVALID_JSON
POST missing observation           -> HTTP 400 INVALID_REQUEST
GET /health after invalid requests -> HTTP 200
```

## 9. HTTP client status

The shared HTTP client now provides:

- configurable timeout;
- API v1 request serialization;
- API v1 response parsing;
- structured HTTP error parsing;
- response validation;
- session-ID correlation;
- step-index correlation.

HTTP failures are represented by `InferenceHTTPError`.

## 10. Backend status

### Mock backend

The Mock backend now returns:

```text
command_type = action_chunks
waypoints = []
stop = false
metadata.backend = mock
metadata.inference_ms >= 0
```

### NaVIDA Hugging Face backend

The Hugging Face backend now constructs the API v1 response model.

Actual inference duration is measured at the HTTP service boundary and written to `metadata.inference_ms`.

Real CUDA model loading and full NaVIDA inference were not tested in this Ubuntu virtual machine.

## 11. Legacy compatibility

The API v1 serializer does not emit the legacy `final` field.

A limited compatibility path remains only in `response_from_dict()`:

```text
legacy response containing final
        ↓
response_from_dict()
        ↓
internal compatibility object
```

This compatibility reduces disruption while B and C migrate.

API v1 clients must use top-level `stop`.

## 12. Validation evidence

### Automated tests

```text
57 passed
```

Evidence:

```text
logs/week1/api_v1_pytest.txt
```

### Live HTTP acceptance

Evidence:

```text
logs/week1/api_v1_acceptance.txt
logs/week1/api_v1_server.log
```

Observed valid response properties:

```text
api_version = 1.0
command_type = action_chunks
waypoints = []
stop = false
metadata.backend = mock
metadata.inference_ms >= 0
```

## 13. Current limitations

1. JPEG validation currently performs protocol-level byte checks rather than a complete Pillow or OpenCV image decode.
2. Local-waypoint serialization and validation exist, but no Week 1 waypoint backend or controller is implemented.
3. The response decoder temporarily accepts the legacy `final` field.
4. Image-size and history-count limits are code constants rather than runtime configuration.
5. Real NaVIDA CUDA inference still requires validation on the RTX 4070 host.
6. Cross-machine integration with B and C remains pending.

## 14. Conclusion

The Python implementation now conforms to the frozen API v1 contract for the Mock-server path.

The previous error-handling blocker has been removed:

```text
Malformed or incomplete requests no longer produce an empty HTTP reply.
They now return structured API v1 JSON errors.
```

Remaining work concerns cross-machine integration and real backend validation rather than the basic protocol implementation.
