from navida_deploy.hf_backend import (
    HuggingFaceQwen25VLBackend,
    build_navida_messages,
    detection_to_target_metadata,
    parse_action_text,
    parse_target_metadata,
)
from navida_deploy.messages import InferenceRequest, Observation


def test_parse_action_text_extracts_json_actions():
    chunks = parse_action_text('{"actions": ["forward", "turn_left", "stop"]}')

    assert [chunk.action for chunk in chunks] == ["forward", "turn_left", "stop"]


def test_parse_action_text_extracts_json_action_chunks_with_repeats():
    chunks = parse_action_text('{"actions": [{"action": "forward", "repeat": 2}, {"action": "turn_left"}]}')

    assert [(chunk.action, chunk.repeat) for chunk in chunks] == [("forward", 2), ("turn_left", 1)]


def test_parse_action_text_normalizes_plain_language_actions():
    chunks = parse_action_text("Go forward, then turn right, then stop.")

    assert [chunk.action for chunk in chunks] == ["forward", "turn_right", "stop"]


def test_parse_action_text_extracts_official_distance_and_degree_chunks():
    chunks = parse_action_text("forward 75 cm, turn left 30 degree, turn right 15 degree")

    assert [(chunk.action, chunk.repeat) for chunk in chunks] == [
        ("forward", 3),
        ("turn_left", 2),
        ("turn_right", 1),
    ]


def test_hf_backend_maps_single_cuda_device_for_accelerate():
    backend = HuggingFaceQwen25VLBackend(device="cuda")

    assert backend.device_map() == {"": "cuda"}


def test_hf_backend_infer_uses_generated_action_text():
    captured = {}

    class FakeBatch(dict):
        def to(self, device):
            self["device"] = device
            return self

    class FakeProcessor:
        def apply_chat_template(self, messages, tokenize, add_generation_prompt):
            return "prompt"

        def __call__(self, **kwargs):
            captured["processor_kwargs"] = kwargs
            return FakeBatch(input_ids=[[1, 2, 3]])

        def batch_decode(self, generated_ids, skip_special_tokens, clean_up_tokenization_spaces):
            return ["forward 25 cm, turn right 15 degree"]

    class FakeModel:
        def generate(self, **kwargs):
            captured["generate_kwargs"] = kwargs
            return [[1, 2, 3, 4, 5]]

    backend = HuggingFaceQwen25VLBackend(input_device="cuda")
    backend.load = lambda: (FakeModel(), FakeProcessor())

    response = backend.infer(
        InferenceRequest(
            session_id="s1",
            step_index=2,
            instruction="go forward then turn right",
            observation=Observation(image_bytes=b"not-a-real-image"),
        )
    )

    assert response.session_id == "s1"
    assert response.step_index == 2
    assert [chunk.action for chunk in response.chunks] == ["forward", "turn_right"]
    assert isinstance(captured["processor_kwargs"]["images"][0], list)
    assert captured["generate_kwargs"]["max_new_tokens"] == 512
    assert captured["generate_kwargs"]["temperature"] == 0.2


def test_build_navida_messages_includes_history_and_current_images():
    request = InferenceRequest(
        session_id="s-history",
        step_index=1,
        instruction="go to the goal",
        observation=Observation(
            image_bytes=b"not-a-real-current-image",
            history_image_bytes=[b"not-a-real-old-1", b"not-a-real-old-2"],
        ),
    )

    messages = build_navida_messages(request)
    content = messages[1]["content"]

    assert messages[0]["role"] == "system"
    assert [item["type"] for item in content].count("image") == 3
    assert content[0]["text"] == (
        "Imagine you are a robot programmed for navigation tasks. "
        "You have been given a video of historical observations"
    )
    assert content[-1]["text"].startswith(". Your assigned task is: 'go to the goal'. Analyze this series of images")


def test_hf_backend_does_not_use_target_detector_without_fallback_enabled():
    class FakeBatch(dict):
        def to(self, device):
            return self

    class FakeProcessor:
        def apply_chat_template(self, messages, tokenize, add_generation_prompt):
            return "prompt"

        def __call__(self, **kwargs):
            return FakeBatch(input_ids=[[1]])

        def batch_decode(self, generated_ids, skip_special_tokens, clean_up_tokenization_spaces):
            return ['{"actions": ["forward"]}']

    class FakeModel:
        def generate(self, **kwargs):
            return [[1, 2]]

    class FailingDetector:
        def __call__(self, *args, **kwargs):
            raise AssertionError("target detector should be opt-in fallback only")

    backend = HuggingFaceQwen25VLBackend(input_device="cuda", target_detector_model_id="fake-detector")
    backend.load = lambda: (FakeModel(), FakeProcessor())
    backend._target_detector = FailingDetector()

    response = backend.infer(
        InferenceRequest(
            session_id="s1",
            step_index=0,
            instruction="go forward",
            observation=Observation(image_bytes=b"not-a-real-image", metadata={"target_label": "chair"}),
        )
    )

    assert [chunk.action for chunk in response.chunks] == ["forward"]
    assert response.metadata["backend"] == backend.model_id
    assert response.metadata["inference_ms"] == 0.0
    assert "target" not in response.metadata


def test_parse_target_metadata_extracts_json_target():
    metadata = parse_target_metadata(
        '{"target": {"visible": true, "center_x": 0.75, "area": 0.12, "confidence": 0.8}, '
        '"actions": ["turn_right"]}'
    )

    assert metadata == {
        "target": {
            "visible": True,
            "center_x": 0.75,
            "area": 0.12,
            "confidence": 0.8,
        }
    }


def test_detection_to_target_metadata_uses_best_box():
    metadata = detection_to_target_metadata(
        [
            {"score": 0.2, "box": {"xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10}},
            {"score": 0.9, "box": {"xmin": 40, "ymin": 10, "xmax": 80, "ymax": 50}},
        ],
        image_width=100,
        image_height=100,
    )

    assert metadata == {
        "target": {
            "visible": True,
            "center_x": 0.6,
            "area": 0.16,
            "confidence": 0.9,
        }
    }


def test_detection_to_target_metadata_prefers_large_centered_target():
    metadata = detection_to_target_metadata(
        [
            {"score": 0.268, "box": {"xmin": 30, "ymin": 196, "xmax": 96, "ymax": 315}},
            {"score": 0.254, "box": {"xmin": 190, "ymin": 98, "xmax": 456, "ymax": 401}},
        ],
        image_width=640,
        image_height=480,
    )

    assert metadata["target"]["center_x"] == 0.504687
    assert metadata["target"]["area"] == 0.262363


def test_detect_target_expands_bare_object_label_to_prompt_phrase():
    class FakeImage:
        width = 100
        height = 100

    class FakeDetector:
        def __call__(self, image, candidate_labels, threshold):
            if "a chair" not in candidate_labels:
                return []
            return [
                {
                    "score": 0.3,
                    "label": "a chair",
                    "box": {"xmin": 20, "ymin": 10, "xmax": 80, "ymax": 70},
                }
            ]

    backend = HuggingFaceQwen25VLBackend(target_detector_model_id="fake-detector")
    backend._target_detector = FakeDetector()
    request = InferenceRequest(
        session_id="s1",
        step_index=0,
        instruction="Go to the chair",
        observation=Observation(metadata={"target_label": "chair"}),
    )

    metadata = backend.detect_target(request, FakeImage())

    assert metadata == {
        "target": {
            "visible": True,
            "center_x": 0.5,
            "area": 0.36,
            "confidence": 0.3,
        }
    }
