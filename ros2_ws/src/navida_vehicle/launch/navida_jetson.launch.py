from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _arg(name: str, default: str, description: str) -> DeclareLaunchArgument:
    return DeclareLaunchArgument(name, default_value=default, description=description)


def generate_launch_description() -> LaunchDescription:
    inference_url = LaunchConfiguration("inference_url")
    instruction = LaunchConfiguration("instruction")
    image_topic = LaunchConfiguration("image_topic")
    cmd_vel_topic = LaunchConfiguration("cmd_vel_topic")
    camera_device = LaunchConfiguration("camera_device")
    camera_width = LaunchConfiguration("camera_width")
    camera_height = LaunchConfiguration("camera_height")
    camera_fps = LaunchConfiguration("camera_fps")
    serial_port = LaunchConfiguration("serial_port")
    baudrate = LaunchConfiguration("baudrate")
    angular_z_scale = LaunchConfiguration("angular_z_scale")
    forward_speed = LaunchConfiguration("forward_speed")
    turn_speed = LaunchConfiguration("turn_speed")
    max_linear_x = LaunchConfiguration("max_linear_x")
    max_angular_z = LaunchConfiguration("max_angular_z")
    command_timeout_s = LaunchConfiguration("command_timeout_s")
    inference_timeout_s = LaunchConfiguration("inference_timeout_s")

    return LaunchDescription(
        [
            _arg("inference_url", "http://REMOTE_INFERENCE_HOST:50051/v1/infer", "4070 inference endpoint"),
            _arg("instruction", "Navigate safely with the front camera.", "Navigation instruction"),
            _arg("image_topic", "/navida/camera/image_raw", "Camera image topic"),
            _arg("cmd_vel_topic", "/cmd_vel", "Chassis velocity topic"),
            _arg("camera_device", "auto", "USB camera device or auto to probe /dev/video*"),
            _arg("camera_width", "640", "Camera width"),
            _arg("camera_height", "480", "Camera height"),
            _arg("camera_fps", "10.0", "Camera frames per second"),
            _arg("serial_port", "/dev/serial_twistctl", "STM32 chassis serial device"),
            _arg("baudrate", "115200", "STM32 chassis serial baudrate"),
            _arg("angular_z_scale", "1.0", "Set to -1.0 if chassis turn direction is reversed"),
            _arg("forward_speed", "0.15", "Forward speed in m/s"),
            _arg("turn_speed", "0.35", "Turn speed in rad/s"),
            _arg("max_linear_x", "0.2", "Linear speed clamp in m/s"),
            _arg("max_angular_z", "0.45", "Angular speed clamp in rad/s"),
            _arg("command_timeout_s", "0.5", "Publish zero Twist after this many seconds without command"),
            _arg("inference_timeout_s", "20.0", "HTTP timeout for one remote inference request"),
            Node(
                package="serial_twistctl",
                executable="serial_twistctl_node",
                name="serial_twistctl_node",
                output="screen",
                parameters=[
                    {
                        "port": serial_port,
                        "baudrate": ParameterValue(baudrate, value_type=int),
                        "send_attempts": 1,
                        "delay_between_attempts_ms": 0,
                        "angular_z_scale": ParameterValue(angular_z_scale, value_type=float),
                    }
                ],
            ),
            Node(
                package="navida_vehicle",
                executable="camera_publisher",
                name="navida_camera_publisher",
                output="screen",
                parameters=[
                    {
                        "camera_device": camera_device,
                        "image_topic": image_topic,
                        "width": ParameterValue(camera_width, value_type=int),
                        "height": ParameterValue(camera_height, value_type=int),
                        "fps": ParameterValue(camera_fps, value_type=float),
                    }
                ],
            ),
            Node(
                package="navida_vehicle",
                executable="remote_controller",
                name="navida_remote_controller",
                output="screen",
                parameters=[
                    {
                        "image_topic": image_topic,
                        "cmd_vel_topic": cmd_vel_topic,
                        "inference_url": inference_url,
                        "instruction": instruction,
                        "inference_timeout_s": ParameterValue(inference_timeout_s, value_type=float),
                        "forward_speed": ParameterValue(forward_speed, value_type=float),
                        "turn_speed": ParameterValue(turn_speed, value_type=float),
                        "max_linear_x": ParameterValue(max_linear_x, value_type=float),
                        "max_angular_z": ParameterValue(max_angular_z, value_type=float),
                        "command_timeout_s": ParameterValue(command_timeout_s, value_type=float),
                    }
                ],
            ),
        ]
    )
