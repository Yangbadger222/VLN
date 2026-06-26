from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _arg(name: str, default: str, description: str) -> DeclareLaunchArgument:
    return DeclareLaunchArgument(name, default_value=default, description=description)


def generate_launch_description() -> LaunchDescription:
    csv_path = LaunchConfiguration("csv_path")
    frame_id = LaunchConfiguration("frame_id")
    topic = LaunchConfiguration("topic")
    publish_rate_hz = LaunchConfiguration("publish_rate_hz")
    sample_limit = LaunchConfiguration("sample_limit")
    drop_zero_points = LaunchConfiguration("drop_zero_points")
    z_offset = LaunchConfiguration("z_offset")

    return LaunchDescription(
        [
            _arg("csv_path", "", "Path to livox_pointcloud.log CSV"),
            _arg("frame_id", "map", "Frame id shown in RViz"),
            _arg("topic", "/navida/pointcloud", "PointCloud2 topic"),
            _arg("publish_rate_hz", "1.0", "Republish rate"),
            _arg("sample_limit", "300000", "Maximum points to load from CSV"),
            _arg("drop_zero_points", "true", "Drop 0,0,0 placeholder points"),
            _arg("z_offset", "0.0", "Meters to add to each z coordinate"),
            Node(
                package="navida_vehicle",
                executable="pointcloud_player",
                name="pointcloud_player",
                output="screen",
                parameters=[
                    {
                        "csv_path": csv_path,
                        "frame_id": frame_id,
                        "topic": topic,
                        "publish_rate_hz": ParameterValue(publish_rate_hz, value_type=float),
                        "sample_limit": ParameterValue(sample_limit, value_type=int),
                        "drop_zero_points": ParameterValue(drop_zero_points, value_type=bool),
                        "z_offset": ParameterValue(z_offset, value_type=float),
                    }
                ],
            ),
        ]
    )
