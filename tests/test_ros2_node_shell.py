from types import SimpleNamespace

from navida_deploy.control import VelocityCommand
from navida_deploy.ros2_node import NavidaRos2Node


def test_ros2_node_shell_builds_and_publishes_without_rclpy():
    published = []

    class Gateway:
        def infer(self, session_id, step_index, instruction, image_msg):
            return SimpleNamespace(
                session_id=session_id,
                step_index=step_index,
                chunks=[
                    SimpleNamespace(index=0, action="forward", repeat=2),
                    SimpleNamespace(index=1, action="stop", repeat=1),
                ],
            )

    class Publisher:
        def publish(self, command):
            published.append(command)

    node = NavidaRos2Node(
        gateway=Gateway(),
        command_publisher=Publisher(),
        session_id="s1",
    )
    node.process_frame(step_index=3, instruction="go forward", image_msg=SimpleNamespace(data=b"frame"))

    assert len(published) == 3
    assert published[0].action == "forward"
    assert published[-1].stop is True


def test_ros2_node_shell_can_project_commands_to_twist2d():
    class Gateway:
        def infer(self, session_id, step_index, instruction, image_msg):
            return SimpleNamespace(
                session_id=session_id,
                step_index=step_index,
                chunks=[
                    SimpleNamespace(index=0, action="forward", repeat=1),
                    SimpleNamespace(index=1, action="turn_right", repeat=1),
                ],
            )

    node = NavidaRos2Node(
        gateway=Gateway(),
        command_publisher=SimpleNamespace(publish=lambda command: None),
        session_id="s1",
    )

    twists = node.process_frame_as_twist(
        step_index=1,
        instruction="turn right",
        image_msg=SimpleNamespace(data=b"frame"),
    )

    assert twists[0].linear_x > 0
    assert twists[1].angular_z < 0
