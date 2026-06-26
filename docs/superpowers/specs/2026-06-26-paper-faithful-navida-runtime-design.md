# Paper-Faithful NaVIDA Runtime Design

## Goal

Make the deployed runtime follow the NaVIDA paper's control shape more closely: send historical egocentric camera observations plus the current observation and language instruction to the remote NaVIDA backend, then execute returned action chunks as safe `geometry_msgs/msg/Twist` pulses on the Jetson.

## Non-Goals

- Do not make open-vocabulary object detection the primary navigation policy.
- Do not add a hand-written multi-target route state machine as the default VLN path.
- Do not add SLAM, mapping, or global planning in this iteration.

## Architecture

The primary control loop is:

1. Jetson camera node publishes front RGB frames.
2. `navida_remote_controller` keeps a small rolling history of prior compressed frames.
3. Each inference request contains `history_image_bytes`, the current `image_bytes`, and the original instruction.
4. The 4070 HF backend builds a multi-image NaVIDA prompt with historical observations and the current observation.
5. NaVIDA returns action chunks such as `forward`, `turn_left`, `turn_right`, and `stop`, optionally with repeat counts.
6. Jetson converts the first returned chunk to a bounded velocity pulse and publishes `/cmd_vel`.

Open-vocabulary target detection remains optional fallback only. When disabled, missing VLM target metadata no longer triggers OWL-ViT; this prevents the fallback detector from becoming the main policy.

## Data Model

`Observation` gains:

- `history_image_bytes: list[bytes]`

The existing single `image_bytes` field remains the current frame. Codec changes must remain backward compatible with older payloads that do not include `history_image_bytes`.

## Backend Behavior

The HF backend decodes all history frames plus the current frame. The prompt should ask NaVIDA to use the observation sequence and return compact JSON action chunks:

```json
{"actions":[{"action":"forward","repeat":2},{"action":"turn_left","repeat":1}]}
```

The existing plain action parser remains as fallback for non-JSON model output.

## Jetson Behavior

`navida_remote_controller` gains a `history_size` parameter. It sends prior compressed frames with each request and appends the current compressed frame after the request is built.

Safety behavior remains unchanged:

- inference failure publishes zero Twist
- watchdog publishes zero Twist on timeout
- velocity commands are clamped
- each non-stop command is followed by an explicit stop pulse

## Configuration

4070 server:

- `--target-detector-fallback` defaults to false
- `--target-detector-model-id` remains available for fallback experiments

Jetson launch:

- `history_size` defaults to `4`
- `visual_servo_enabled` can stay true, but without target metadata it does not override action chunks

## Testing

Add tests for:

- request codec round-trips `history_image_bytes`
- ROS gateway includes historical frames in requests
- HF backend builds multi-image messages from history plus current frame
- JSON action chunks with repeat counts parse into `ActionChunk`
- remote controller/gateway can pass a history snapshot without changing existing one-frame behavior
