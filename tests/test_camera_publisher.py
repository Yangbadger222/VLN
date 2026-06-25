from navida_vehicle.camera_publisher import resolve_camera_device


class FakeCapture:
    def __init__(self, opened: bool, readable: bool = True) -> None:
        self._opened = opened
        self._readable = readable
        self.released = False

    def isOpened(self) -> bool:
        return self._opened

    def read(self):
        return self._readable, object() if self._readable else None

    def release(self) -> None:
        self.released = True


def test_resolve_camera_device_picks_first_open_capture():
    seen = []

    def factory(source):
        seen.append(source)
        return FakeCapture(source == "/dev/video4")

    device = resolve_camera_device("auto", factory, candidates=["/dev/video0", "/dev/video4"])

    assert device == "/dev/video4"
    assert seen == ["/dev/video0", "/dev/video4"]


def test_resolve_camera_device_skips_open_capture_without_frame():
    seen = []

    def factory(source):
        seen.append(source)
        if source == "/dev/video0":
            return FakeCapture(opened=True, readable=False)
        return FakeCapture(opened=True, readable=True)

    device = resolve_camera_device("auto", factory, candidates=["/dev/video0", "/dev/video2"])

    assert device == "/dev/video2"
    assert seen == ["/dev/video0", "/dev/video2"]
