# Week 1 Test Results - 2026-07-06

## Baseline

- Host: `sousuke-Legion-Y7000P-IRX9`
- Repository: `~/Desktop/VLN`
- Branch: `codex/navida-deploy-scaffold`
- Commit: `5032a2c`
- API version: `1.0`
- Server endpoint: `http://127.0.0.1:50051/v1/infer`

## Summary

| Area | Result | Evidence |
|---|---|---|
| API v1 automated tests | Passed | `57 passed in 4.46s` |
| Mock server health | Passed | `GET /health -> {"status":"ok"}` |
| Python client | Passed | API v1 response with `action_chunks` |
| ROS2 workspace build | Passed | `serial`, `serial_twistctl`, `navida_vehicle` built |
| Camera-to-ROS2 smoke test | Passed | `camera_publisher` opened `/dev/video0` |
| ROS2 Mock action loop | Passed | `/cmd_vel` published non-zero Twist, then zero Twist |
| Server-down safety | Passed | connection refused produced zero Twist only |
| Target external camera | Not tested | Target camera not connected yet |
| Real chassis serial | Not tested | `/dev/serial_twistctl` missing |

## API v1 Test

Command result:

```text
57 passed in 4.46s
```

Evidence file:

```text
logs/week1/api_v1_pytest_rerun.txt
```

## Mock Server

Observed:

```text
listening on http://0.0.0.0:50051/v1/infer with backend=mock
GET /health -> HTTP 200
POST /v1/infer -> HTTP 200
```

Python client returned an API v1 response containing:

```text
api_version = 1.0
command_type = action_chunks
chunks = forward, turn_left
waypoints = []
stop = false
metadata.backend = mock
```

Evidence file:

```text
logs/week1/server_api_v1_rerun.log
```

## ROS2 Normal Path

ROS2 build result:

```text
serial
serial_twistctl
navida_vehicle
```

Launch result:

```text
camera_publisher opened /dev/video0
remote_controller subscribed to /navida/camera/image_raw
remote_controller published /cmd_vel
```

Observed `/cmd_vel` pattern:

```text
linear.x = 0.15
angular.z = 0.0

linear.x = 0.0
angular.z = 0.0
```

Conclusion:

```text
The ROS2 Mock action loop reached /cmd_vel and produced zero Twist after motion.
```

Evidence files:

```text
logs/week1/ros2_node_api_v1_rerun.log
logs/week1/cmd_vel_api_v1_rerun.log
```

## Server-Down Safety

Test condition:

```text
Mock server stopped before running ROS2 launch.
```

Observed ROS2 log:

```text
remote inference failed: <urlopen error [Errno 111] Connection refused>
command watchdog expired; publishing zero Twist
```

Observed `/cmd_vel`:

```text
linear.x = 0.0
angular.z = 0.0
```

Conclusion:

```text
When the server is unavailable, remote_controller does not reuse an old action.
It publishes or maintains zero Twist.
```

Evidence files:

```text
logs/week1/ros2_server_down_rerun.log
logs/week1/cmd_vel_server_down_rerun.log
```

## Current Limits

- `/dev/video0` was a system video device on the Ubuntu host. The target external camera has not been connected and verified yet.
- `/dev/serial_twistctl` was not present, so the real chassis serial path was not tested.
- Remaining B-side tests still include URL error, timeout, invalid action, empty action, and stale response handling.
- C-side batch testing and statistics have not started yet.

## Current Project Status

```text
Mock server + ROS2 /cmd_vel minimum loop: passed
Server-down zero Twist safety: passed
Target external camera: pending
Real chassis serial: pending
Batch client and statistics: pending
```
