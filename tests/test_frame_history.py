from navida_deploy.frame_history import FrameHistory


def test_frame_history_returns_prior_frames_before_appending_current():
    history = FrameHistory(max_frames=2)

    assert history.snapshot() == []

    history.append(b"frame-1")
    history.append(b"frame-2")

    assert history.snapshot() == [b"frame-1", b"frame-2"]

    history.append(b"frame-3")

    assert history.snapshot() == [b"frame-2", b"frame-3"]


def test_frame_history_ignores_empty_frames_and_disabled_history():
    history = FrameHistory(max_frames=0)

    history.append(b"frame-1")

    assert history.snapshot() == []
