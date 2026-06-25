from __future__ import annotations


DEFAULT_CAMERA_CANDIDATES = tuple(f"/dev/video{index}" for index in range(6))


def _normalize_camera_device(raw):
    if isinstance(raw, str):
        value = raw.strip()
        if value.isdigit():
            return int(value)
        return value
    return raw


def resolve_camera_device(camera_device, capture_factory, candidates=DEFAULT_CAMERA_CANDIDATES):
    normalized = _normalize_camera_device(camera_device)
    if normalized != "auto":
        return normalized

    for candidate in candidates:
        capture = capture_factory(candidate)
        try:
            if capture is None or not capture.isOpened():
                continue
            ok, frame = capture.read()
            if ok and frame is not None:
                return candidate
        finally:
            if capture is not None and hasattr(capture, "release"):
                capture.release()

    raise RuntimeError(
        "Could not find a readable camera device. Checked: "
        + ", ".join(str(candidate) for candidate in candidates)
    )


class UsbCameraPublisher:
    def __init__(self) -> None:
        import cv2
        import rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import Image

        class _Node(Node):
            def __init__(self) -> None:
                super().__init__("navida_camera_publisher")
                self.declare_parameter("camera_device", "auto")
                self.declare_parameter("image_topic", "/navida/camera/image_raw")
                self.declare_parameter("frame_id", "navida_camera")
                self.declare_parameter("width", 640)
                self.declare_parameter("height", 480)
                self.declare_parameter("fps", 10.0)

                self._image_type = Image
                self._frame_id = str(self.get_parameter("frame_id").value)
                topic = str(self.get_parameter("image_topic").value)
                fps = float(self.get_parameter("fps").value)
                device = resolve_camera_device(self.get_parameter("camera_device").value, cv2.VideoCapture)

                self._capture = cv2.VideoCapture(device)
                self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.get_parameter("width").value))
                self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.get_parameter("height").value))
                self._capture.set(cv2.CAP_PROP_FPS, fps)
                if not self._capture.isOpened():
                    raise RuntimeError(f"Failed to open camera device: {device}")
                self._publisher = self.create_publisher(Image, topic, 10)
                self._timer = self.create_timer(1.0 / max(1.0, fps), self._publish_frame)
                self.get_logger().info(f"Publishing camera frames from {device} to {topic}")

            def _publish_frame(self) -> None:
                ok, frame = self._capture.read()
                if not ok:
                    self.get_logger().warn("camera frame read failed")
                    return

                height, width = frame.shape[:2]
                message = self._image_type()
                message.header.stamp = self.get_clock().now().to_msg()
                message.header.frame_id = self._frame_id
                message.height = int(height)
                message.width = int(width)
                message.encoding = "bgr8"
                message.is_bigendian = 0
                message.step = int(width * 3)
                message.data = frame.tobytes()
                self._publisher.publish(message)

            def destroy_node(self) -> bool:
                if self._capture is not None:
                    self._capture.release()
                return super().destroy_node()

        self.rclpy = rclpy
        self.node = _Node()


def main() -> None:
    import rclpy

    rclpy.init()
    app = UsbCameraPublisher()
    try:
        rclpy.spin(app.node)
    finally:
        app.node.destroy_node()
        rclpy.shutdown()
