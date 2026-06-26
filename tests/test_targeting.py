from navida_deploy.control import VelocityCommand
from navida_deploy.targeting import target_metadata_to_velocity_command


def test_target_metadata_to_velocity_command_turns_toward_right_target():
    command = target_metadata_to_velocity_command(
        {"target": {"visible": True, "center_x": 0.8, "area": 0.1, "confidence": 0.9}},
        forward_speed=0.1,
        turn_gain=0.8,
        max_angular_z=0.25,
        center_deadband=0.1,
        stop_area=0.3,
        min_confidence=0.2,
        duration_s=0.2,
    )

    assert command == VelocityCommand(
        action="visual_servo",
        linear_x=0.0,
        angular_z=-0.24,
        duration_s=0.2,
    )


def test_target_metadata_to_velocity_command_drives_when_centered():
    command = target_metadata_to_velocity_command(
        {"target": {"visible": True, "center_x": 0.54, "area": 0.1, "confidence": 0.9}},
        forward_speed=0.1,
        center_deadband=0.1,
        stop_area=0.3,
    )

    assert command == VelocityCommand(action="visual_servo", linear_x=0.1, duration_s=0.35)


def test_target_metadata_to_velocity_command_stops_when_close_or_not_visible():
    close = target_metadata_to_velocity_command(
        {"target": {"visible": True, "center_x": 0.5, "area": 0.35, "confidence": 0.9}},
        stop_area=0.3,
    )
    missing = target_metadata_to_velocity_command(
        {"target": {"visible": False, "center_x": None, "area": None, "confidence": 0.1}},
        min_confidence=0.2,
    )

    assert close == VelocityCommand(action="visual_stop", duration_s=0.0, stop=True)
    assert missing == VelocityCommand(action="visual_stop", duration_s=0.0, stop=True)
