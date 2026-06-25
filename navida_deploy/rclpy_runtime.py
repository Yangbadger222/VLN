from __future__ import annotations

from typing import Any

from .twist_bridge import Twist2D


def fill_twist_message(message: Any, twist: Twist2D) -> Any:
    if not hasattr(message, "linear"):
        message.linear = type("Vector3", (), {})()
    if not hasattr(message, "angular"):
        message.angular = type("Vector3", (), {})()

    message.linear.x = twist.linear_x
    message.linear.y = 0.0
    message.linear.z = 0.0
    message.angular.x = 0.0
    message.angular.y = 0.0
    message.angular.z = twist.angular_z
    return message


def build_twist_message(twist: Twist2D, twist_type: Any | None = None) -> Any:
    if twist_type is None:
        twist_type = _try_import_twist()
    message = twist_type()
    return fill_twist_message(message, twist)


def _try_import_twist() -> Any:
    try:
        from geometry_msgs.msg import Twist
    except Exception as exc:  # pragma: no cover - import depends on ROS2 runtime
        raise RuntimeError("geometry_msgs is required to build Twist messages") from exc
    return Twist
