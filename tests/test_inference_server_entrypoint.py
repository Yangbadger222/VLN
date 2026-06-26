from navida_deploy.backend import MockNaVIDABackend
from scripts.run_inference_server import build_backend


def test_build_backend_returns_mock_backend_by_default():
    backend = build_backend("mock")

    assert isinstance(backend, MockNaVIDABackend)


def test_build_backend_enables_4bit_loading_for_hf_backend():
    backend = build_backend("hf")

    assert backend.load_in_4bit is True


def test_build_backend_enables_target_detector_fallback_only_when_requested():
    default_backend = build_backend("hf")
    fallback_backend = build_backend("hf", target_detector_fallback=True)

    assert default_backend.target_detector_fallback is False
    assert fallback_backend.target_detector_fallback is True
