from __future__ import annotations

from types import SimpleNamespace

from navida_deploy.http_client import post_inference
from navida_deploy.ros2_bridge import NavidaRos2Gateway
from navida_deploy.ros2_node import NavidaRos2Node


class PrintPublisher:
    def publish(self, command):
        print(command)


if __name__ == "__main__":
    gateway = NavidaRos2Gateway("http://127.0.0.1:50051/v1/infer", post=post_inference)
    node = NavidaRos2Node(gateway=gateway, command_publisher=PrintPublisher(), session_id="demo")
    node.process_frame(
        step_index=0,
        instruction="go forward then turn left",
        image_msg=SimpleNamespace(data=b"demo", height=1, width=1, encoding="mono8", step=1),
    )

