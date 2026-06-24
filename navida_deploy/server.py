from __future__ import annotations

from typing import Iterable

from .backend import InferenceBackend, MockNaVIDABackend
from .messages import ActionChunk, InferenceRequest, InferenceResponse

_DEFAULT_BACKEND = MockNaVIDABackend()


def run_mock_inference(request: InferenceRequest) -> InferenceResponse:
    return _DEFAULT_BACKEND.infer(request)


def infer_with_backend(request: InferenceRequest, backend: InferenceBackend) -> InferenceResponse:
    return backend.infer(request)


def stream_mock_chunks(response: InferenceResponse) -> Iterable[ActionChunk]:
    yield from response.chunks
