from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from .chunking import chunk_atomic_actions
from .messages import ActionChunk, InferenceRequest, InferenceResponse


@dataclass
class HuggingFaceQwen25VLBackend:
    model_id: str = "waynechu/NaVIDA"
    device: str = "cuda"
    input_device: str = "cuda"
    trust_remote_code: bool = False
    max_new_tokens: int = 64
    load_in_4bit: bool = True

    _model: Any | None = None
    _processor: Any | None = None

    def load(self):
        try:
            from transformers import AutoProcessor
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("transformers is required for the Hugging Face backend") from exc
        quantization_config = None
        if self.load_in_4bit:
            try:
                import torch
                from transformers import BitsAndBytesConfig
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "Install torch and bitsandbytes on the 4070 host to enable 4-bit loading."
                ) from exc
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
        try:
            from transformers import Qwen2_5_VLForConditionalGeneration as ModelClass
        except ImportError:  # pragma: no cover
            from transformers import AutoModelForImageTextToText as ModelClass

        model = ModelClass.from_pretrained(
            self.model_id,
            torch_dtype="auto",
            device_map=self.device_map(),
            quantization_config=quantization_config,
            trust_remote_code=self.trust_remote_code,
        )
        processor = AutoProcessor.from_pretrained(
            self.model_id,
            trust_remote_code=self.trust_remote_code,
        )
        return model, processor

    def device_map(self):
        if self.device in {"auto", "balanced", "balanced_low_0", "sequential"}:
            return self.device
        return {"": self.device}

    def _get_model_and_processor(self):
        if self._model is None or self._processor is None:
            self._model, self._processor = self.load()
        return self._model, self._processor

    def infer(self, request: InferenceRequest) -> InferenceResponse:
        model, processor = self._get_model_and_processor()
        image = _observation_to_image(request)
        messages = build_navida_messages(request, image=image)
        text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = processor(
            text=[text],
            images=[image],
            padding=True,
            return_tensors="pt",
        ).to(self.input_device)
        generated_ids = model.generate(**inputs, max_new_tokens=self.max_new_tokens)
        input_ids = inputs.get("input_ids")
        if input_ids is not None:
            generated_ids = [
                output_ids[len(input_ids[index]) :]
                for index, output_ids in enumerate(generated_ids)
            ]
        generated_text = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        return InferenceResponse(
            session_id=request.session_id,
            step_index=request.step_index,
            chunks=parse_action_text(generated_text),
            final=True,
        )


def build_navida_messages(request: InferenceRequest, image: Any | None = None) -> list[dict[str, Any]]:
    instruction = request.instruction or "Navigate safely using the current camera view."
    prompt = (
        "You are controlling a small ground robot. "
        "Choose only from these actions: forward, turn_left, turn_right, stop. "
        "Return JSON exactly like {\"actions\": [\"forward\", \"stop\"]}. "
        f"Navigation instruction: {instruction}"
    )
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image if image is not None else _observation_to_image(request)},
                {"type": "text", "text": prompt},
            ],
        }
    ]


def parse_action_text(text: str) -> list[ActionChunk]:
    actions = _extract_actions_from_json(text) or _extract_actions_from_text(text)
    if not actions:
        actions = ["stop"]
    return chunk_atomic_actions(actions, merge_probability=1.0, rng=lambda: 0.0)


def _extract_actions_from_json(text: str) -> list[str]:
    try:
        payload = json.loads(_slice_json_object(text))
    except (ValueError, TypeError, json.JSONDecodeError):
        return []
    raw_actions = payload.get("actions", [])
    if isinstance(raw_actions, str):
        raw_actions = [raw_actions]
    return [_normalize_action(str(action)) for action in raw_actions if _normalize_action(str(action))]


def _extract_actions_from_text(text: str) -> list[str]:
    lowered = text.lower().replace("-", "_").replace(" ", "_")
    ordered: list[tuple[int, str]] = []
    patterns = {
        "turn_left": ["turn_left", "left"],
        "turn_right": ["turn_right", "right"],
        "forward": ["go_forward", "move_forward", "forward", "straight"],
        "stop": ["stop", "halt"],
    }
    for action, tokens in patterns.items():
        positions = [lowered.find(token) for token in tokens if lowered.find(token) >= 0]
        if positions:
            ordered.append((min(positions), action))
    return [action for _, action in sorted(ordered)]


def _normalize_action(action: str) -> str:
    normalized = action.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "left": "turn_left",
        "right": "turn_right",
        "go": "forward",
        "move_forward": "forward",
        "go_forward": "forward",
        "straight": "forward",
        "halt": "stop",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in {"forward", "turn_left", "turn_right", "stop"}:
        return normalized
    return ""


def _slice_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no json object found")
    return text[start : end + 1]


def _observation_to_image(request: InferenceRequest):
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required to decode image observations") from exc

    observation = request.observation
    if observation.image_bytes:
        try:
            return Image.open(BytesIO(observation.image_bytes)).convert("RGB")
        except Exception:
            return Image.new("RGB", (1, 1), color=(0, 0, 0))
    if observation.image_path:
        return Image.open(observation.image_path).convert("RGB")
    return Image.new("RGB", (1, 1), color=(0, 0, 0))
