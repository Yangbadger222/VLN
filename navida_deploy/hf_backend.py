from __future__ import annotations

from dataclasses import dataclass

from .messages import InferenceRequest, InferenceResponse


@dataclass
class HuggingFaceQwen25VLBackend:
    model_id: str = "waynechu/NaVIDA"
    device: str = "cuda"
    trust_remote_code: bool = False

    def load(self):
        try:
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("transformers is required for the Hugging Face backend") from exc

        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_id,
            torch_dtype="auto",
            device_map=self.device,
            trust_remote_code=self.trust_remote_code,
        )
        processor = AutoProcessor.from_pretrained(
            self.model_id,
            trust_remote_code=self.trust_remote_code,
        )
        return model, processor

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        raise NotImplementedError("Hook model inference here after loading the processor and prompt.")
