from __future__ import annotations

from typing import Any

from .control import VelocityCommand


def target_metadata_to_velocity_command(
    metadata: dict[str, Any],
    forward_speed: float = 0.1,
    turn_gain: float = 0.8,
    max_angular_z: float = 0.25,
    center_deadband: float = 0.1,
    stop_area: float = 0.3,
    min_confidence: float = 0.2,
    duration_s: float = 0.35,
) -> VelocityCommand | None:
    target = metadata.get("target")
    if not isinstance(target, dict):
        return None

    visible = bool(target.get("visible"))
    confidence = _float_or_none(target.get("confidence"))
    center_x = _float_or_none(target.get("center_x"))
    area = _float_or_none(target.get("area"))

    if not visible or center_x is None or (confidence is not None and confidence < min_confidence):
        return _visual_stop()
    if area is not None and area >= stop_area:
        return _visual_stop()

    center_x = max(0.0, min(1.0, center_x))
    error = center_x - 0.5
    if abs(error) <= center_deadband:
        return VelocityCommand(action="visual_servo", linear_x=forward_speed, duration_s=duration_s)

    angular_z = -max(-max_angular_z, min(max_angular_z, turn_gain * error))
    return VelocityCommand(action="visual_servo", angular_z=round(angular_z, 6), duration_s=duration_s)


def _visual_stop() -> VelocityCommand:
    return VelocityCommand(action="visual_stop", duration_s=0.0, stop=True)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
