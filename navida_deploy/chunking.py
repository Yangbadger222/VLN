from __future__ import annotations

from random import random
from typing import Callable, Iterable

from .messages import ActionChunk


def chunk_atomic_actions(
    actions: Iterable[str],
    merge_probability: float = 0.5,
    rng: Callable[[], float] = random,
) -> list[ActionChunk]:
    chunks: list[ActionChunk] = []
    current_action: str | None = None
    repeat = 0

    for action in actions:
        if current_action is None:
            current_action = action
            repeat = 1
            continue

        should_merge = action == current_action and repeat < 3 and rng() <= merge_probability
        if should_merge:
            repeat += 1
            continue

        chunks.append(ActionChunk(index=len(chunks), action=current_action, repeat=repeat))
        current_action = action
        repeat = 1

    if current_action is not None:
        chunks.append(ActionChunk(index=len(chunks), action=current_action, repeat=repeat))

    return chunks

