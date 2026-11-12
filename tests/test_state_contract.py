"""Golden contract for the signed replay state stored in session history.

The frozen values below were produced by the core provider before this module
moved into the package; any drift breaks replay of existing sessions.
"""

import copy

from kt_antigravity_login.format import STATE_KEY, replay_target, signed_state

MESSAGE = {
    "role": "assistant",
    "content": "hi",
    "tool_calls": [
        {"id": "a", "type": "function", "function": {"name": "echo", "arguments": "{}"}}
    ],
}
PARTS = [
    {"text": "hi", "thoughtSignature": "sig"},
    {"functionCall": {"name": "echo", "args": {}}},
]
GOLDEN = {
    "version": 1,
    "provider": "google-antigravity",
    "model": "gemini-4-argon-medium",
    "scope": "proj",
    "digest": "2602d0e8faff8cf4dd84c3f4bf731e910ad2e0cafd9e497ad856a97757906e2c",
    "parts": PARTS,
}


def test_state_key_literal_is_frozen():
    assert STATE_KEY == "_kt_antigravity_content"


def test_signed_state_matches_the_frozen_bytes():
    assert (
        signed_state(MESSAGE, copy.deepcopy(PARTS), "gemini-4-argon-medium", "proj")
        == GOLDEN
    )


def test_signed_parts_are_detached_from_the_caller():
    parts = copy.deepcopy(PARTS)
    state = signed_state(MESSAGE, parts, "gemini-4-argon-medium", "proj")
    parts[0]["text"] = "mutated"
    assert state["parts"][0]["text"] == "hi"


def test_bound_message_is_reused_without_rewriting_it():
    target = copy.deepcopy(MESSAGE)
    messages = [target]
    assert replay_target(messages, target, GOLDEN) is target
    assert messages == [target] and STATE_KEY not in target


def test_signed_empty_turn_is_appended_as_a_fresh_round():
    empty = {"role": "assistant", "content": ""}
    state = signed_state(empty, [], "gemini-4-argon-medium", "proj")
    messages = []
    chosen = replay_target(messages, None, state)
    assert chosen == empty and messages == [empty]


def test_edited_history_is_not_replayed():
    edited = copy.deepcopy(MESSAGE)
    edited["content"] = "edited"
    assert replay_target([], edited, GOLDEN) is None
