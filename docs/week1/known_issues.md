# Week 1 Known Issues

| ID | Issue | Owner | Type | Status | Demonstration impact | Planned handling |
|---|---|---|---|---|---|---|
| ENV-001 | Editable installation initially failed because system-level and user-level Python packages were mixed | A | Environment / dependency | Resolved | None | Use the project-local `.venv` |
| ENV-002 | ROS 2 `launch_testing` pytest plugin was automatically loaded and failed because `lark` was unavailable in `.venv` | A | Environment / dependency isolation | Resolved | None | Run tests with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` |
| A2-001 | Malformed JSON or missing fields produced an uncaught request-thread exception and an empty HTTP reply | A | Server error handling | Resolved | None | API v1 now returns structured JSON errors with HTTP status codes |
| A2-002 | Normal HTTP requests were not individually written to the server log | A | Logging | Resolved | None | Base HTTP request and error logging is now enabled |
| A3-001 | JPEG validation checks JPEG byte markers instead of performing a complete Pillow or OpenCV decode | A | Image validation | Open | Low for the Mock demonstration | Add full image decoding after image dependencies are finalized |
| A3-002 | The response decoder temporarily accepts the legacy `final` field | A | Compatibility | Open | None | Remove after B and C migrate completely to top-level `stop` |
| A3-003 | Image-size and history-count limits are code constants | A | Configuration | Open | None | Move the limits into server configuration after Week 1 |
| A3-004 | Local-waypoint serialization and validation exist, but no waypoint backend or controller is implemented | A | Backend / control | Open | Does not block action-chunk Mock demonstration | Implement after the action-chunk integration path is stable |
| A4-001 | The candidate VM address has not yet been verified from both B and C machines | A/B/C | Integration network | Pending | Can block cross-machine integration | Verify ping and `/health` from both client machines |
| A4-002 | Real NaVIDA CUDA inference has not yet been accepted on the RTX 4070 host | A | Backend deployment | Pending | Does not block the Mock demonstration | Install server dependencies, load the model and run acceptance tests |
| A4-003 | Joint B/C integration evidence has not yet been collected | A/B/C | Integration | Pending | Blocks the final end-to-end integration claim | Complete the shared integration checklist and save one joint run |
| A4-004 | Vehicle safe-stop behaviour after timeout and connection failure still requires B-side evidence | A/B | Safety | Pending | Can block the physical demonstration | Verify zero velocity and no stale action after failure |

## Current protocol conclusion

The Mock-server API v1 implementation now provides:

- validated API version, session and step fields;
- Base64 JPEG request handling;
- action-chunk and local-waypoint response structures;
- response metadata containing backend name and inference duration;
- structured HTTP error responses;
- request and response correlation checks;
- an HTTP client with timeout and structured error handling.

Current automated result:

```text
57 passed
```

Current live acceptance result:

```text
GET /health                         -> HTTP 200
valid POST /v1/infer                -> HTTP 200
malformed JSON                      -> HTTP 400 INVALID_JSON
missing observation                 -> HTTP 400 INVALID_REQUEST
GET /health after invalid requests  -> HTTP 200
```

There is no remaining API v1 blocker for the Week 1 Mock-server demonstration.

Cross-machine B/C integration, vehicle safety evidence and real NaVIDA GPU validation remain pending.
