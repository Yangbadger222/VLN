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


@dataclass
class CommandWatchdog:
    timeout_s: float
    last_command_time_s: float | None = None

    def record_command(self, now_s: float) -> None:
        self.last_command_time_s = now_s

    def expired(self, now_s: float) -> bool:
        return self.last_command_time_s is not None and (now_s - self.last_command_time_s) > self.timeout_s


def clamp_velocity_command(
    command: VelocityCommand,
    max_linear_x: float = 0.3,
    max_angular_z: float = 1.0,
) -> VelocityCommand:
    if command.stop:
        return VelocityCommand(action=command.action, duration_s=0.0, stop=True)

    linear_x = max(-max_linear_x, min(max_linear_x, command.linear_x))
    angular_z = max(-max_angular_z, min(max_angular_z, command.angular_z))
    return VelocityCommand(
        action=command.action,
        linear_x=linear_x,
        angular_z=angular_z,
        duration_s=command.duration_s,
        stop=command.stop,
    )


def velocity_command_to_pulse(command: VelocityCommand) -> list[VelocityCommand]:
    if command.stop:
        return [command]
    return [
        command,
        VelocityCommand(action="stop", duration_s=0.0, stop=True),
    ]


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
    max_linear_x: float | None = 0.3,
    max_angular_z: float | None = 1.0,
) -> list[VelocityCommand]:
    commands: list[VelocityCommand] = []
    for chunk in response.chunks:
        command = action_chunk_to_velocity_command(
            chunk,
            forward_speed=forward_speed,
            turn_speed=turn_speed,
            step_duration_s=step_duration_s,
        )
        if max_linear_x is not None or max_angular_z is not None:
            command = clamp_velocity_command(
                command,
                max_linear_x=max_linear_x if max_linear_x is not None else abs(command.linear_x),
                max_angular_z=max_angular_z if max_angular_z is not None else abs(command.angular_z),
            )
        commands.extend([command] * max(1, chunk.repeat))
    return commands
