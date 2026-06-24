import pytest

from navida_deploy.control import (
    VelocityCommand,
    action_chunk_to_velocity_command,
    response_to_velocity_commands,
)
from navida_deploy.messages import ActionChunk, InferenceResponse


def test_action_chunk_to_velocity_command_maps_cardinal_actions():
    forward = action_chunk_to_velocity_command(
        ActionChunk(index=0, action="forward", repeat=2),
        forward_speed=0.3,
        turn_speed=0.8,
        step_duration_s=0.5,
    )
    turn_left = action_chunk_to_velocity_command(ActionChunk(index=1, action="turn_left"))
    turn_right = action_chunk_to_velocity_command(ActionChunk(index=2, action="turn_right"))
    stop = action_chunk_to_velocity_command(ActionChunk(index=3, action="stop"))

    assert forward == VelocityCommand(action="forward", linear_x=0.3, angular_z=0.0, duration_s=0.5)
    assert turn_left == VelocityCommand(action="turn_left", linear_x=0.0, angular_z=0.8, duration_s=0.5)
    assert turn_right == VelocityCommand(action="turn_right", linear_x=0.0, angular_z=-0.8, duration_s=0.5)
    assert stop.stop is True


def test_response_to_velocity_commands_expands_chunk_repeats():
    response = InferenceResponse(
        session_id="s1",
        step_index=4,
        chunks=[
            ActionChunk(index=0, action="forward", repeat=2),
            ActionChunk(index=1, action="turn_left", repeat=1),
        ],
    )

    commands = response_to_velocity_commands(response, forward_speed=0.2, turn_speed=0.6, step_duration_s=1.0)

    assert len(commands) == 3
    assert commands[0].action == "forward"
    assert commands[1].action == "forward"
    assert commands[2].action == "turn_left"


def test_action_chunk_to_velocity_command_rejects_unknown_actions():
    with pytest.raises(ValueError):
        action_chunk_to_velocity_command(ActionChunk(index=0, action="spin"))

