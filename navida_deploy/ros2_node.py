from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .control import VelocityCommand, response_to_velocity_commands
from .ros2_bridge import NavidaRos2Gateway


class CommandPublisher(Protocol):
    def publish(self, command: VelocityCommand) -> None:
        raise NotImplementedError


@dataclass
class NavidaRos2Node:
    gateway: NavidaRos2Gateway | Any
    command_publisher: CommandPublisher
    session_id: str
    forward_speed: float = 0.2
    turn_speed: float = 0.8
    step_duration_s: float = 0.5

    def process_frame(self, step_index: int, instruction: str, image_msg: Any) -> None:
        response = self.gateway.infer(
            session_id=self.session_id,
            step_index=step_index,
            instruction=instruction,
            image_msg=image_msg,
        )
        for command in response_to_velocity_commands(
            response,
            forward_speed=self.forward_speed,
            turn_speed=self.turn_speed,
            step_duration_s=self.step_duration_s,
        ):
            self.command_publisher.publish(command)

