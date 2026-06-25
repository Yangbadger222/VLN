from types import SimpleNamespace

from navida_deploy.rclpy_runtime import fill_twist_message
from navida_deploy.twist_bridge import Twist2D


def test_fill_twist_message_sets_cmd_vel_axes_only():
    msg = SimpleNamespace(
        linear=SimpleNamespace(x=9.0, y=8.0, z=7.0),
        angular=SimpleNamespace(x=6.0, y=5.0, z=4.0),
    )

    fill_twist_message(msg, Twist2D(linear_x=0.25, angular_z=-0.6))

    assert msg.linear.x == 0.25
    assert msg.linear.y == 0.0
    assert msg.linear.z == 0.0
    assert msg.angular.x == 0.0
    assert msg.angular.y == 0.0
    assert msg.angular.z == -0.6
