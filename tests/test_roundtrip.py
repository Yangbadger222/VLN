from navida_deploy.client import demo_roundtrip


def test_demo_roundtrip_returns_api_v1_chunked_actions():
    result = demo_roundtrip()

    assert result["api_version"] == "1.0"
    assert result["session_id"] == "demo-session"
    assert result["command_type"] == "action_chunks"
    assert result["chunks"][0]["action"] == "forward"
    assert result["chunks"][0]["repeat"] == 1
    assert result["waypoints"] == []
    assert result["stop"] is False
    assert "final" not in result
