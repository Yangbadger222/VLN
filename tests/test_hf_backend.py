from navida_deploy.hf_backend import HuggingFaceQwen25VLBackend, parse_action_text, parse_target_metadata
from navida_deploy.messages import InferenceRequest, Observation


def test_parse_action_text_extracts_json_actions():
    chunks = parse_action_text('{"actions": ["forward", "turn_left", "stop"]}')

    assert [chunk.action for chunk in chunks] == ["forward", "turn_left", "stop"]


def test_parse_action_text_normalizes_plain_language_actions():
    chunks = parse_action_text("Go forward, then turn right, then stop.")

    assert [chunk.action for chunk in chunks] == ["forward", "turn_right", "stop"]


def test_hf_backend_maps_single_cuda_device_for_accelerate():
    backend = HuggingFaceQwen25VLBackend(device="cuda")

    assert backend.device_map() == {"": "cuda"}


def test_hf_backend_infer_uses_generated_action_text():
    class FakeBatch(dict):
        def to(self, device):
            self["device"] = device
            return self

    class FakeProcessor:
        def apply_chat_template(self, messages, tokenize, add_generation_prompt):
            return "prompt"

        def __call__(self, **kwargs):
            return FakeBatch(input_ids=[[1, 2, 3]])

        def batch_decode(self, generated_ids, skip_special_tokens, clean_up_tokenization_spaces):
            return ['{"actions": ["forward", "turn_right"]}']

    class FakeModel:
        def generate(self, **kwargs):
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
