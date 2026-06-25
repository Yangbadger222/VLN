from navida_deploy.backend import MockNaVIDABackend
from scripts.run_inference_server import build_backend


def test_build_backend_returns_mock_backend_by_default():
    backend = build_backend("mock")

    assert isinstance(backend, MockNaVIDABackend)
