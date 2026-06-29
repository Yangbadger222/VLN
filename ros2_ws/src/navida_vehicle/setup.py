from setuptools import setup


package_name = "navida_vehicle"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", ["config/navida_jetson.yaml"]),
        (
            f"share/{package_name}/launch",
            ["launch/navida_jetson.launch.py", "launch/pointcloud_player.launch.py"],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="VLN Team",
    maintainer_email="maintainer@example.com",
    description="Jetson-side ROS 2 camera and remote NaVIDA control nodes.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "camera_publisher = navida_vehicle.camera_publisher:main",
            "csv_to_pcd = navida_vehicle.csv_to_pcd:main",
            "pointcloud_player = navida_vehicle.pointcloud_player:main",
            "remote_controller = navida_vehicle.remote_controller:main",
        ],
    },
)
