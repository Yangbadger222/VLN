from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .messages import ActionChunk, InferenceResponse


@dataclass(frozen=True)
class VelocityCommand:
    action: str
    linear_x: float = 0.0
    angular_z: float = 0.0
    duration_s: float = 0.5
    stop: bool = False


def action_chunk_to_velocity_command(
    chunk: ActionChunk,
    forward_speed: float = 0.2,
    turn_speed: float = 0.8,
    step_duration_s: float = 0.5,
) -> VelocityCommand:
    action = chunk.action.lower()
    if action == "forward":
        return VelocityCommand(action=chunk.action, linear_x=forward_speed, duration_s=step_duration_s)
    if action == "turn_left":
        return VelocityCommand(action=chunk.action, angular_z=turn_speed, duration_s=step_duration_s)
    if action == "turn_right":
        return VelocityCommand(action=chunk.action, angular_z=-turn_speed, duration_s=step_duration_s)
    if action == "stop":
        return VelocityCommand(action=chunk.action, stop=True, duration_s=0.0)
    raise ValueError(f"Unsupported action chunk: {chunk.action}")


def response_to_velocity_commands(
    response: InferenceResponse,
    forward_speed: float = 0.2,
    turn_speed: float = 0.8,
    step_duration_s: float = 0.5,
) -> list[VelocityCommand]:
    commands: list[VelocityCommand] = []
    for chunk in response.chunks:
        command = action_chunk_to_velocity_command(
            chunk,
            forward_speed=forward_speed,
            turn_speed=turn_speed,
            step_duration_s=step_duration_s,
        )
        commands.extend([command] * max(1, chunk.repeat))
    return commands
