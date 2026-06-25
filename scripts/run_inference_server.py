from __future__ import annotations

import argparse

from navida_deploy.backend import InferenceBackend, MockNaVIDABackend
from navida_deploy.hf_backend import HuggingFaceQwen25VLBackend
from navida_deploy.http_service import create_server


def build_backend(kind: str, model_id: str = "waynechu/NaVIDA", device: str = "cuda") -> InferenceBackend:
    if kind == "mock":
        return MockNaVIDABackend()
    if kind == "hf":
        return HuggingFaceQwen25VLBackend(model_id=model_id, device=device, input_device=device)
    raise ValueError(f"Unsupported backend kind: {kind}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the NaVIDA remote inference HTTP service.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument("--backend", choices=("mock", "hf"), default="mock")
    parser.add_argument("--model-id", default="waynechu/NaVIDA")
    parser.add_argument("--device", default="cuda")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    backend = build_backend(args.backend, model_id=args.model_id, device=args.device)
    server = create_server((args.host, args.port), backend=backend)
    print(f"listening on http://{args.host}:{args.port}/v1/infer with backend={args.backend}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
