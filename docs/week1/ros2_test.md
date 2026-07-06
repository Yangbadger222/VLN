# ROS2 Bridge Test Evidence - 2026-07-06

## Scope

This file records the B-side evidence requested by the Week 1 integration checklist:

```text
docs/week1/ros2_test.md
logs/week1/ros2_node.log
logs/week1/cmd_vel.log
```

The evidence is based on the recorded 2026-07-06 rerun summary from the local branch history. It captures the ROS2 bridge status for the Mock server integration path.

## Environment

```text
Host: sousuke-Legion-Y7000P-IRX9
Repository: ~/Desktop/VLN
Branch: codex/navida-deploy-scaffold
API version: 1.0
Server endpoint: http://127.0.0.1:50051/v1/infer
```

## Checklist Result

| Check | Result | Evidence |
|---|---|---|
| ROS2 workspace build | Passed | `serial`, `serial_twistctl`, and `navida_vehicle` built |
| Camera image reaches ROS2 | Passed | `camera_publisher` opened `/dev/video0` |
| Image topic reaches bridge | Passed | `remote_controller` subscribed to `/navida/camera/image_raw` |
| Instruction reaches server | Passed | Mock server returned API v1 action chunks |
| First action chunk executed | Passed | `/cmd_vel` published forward motion |
| Motion followed by zero velocity | Passed | `/cmd_vel` returned to zero Twist |
| Connection failure safe stop | Passed | Server-down path produced zero Twist only |
| Old action reused after HTTP failure | Not observed | Server-down path did not continue a previous non-zero action |
| Target external camera | Not tested | Target camera was not connected |
| Real chassis serial path | Not tested | `/dev/serial_twistctl` was missing |
| Timeout, invalid action, empty action, stale response | Pending | Still needs dedicated negative tests |

## Normal ROS2 Mock Path

Observed launch state:

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

## Evidence Files

```text
logs/week1/ros2_node.log
logs/week1/cmd_vel.log
```

