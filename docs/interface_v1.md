# NaVIDA Deployment HTTP API v1

This document defines the JSON interface between a vehicle client and a NaVIDA inference service. API v1 uses the version string `"1.0"` and the inference endpoint `POST /v1/infer`.

Requests and responses use `Content-Type: application/json`. A successful inference returns HTTP 200. Failures use the structured error body described below.

Example payloads are available in [`examples/request.json`](../examples/request.json), [`examples/response_action.json`](../examples/response_action.json), [`examples/response_waypoint.json`](../examples/response_waypoint.json), and [`examples/error_response.json`](../examples/error_response.json).

## Request

Every request has the following shape:

```json
{
  "api_version": "1.0",
  "session_id": "warehouse-run-20260701-001",
  "step_index": 0,
  "instruction": "Proceed down the aisle and stop beside the red pallet.",
  "observation": {
    "image_bytes": "<Base64-encoded JPEG>",
    "history_image_bytes": [
      "<oldest Base64-encoded JPEG>",
      "<newest Base64-encoded historical JPEG>"
    ],
    "metadata": {
      "camera": "front",
      "captured_at": "2026-07-01T09:15:30.125Z"
    }
  }
}
```

| Field | Type | Requirements |
| --- | --- | --- |
| `api_version` | string | Required. Must be exactly `"1.0"`. |
| `session_id` | string | Required and non-empty. A new navigation episode must use a new value. |
| `step_index` | integer | Required and non-negative. Starts at `0` for each new episode and increases with control steps. |
| `instruction` | string | Required and non-empty. The navigation instruction for the episode. |
| `observation.image_bytes` | string | Required. Base64 encoding of the current JPEG image bytes. A data-URL prefix is not used. |
| `observation.history_image_bytes` | array of strings | Required; may be empty. Each item is a Base64-encoded JPEG. Items are ordered oldest to newest. |
| `observation.metadata` | object | Required; may be empty. Contains optional observation context. |

Each new episode gets a new `session_id` and resets `step_index` to `0`. Clients must not reuse a session ID for an unrelated episode. The service echoes `session_id` and `step_index` in its response so a client can reject stale or mismatched results.

## Successful response

A successful response contains all of these top-level fields:

| Field | Type | Requirements |
| --- | --- | --- |
| `api_version` | string | Always `"1.0"`. |
| `session_id` | string | Equal to the request's `session_id`. |
| `step_index` | integer | Equal to the request's `step_index`. |
| `command_type` | string | Either `"action_chunks"` or `"local_waypoints"`. |
| `chunks` | array | Action chunks, or an empty array for local-waypoint responses. |
| `waypoints` | array | Local waypoints, or an empty array for action-chunk responses. |
| `stop` | boolean | Whether the client must terminate the current navigation episode. |
| `metadata` | object | Contains at least `backend` and `inference_ms`. |

`metadata.backend` is the backend identifier. `metadata.inference_ms` is the non-negative inference duration in milliseconds. Other metadata is optional.

### Action chunks

When `command_type` is `"action_chunks"`, `chunks` contains zero or more action chunks and `waypoints` must be an empty array.

| Field | Type | Requirements |
| --- | --- | --- |
| `index` | integer | Non-negative chunk index. |
| `action` | string | One of `forward`, `turn_left`, `turn_right`, or `stop`. |
| `repeat` | integer | Positive integer number of repetitions. |
| `score` | number or null | Backend confidence, or `null` when the backend does not provide a score. |

The first deployment stage executes only the first action chunk in a response. Its safety layer bounds the resulting motion and follows motion pulses with a zero-velocity command.

An action chunk with `action` equal to `stop` stops the current control step. It does not by itself declare that the navigation task succeeded. The top-level `stop: true` terminates the navigation episode. Zero velocity alone also does not mean task success.

When `stop` is `true`, the client must not execute any command in that same response, even if `chunks` or `waypoints` is non-empty.

See [`examples/response_action.json`](../examples/response_action.json) for a complete response.

### Local waypoints

