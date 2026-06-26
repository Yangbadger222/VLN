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
    target_detector_model_id: str | None = None
    target_detector_threshold: float = 0.1

    _model: Any | None = None
    _processor: Any | None = None
    _target_detector: Any | None = None

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

    def load_target_detector(self):
        if not self.target_detector_model_id:
            return None
        try:
            from transformers import pipeline
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("transformers is required for the target detector") from exc
        device = 0 if self.input_device == "cuda" else -1
        return pipeline(
            task="zero-shot-object-detection",
            model=self.target_detector_model_id,
            device=device,
        )

    def device_map(self):
        if self.device in {"auto", "balanced", "balanced_low_0", "sequential"}:
            return self.device
        return {"": self.device}

    def _get_model_and_processor(self):
        if self._model is None or self._processor is None:
            self._model, self._processor = self.load()
        return self._model, self._processor

    def _get_target_detector(self):
        if self.target_detector_model_id and self._target_detector is None:
            self._target_detector = self.load_target_detector()
        return self._target_detector

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
        metadata = parse_target_metadata(generated_text)
        if not metadata:
            metadata = self.detect_target(request, image)
        return InferenceResponse(
            session_id=request.session_id,
            step_index=request.step_index,
            chunks=parse_action_text(generated_text),
            final=True,
            metadata=metadata,
        )

    def detect_target(self, request: InferenceRequest, image: Any) -> dict[str, Any]:
        detector = self._get_target_detector()
        if detector is None:
            return {}
        label = target_label_from_request(request)
        if not label:
            return {}
        detections = detector(
            image,
            candidate_labels=target_candidate_labels(label),
            threshold=self.target_detector_threshold,
        )
        return detection_to_target_metadata(
            detections,
            image_width=image.width,
            image_height=image.height,
        )


def build_navida_messages(request: InferenceRequest, image: Any | None = None) -> list[dict[str, Any]]:
    instruction = request.instruction or "Navigate safely using the current camera view."
    prompt = (
        "You are controlling a small ground robot. "
        "Find the navigation target described by the instruction in the image. "
        "Return JSON exactly like "
        "{\"target\":{\"visible\":true,\"center_x\":0.50,\"area\":0.10,\"confidence\":0.80},"
        "\"actions\":[\"forward\"]}. "
        "Use center_x from 0.0 left to 1.0 right. Use area as the target bounding box area "
        "divided by image area. If the target is not visible, set visible false and actions [\"stop\"]. "
        "Choose actions only from: forward, turn_left, turn_right, stop. "
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


def parse_target_metadata(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(_slice_json_object(text))
    except (ValueError, TypeError, json.JSONDecodeError):
        return {}
    target = payload.get("target")
    if not isinstance(target, dict):
        return {}
    return {
        "target": {
            "visible": bool(target.get("visible")),
            "center_x": _number_or_none(target.get("center_x")),
            "area": _number_or_none(target.get("area")),
            "confidence": _number_or_none(target.get("confidence")),
        }
    }


def detection_to_target_metadata(
    detections: list[dict[str, Any]],
    image_width: int,
    image_height: int,
) -> dict[str, Any]:
    if image_width <= 0 or image_height <= 0:
        return {}
    valid = [detection for detection in detections if isinstance(detection, dict)]
    if not valid:
        return {"target": {"visible": False, "center_x": None, "area": None, "confidence": 0.0}}
    best = max(
        valid,
        key=lambda detection: _detection_selection_score(detection, image_width, image_height),
    )
    box = best.get("box") or {}
    try:
        xmin = float(box["xmin"])
        ymin = float(box["ymin"])
        xmax = float(box["xmax"])
        ymax = float(box["ymax"])
    except (KeyError, TypeError, ValueError):
        return {"target": {"visible": False, "center_x": None, "area": None, "confidence": 0.0}}
    center_x = ((xmin + xmax) / 2.0) / image_width
    area = max(0.0, xmax - xmin) * max(0.0, ymax - ymin) / float(image_width * image_height)
    return {
        "target": {
            "visible": True,
            "center_x": round(max(0.0, min(1.0, center_x)), 6),
            "area": round(max(0.0, min(1.0, area)), 6),
            "confidence": round(float(best.get("score") or 0.0), 6),
        }
    }


def _detection_selection_score(detection: dict[str, Any], image_width: int, image_height: int) -> float:
    box = detection.get("box") or {}
    try:
        xmin = float(box["xmin"])
        ymin = float(box["ymin"])
        xmax = float(box["xmax"])
        ymax = float(box["ymax"])
    except (KeyError, TypeError, ValueError):
        return -1.0
    score = float(detection.get("score") or 0.0)
    center_x = ((xmin + xmax) / 2.0) / max(1.0, float(image_width))
    area = max(0.0, xmax - xmin) * max(0.0, ymax - ymin) / max(1.0, float(image_width * image_height))
    centered_bonus = 1.0 - min(1.0, abs(center_x - 0.5) * 2.0)
    return score + area + 0.15 * centered_bonus


def target_label_from_request(request: InferenceRequest) -> str:
    metadata = request.observation.metadata or {}
    label = str(metadata.get("target_label") or "").strip()
    if label:
        return label
    instruction = request.instruction.strip()
    prefixes = [
        "go to the ",
        "go to ",
        "approach the ",
        "approach ",
        "move to the ",
        "move to ",
    ]
    lowered = instruction.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return instruction[len(prefix) :].split(".")[0].strip()
    return instruction


def target_candidate_labels(label: str) -> list[str]:
    normalized = " ".join(label.strip().split())
    if not normalized:
        return []
    lowered = normalized.lower()
    candidates = [normalized]
    if not lowered.startswith(("a ", "an ", "the ")):
        candidates.extend([f"a {normalized}", f"the {normalized}"])
    return list(dict.fromkeys(candidates))


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


def _number_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
