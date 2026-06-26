from __future__ import annotations

import time
from functools import partial
from uuid import uuid4

from navida_deploy.control import CommandWatchdog, response_to_velocity_commands, velocity_command_to_pulse
from navida_deploy.http_client import post_inference
from navida_deploy.rclpy_runtime import build_twist_message
from navida_deploy.ros2_bridge import NavidaRos2Gateway
from navida_deploy.targeting import target_metadata_to_velocity_command
from navida_deploy.twist_bridge import Twist2D, velocity_command_to_twist2d


class NavidaRemoteController:
    def __init__(self) -> None:
        import rclpy
        from geometry_msgs.msg import Twist
        from rclpy.node import Node
        from sensor_msgs.msg import Image

        class _Node(Node):
            def __init__(self) -> None:
                super().__init__("navida_remote_controller")
                self.declare_parameter("image_topic", "/navida/camera/image_raw")
                self.declare_parameter("cmd_vel_topic", "/cmd_vel")
                self.declare_parameter("inference_url", "http://REMOTE_INFERENCE_HOST:50051/v1/infer")
                self.declare_parameter("inference_timeout_s", 20.0)
                self.declare_parameter("instruction", "Navigate safely with the front camera.")
                self.declare_parameter("session_id", "")
                self.declare_parameter("forward_speed", 0.15)
                self.declare_parameter("turn_speed", 0.35)
                self.declare_parameter("step_duration_s", 0.35)
                self.declare_parameter("max_linear_x", 0.2)
                self.declare_parameter("max_angular_z", 0.45)
                self.declare_parameter("command_timeout_s", 0.5)
                self.declare_parameter("min_inference_period_s", 0.5)
                self.declare_parameter("visual_servo_enabled", True)
                self.declare_parameter("target_forward_speed", 0.1)
                self.declare_parameter("target_turn_gain", 0.8)
                self.declare_parameter("target_max_angular_z", 0.25)
                self.declare_parameter("target_center_deadband", 0.1)
                self.declare_parameter("target_stop_area", 0.3)
                self.declare_parameter("target_min_confidence", 0.2)

                self._twist_type = Twist
                self._instruction = str(self.get_parameter("instruction").value)
                self._session_id = str(self.get_parameter("session_id").value) or f"jetson-{uuid4().hex[:8]}"
                self._gateway = NavidaRos2Gateway(
                    str(self.get_parameter("inference_url").value),
                    post=partial(post_inference, timeout_s=float(self.get_parameter("inference_timeout_s").value)),
                )
                self._step_index = 0
                self._last_inference_time_s = 0.0
                self._min_inference_period_s = float(self.get_parameter("min_inference_period_s").value)
                self._watchdog = CommandWatchdog(timeout_s=float(self.get_parameter("command_timeout_s").value))

                cmd_vel_topic = str(self.get_parameter("cmd_vel_topic").value)
                image_topic = str(self.get_parameter("image_topic").value)
                self._cmd_pub = self.create_publisher(Twist, cmd_vel_topic, 10)
                self._image_sub = self.create_subscription(Image, image_topic, self._on_image, 10)
                self._watchdog_timer = self.create_timer(0.1, self._on_watchdog_timer)
                self.get_logger().info(
                    f"Subscribing to {image_topic}, publishing {cmd_vel_topic}, inference={self._gateway.infer_url}"
                )

            def _on_image(self, image_msg) -> None:
                now_s = time.monotonic()
                if now_s - self._last_inference_time_s < self._min_inference_period_s:
                    return
                self._last_inference_time_s = now_s

                try:
                    response = self._gateway.infer(
                        session_id=self._session_id,
                        step_index=self._step_index,
                        instruction=self._instruction,
                        image_msg=image_msg,
                    )
                except Exception as exc:
                    self.get_logger().error(f"remote inference failed: {exc}")
                    self._publish_stop()
                    return

                self._step_index += 1
                visual_command = self._visual_servo_command(response)
                if visual_command is not None:
                    self._publish_velocity_pulse(visual_command)
                    return

                commands = response_to_velocity_commands(
                    response,
                    forward_speed=float(self.get_parameter("forward_speed").value),
                    turn_speed=float(self.get_parameter("turn_speed").value),
                    step_duration_s=float(self.get_parameter("step_duration_s").value),
                    max_linear_x=float(self.get_parameter("max_linear_x").value),
                    max_angular_z=float(self.get_parameter("max_angular_z").value),
                )
                if not commands:
                    self._publish_stop()
                    return
                self._publish_velocity_pulse(commands[0])

            def _visual_servo_command(self, response):
                if not bool(self.get_parameter("visual_servo_enabled").value):
                    return None
                return target_metadata_to_velocity_command(
                    response.metadata,
                    forward_speed=float(self.get_parameter("target_forward_speed").value),
                    turn_gain=float(self.get_parameter("target_turn_gain").value),
                    max_angular_z=float(self.get_parameter("target_max_angular_z").value),
                    center_deadband=float(self.get_parameter("target_center_deadband").value),
                    stop_area=float(self.get_parameter("target_stop_area").value),
                    min_confidence=float(self.get_parameter("target_min_confidence").value),
                    duration_s=float(self.get_parameter("step_duration_s").value),
                )

            def _on_watchdog_timer(self) -> None:
                if self._watchdog.expired(time.monotonic()):
                    self.get_logger().warn("command watchdog expired; publishing zero Twist")
                    self._publish_stop()

            def _publish_stop(self) -> None:
                self._publish_twist(Twist2D())

            def _publish_velocity_pulse(self, command) -> None:
                pulse = velocity_command_to_pulse(command)
                for index, pulse_command in enumerate(pulse):
                    self._publish_twist(velocity_command_to_twist2d(pulse_command))
                    if index < len(pulse) - 1 and pulse_command.duration_s > 0:
                        time.sleep(float(pulse_command.duration_s))

            def _publish_twist(self, twist: Twist2D) -> None:
                self._cmd_pub.publish(build_twist_message(twist, twist_type=self._twist_type))
                self._watchdog.record_command(time.monotonic())

        self.rclpy = rclpy
        self.node = _Node()


def main() -> None:
    import rclpy

    rclpy.init()
    app = NavidaRemoteController()
    try:
        rclpy.spin(app.node)
    finally:
        app.node.destroy_node()
        rclpy.shutdown()