When `command_type` is `"local_waypoints"`, `waypoints` contains at most 8 local waypoints and `chunks` must be an empty array.

| Field | Type | Requirements |
| --- | --- | --- |
| `x` | number | Forward displacement in metres. Positive is forward. |
| `y` | number | Lateral displacement in metres. Positive is left. |
| `yaw` | number | Heading in radians. Positive is counter-clockwise. |

All waypoints use the vehicle `base_link` frame. Every `x`, `y`, and `yaw` value must be finite; NaN and positive or negative infinity are invalid. Distance values use metres and angles use radians.

See [`examples/response_waypoint.json`](../examples/response_waypoint.json) for a complete response.

## Command consistency

The `command_type` selects exactly one command representation:

- An `action_chunks` response has an empty `waypoints` array.
- A `local_waypoints` response has an empty `chunks` array.

Both arrays remain present so clients can validate a stable response shape. A response that violates these rules is semantically invalid backend output.

## Errors

Every non-success response uses this structure:

```json
{
  "api_version": "1.0",
  "session_id": null,
  "step_index": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "step_index must be a non-negative integer",
    "details": {
      "field": "step_index",
      "value": -1
    }
  }
}
```

`session_id` and `step_index` are nullable because malformed input may not provide usable correlation values. When a valid value can be recovered from the request, the service returns it. `error.code` is a stable machine-readable string, `error.message` is a human-readable summary, and `error.details` is a JSON object with diagnostic context. Clients must branch on `error.code`, not on the message text.

| Error code | Meaning |
| --- | --- |
| `INVALID_JSON` | The request body is not valid JSON. |
| `UNSUPPORTED_API_VERSION` | `api_version` is absent or is not supported by this endpoint. |
| `INVALID_REQUEST` | A required field is missing, has the wrong JSON type, is empty when prohibited, or violates request semantics. |
| `INVALID_BASE64` | An image field is not valid Base64. |
| `INVALID_IMAGE` | Decoded image bytes are not a valid supported JPEG. |
| `IMAGE_TOO_LARGE` | The current image or a history image exceeds the configured image-size limit. |
| `TOO_MANY_HISTORY_IMAGES` | The history array exceeds the configured count limit. |
| `INVALID_ACTION` | Backend output contains an invalid action chunk. |
| `INVALID_WAYPOINT` | Backend output contains an invalid waypoint, inconsistent command arrays, or more than 8 waypoints. |
| `BACKEND_ERROR` | The inference backend failed or is unavailable. |
| `BACKEND_TIMEOUT` | The inference backend exceeded its deadline. |
| `INTERNAL_ERROR` | The service encountered an unexpected internal failure. |

### HTTP status codes

| Status | Use |
| --- | --- |
| `200 OK` | Successful inference response. |
| `400 Bad Request` | Malformed JSON, invalid Base64, or a structurally invalid request. |
| `413 Content Too Large` | The request, an image, or the history image count exceeds a configured limit. |
| `422 Unprocessable Content` | The JSON shape is valid but the request semantics or backend command output is invalid. |
| `500 Internal Server Error` | Internal service failure or non-availability-related backend failure. |
| `503 Service Unavailable` | The inference backend is unavailable. This uses `BACKEND_ERROR`. |
| `504 Gateway Timeout` | The inference backend timed out. This uses `BACKEND_TIMEOUT`. |

For example, `INVALID_REQUEST` can use 400 for a missing or mistyped field and 422 for a correctly typed value that violates a semantic constraint. [`examples/error_response.json`](../examples/error_response.json) demonstrates the latter.

## Compatibility

Optional unknown fields inside request or response `metadata` objects may be ignored. Clients and servers must not assign required behavior to unknown metadata without negotiating it separately.

Breaking semantic changes require a new API version. Additive optional metadata does not require a new version.

The legacy response field `final` is replaced by the explicit top-level `stop` field in API v1. API v1 clients must use `stop` and must not infer episode success from `final`, an `action: "stop"` chunk, or zero velocity.
