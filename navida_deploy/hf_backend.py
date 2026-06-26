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
    target_detector_fallback: bool = False

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
        images = _observation_to_images(request)
        image = images[-1]
        messages = build_navida_messages(request, images=images)
        text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = processor(
            text=[text],
            images=images,
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
        if not metadata and self.target_detector_fallback:
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


def build_navida_messages(
    request: InferenceRequest,
    images: list[Any] | None = None,
    image: Any | None = None,
) -> list[dict[str, Any]]:
    instruction = request.instruction or "Navigate safely using the current camera view."
    observation_images = images or ([image] if image is not None else _observation_to_images(request))
    prompt = (
        "You are controlling a small ground robot. "
        "Use the historical observations followed by the current observation to decide the next move. "
        "Return compact JSON exactly like "
        "{\"actions\":[{\"action\":\"forward\",\"repeat\":1}]}. "
        "Use action chunks only from: forward, turn_left, turn_right, stop. "
        "Use repeat for short repeated chunks when needed. "
        f"Navigation instruction: {instruction}"
    )
    content = [{"type": "image", "image": item} for item in observation_images]
    content.append({"type": "text", "text": prompt})
    return [
        {
            "role": "user",
            "content": content,
        }
    ]


def parse_action_text(text: str) -> list[ActionChunk]:
    chunks = _extract_action_chunks_from_json(text)
    if chunks:
        return chunks
    actions = _extract_actions_from_text(text)
    if not actions:
        return chunk_atomic_actions(["stop"], merge_probability=1.0, rng=lambda: 0.0)
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


def _extract_action_chunks_from_json(text: str) -> list[ActionChunk]:
    try:
        payload = json.loads(_slice_json_object(text))
    except (ValueError, TypeError, json.JSONDecodeError):
        return []
    raw_actions = payload.get("actions", [])
    if isinstance(raw_actions, (str, dict)):
        raw_actions = [raw_actions]
    chunks: list[ActionChunk] = []
    for raw in raw_actions:
        score = None
        repeat = 1
        if isinstance(raw, dict):
            action = _normalize_action(str(raw.get("action") or raw.get("name") or ""))
            repeat = _positive_int(raw.get("repeat"), default=1)
            score = _number_or_none(raw.get("score"))
        else:
            action = _normalize_action(str(raw))
        if action:
            chunks.append(ActionChunk(index=len(chunks), action=action, repeat=repeat, score=score))
    return chunks


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


def _positive_int(value: Any, default: int = 1) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


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


def _observation_to_images(request: InferenceRequest):
    images = [_decode_observation_image(item) for item in request.observation.history_image_bytes if item]
    current = _decode_observation_image(request.observation.image_bytes)
    if current is not None:
        images.append(current)
    if images:
        return images
    if request.observation.image_path:
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Pillow is required to decode image observations") from exc
        return [Image.open(request.observation.image_path).convert("RGB")]
    return [_blank_image()]


def _observation_to_image(request: InferenceRequest):
    return _observation_to_images(request)[-1]


def _decode_observation_image(image_bytes: bytes | None):
    if not image_bytes:
        return None
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required to decode image observations") from exc

    try:
        return Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return Image.new("RGB", (1, 1), color=(0, 0, 0))


def _blank_image():
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required to decode image observations") from exc
    return Image.new("RGB", (1, 1), color=(0, 0, 0))
