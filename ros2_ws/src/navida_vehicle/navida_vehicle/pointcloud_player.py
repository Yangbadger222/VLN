from __future__ import annotations

import csv
import math
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header


class PointCloudPlayer(Node):
    def __init__(self) -> None:
        super().__init__("pointcloud_player")
        self.declare_parameter("csv_path", "")
        self.declare_parameter("frame_id", "map")
        self.declare_parameter("topic", "/navida/pointcloud")
        self.declare_parameter("publish_rate_hz", 1.0)
        self.declare_parameter("sample_limit", 300000)
        self.declare_parameter("drop_zero_points", True)
        self.declare_parameter("z_offset", 0.0)

        self.csv_path = Path(self.get_parameter("csv_path").value).expanduser()
        self.frame_id = self.get_parameter("frame_id").value
        self.topic = self.get_parameter("topic").value
        self.sample_limit = int(self.get_parameter("sample_limit").value)
        self.drop_zero_points = bool(self.get_parameter("drop_zero_points").value)
        self.z_offset = float(self.get_parameter("z_offset").value)

        rate = float(self.get_parameter("publish_rate_hz").value)
        self.publisher = self.create_publisher(PointCloud2, self.topic, 1)
        self.points = self._load_points()
        if not self.points:
            raise RuntimeError(f"No usable points loaded from {self.csv_path}")

        self.fields = [
            PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name="intensity", offset=12, datatype=PointField.FLOAT32, count=1),
        ]
        self.cloud = point_cloud2.create_cloud(
            Header(frame_id=self.frame_id),
            self.fields,
            self.points,
        )
        self.timer = self.create_timer(1.0 / max(rate, 0.1), self._publish_once)
        self.get_logger().info(
            f"Loaded {len(self.points):,} points from {self.csv_path} -> {self.topic}"
        )

    def _load_points(self):
        points = []
        with self.csv_path.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    x = float(row["x"])
                    y = float(row["y"])
                    z = float(row["z"]) + self.z_offset
                    intensity = float(row.get("reflectivity", 0.0))
                except Exception:
                    continue
                if any(math.isnan(v) or math.isinf(v) for v in (x, y, z, intensity)):
                    continue
                if self.drop_zero_points and x == 0.0 and y == 0.0 and z == self.z_offset:
                    continue
                points.append((x, y, z, intensity))
                if len(points) >= self.sample_limit:
                    break
        return points

    def _publish_once(self) -> None:
        self.cloud.header.stamp = self.get_clock().now().to_msg()
        self.publisher.publish(self.cloud)


def main() -> None:
    rclpy.init()
    node = None
    try:
        node = PointCloudPlayer()
        rclpy.spin(node)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
