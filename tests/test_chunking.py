from navida_deploy.chunking import chunk_atomic_actions
from navida_deploy.messages import ActionChunk


def test_chunk_atomic_actions_merges_repeated_actions_up_to_three():
    chunks = chunk_atomic_actions(
        ["forward", "forward", "forward", "forward", "turn_left"],
        merge_probability=1.0,
        rng=lambda: 0.0,
    )

    assert chunks == [
        ActionChunk(index=0, action="forward", repeat=3),
        ActionChunk(index=1, action="forward", repeat=1),
        ActionChunk(index=2, action="turn_left", repeat=1),
    ]

