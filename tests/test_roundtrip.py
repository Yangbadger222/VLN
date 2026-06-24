from navida_deploy.client import demo_roundtrip


def test_demo_roundtrip_returns_chunked_actions():
    result = demo_roundtrip()

    assert result["session_id"] == "demo-session"
    assert result["chunks"][0]["action"] == "forward"
    assert result["chunks"][0]["repeat"] == 1
    assert result["final"] is True

