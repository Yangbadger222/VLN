# Week 1 Known Issues

| ID | Issue | Type | Status | Demonstration impact | Planned handling |
|---|---|---|---|---|---|
| ENV-001 | Editable installation initially failed because system-level and user-level Python packages were mixed | Environment / dependency | Resolved | None | Use the project-local `.venv` |
| ENV-002 | ROS 2 `launch_testing` pytest plugin was automatically loaded and failed because `lark` was unavailable in `.venv` | Environment / dependency isolation | Resolved | None | Run tests with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` |
| A2-001 | Malformed JSON or missing required fields cause an uncaught request-thread exception and an empty HTTP reply instead of a structured HTTP 400 JSON response | Server error handling | Open | Does not terminate the server and does not block the Mock demonstration | Add request validation and structured exception handling after the Week 1 baseline |
| A2-002 | Successful HTTP requests are not individually written to `server.log` because normal request logging is disabled | Logging | Open | Reduces traceability but does not block inference | Add concise structured request logging later |

## Current A2 conclusion

The Mock server passed the Week 1 baseline acceptance test:

- 50 Python tests passed.
- `/health` returned HTTP 200.
- One normal inference request passed.
- Ten consecutive valid requests passed.
- The server remained alive after repeated requests.
- An incorrect endpoint returned HTTP 404.
- Malformed JSON and missing fields produced tracebacks.
- Malformed requests did not terminate the server process.

The remaining error-handling limitation does not block the Week 1 Mock-server demonstration.
