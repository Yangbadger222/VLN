from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .control import VelocityCommand


@dataclass(frozen=True)
class Twist2D:
    linear_x: float = 0.0
    angular_z: float = 0.0


def velocity_command_to_twist2d(command: VelocityCommand) -> Twist2D:
    if command.stop:
        return Twist2D()
    return Twist2D(linear_x=command.linear_x, angular_z=command.angular_z)


def velocity_commands_to_twist2d(commands: Iterable[VelocityCommand]) -> list[Twist2D]:
    return [velocity_command_to_twist2d(command) for command in commands]
