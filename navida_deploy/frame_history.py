from __future__ import annotations

from collections import deque


class FrameHistory:
    def __init__(self, max_frames: int) -> None:
        self._frames: deque[bytes] = deque(maxlen=max(0, int(max_frames)))

    def append(self, frame: bytes | None) -> None:
        if self._frames.maxlen == 0 or not frame:
            return
        self._frames.append(bytes(frame))

    def snapshot(self) -> list[bytes]:
        return list(self._frames)
