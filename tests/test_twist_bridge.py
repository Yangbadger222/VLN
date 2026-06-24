from navida_deploy.control import VelocityCommand
from navida_deploy.twist_bridge import Twist2D, velocity_command_to_twist2d, velocity_commands_to_twist2d


def test_velocity_command_to_twist2d_maps_cmd_vel_subset():
    forward = velocity_command_to_twist2d(
        VelocityCommand(action="forward", linear_x=0.3, angular_z=0.0, duration_s=0.5)
    )
    turn_left = velocity_command_to_twist2d(
        VelocityCommand(action="turn_left", linear_x=0.0, angular_z=0.8, duration_s=0.5)
    )
    stop = velocity_command_to_twist2d(VelocityCommand(action="stop", stop=True))

    assert forward == Twist2D(linear_x=0.3, angular_z=0.0)
    assert turn_left == Twist2D(linear_x=0.0, angular_z=0.8)
    assert stop == Twist2D()


def test_velocity_commands_to_twist2d_preserves_sequence_order():
    twists = velocity_commands_to_twist2d(
        [
            VelocityCommand(action="forward", linear_x=0.2),
            VelocityCommand(action="turn_right", angular_z=-0.6),
            VelocityCommand(action="stop", stop=True),
        ]
    )

    assert twists == [
        Twist2D(linear_x=0.2, angular_z=0.0),
        Twist2D(linear_x=0.0, angular_z=-0.6),
        Twist2D(),
    ]
