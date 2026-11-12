"""Model catalogue and variation-group data this package publishes."""

import pytest
from kohakuterrarium.llm.profiles.variations import apply_variation_groups

from kt_antigravity_login.presets import (
    DEPRECATED,
    MODELS,
    PRESETS,
    PROVIDER,
    model_settings,
)

LEVELS = ["low", "medium", "high"]


def preset(model):
    return PRESETS[(PROVIDER, model)]


@pytest.mark.parametrize(
    "model,context,output,efforts,contexts",
    [
        ("gemini-4-argon", 256000, 65536, LEVELS, ["256k", "512k", "900k"]),
        ("gemini-3.8-flash", 256000, 65536, LEVELS, ["256k", "1048k"]),
        ("claude-opus-5-5", 256000, 128000, LEVELS, ["256k", "840k"]),
        ("claude-sonnet-5-5", 256000, 128000, LEVELS, ["256k", "840k"]),
        ("gpt-oss-120b", 80000, 32768, [], ["80k", "131k"]),
    ],
)
def test_current_agy_limits_and_variations(model, context, output, efforts, contexts):
    body = preset(model)
    assert (body["max_context"], body["max_output"]) == (context, output)
    assert body["reasoning_effort"] == "medium"
    groups = body["variation_groups"]
    assert list(groups.get("reasoning", {})) == efforts
    assert list(groups["context"]) == contexts


def test_catalog_is_exactly_the_agy_agent_list():
    advertised = {
        f"{family}-{effort}"
        for family, spec in MODELS.items()
        for effort in spec.efforts
    }
    assert advertised == {
        *(f"gemini-4-carbon-{e}" for e in LEVELS),
        *(f"gemini-4-argon-{e}" for e in LEVELS),
        *(f"gemini-3.8-flash-{e}" for e in LEVELS),
        *(f"claude-opus-5-5-{e}" for e in LEVELS),
        *(f"claude-sonnet-5-5-{e}" for e in LEVELS),
        "gpt-oss-120b-medium",
    }
    assert {name for provider, name in PRESETS if provider == PROVIDER} == set(MODELS)


@pytest.mark.parametrize(
    "model,effort,wire,thinking,limit",
    [
        (
            "gemini-4-argon",
            "",
            "gemini-4-argon-medium",
            {"thinkingLevel": "MEDIUM"},
            65536,
        ),
        (
            "gemini-4-argon-high",
            "",
            "gemini-4-argon-high",
            {"thinkingLevel": "HIGH"},
            65536,
        ),
        (
            "gemini-3.8-flash",
            "low",
            "gemini-3.8-flash-low",
            {"thinkingBudget": 1000},
            65536,
        ),
        (
            "gemini-3.8-flash-high",
            "high",
            "gemini-3.8-flash-high",
            {"thinkingBudget": -1},
            65536,
        ),
        (
            "claude-opus-5-5-low",
            "",
            "claude-opus-5-5-low",
            {"thinkingLevel": "LOW"},
            128000,
        ),
        ("gpt-oss-120b", "", "gpt-oss-120b-medium", {"thinkingBudget": 8192}, 32768),
    ],
)
def test_default_and_explicit_sku_settings(model, effort, wire, thinking, limit):
    settings = model_settings(model, effort)
    assert settings.wire_model == wire
    assert settings.thinking_config == {"includeThoughts": True, **thinking}
    assert settings.max_output == limit


def test_custom_model_passes_through_without_thinking():
    settings = model_settings("gemini-custom")
    assert (settings.wire_model, settings.max_output, settings.max_context) == (
        "gemini-custom",
        8192,
        120000,
    )
    assert settings.thinking_config == {}


@pytest.mark.parametrize(
    "model,effort,limit,error",
    [
        ("gemini-4-argon-minimal", "", None, "unsupported_reasoning_effort"),
        ("gemini-4-argon-tiered", "", None, "unsupported_reasoning_effort"),
        ("gemini-3.8-flash-low", "high", None, "conflicting_reasoning_effort"),
        ("gpt-oss-120b", "high", None, "unsupported_reasoning_effort"),
        ("gemini-unknown", "high", None, "unsupported_reasoning_effort"),
        (
            "gemini-3.8-flash-low",
            "",
            1000,
            "max_output_tokens_must_exceed_thinking_budget",
        ),
        ("gpt-oss-120b", "", 8192, "max_output_tokens_must_exceed_thinking_budget"),
        ("gemini-3.8-flash", "low", 65537, "invalid_max_output_tokens"),
        ("gemini-3.8-flash", "low", 1.5, "invalid_max_output_tokens"),
        ("gemini-3.8-flash", "low", True, "invalid_max_output_tokens"),
        ("claude-sonnet-5-5", "", 128001, "invalid_max_output_tokens"),
    ],
)
def test_reject_invalid_settings(model, effort, limit, error):
    with pytest.raises(ValueError, match=error):
        model_settings(model, effort, limit)


def test_dynamic_budget_accepts_any_output_limit():
    settings = model_settings("gemini-3.8-flash-high", "", 64)
    assert settings.max_output == 64
    assert settings.thinking_config["thinkingBudget"] == -1


@pytest.mark.parametrize("old,replacement", sorted(DEPRECATED.items()))
def test_retired_raw_ids_name_their_successor(old, replacement):
    assert replacement in MODELS
    for model in (old, old + "-high"):
        with pytest.raises(ValueError, match=f"deprecated_model, use {replacement}"):
            model_settings(model)


def test_smaller_explicit_output_is_preserved():
    assert model_settings("gemini-4-argon", "low", 4096).max_output == 4096
    assert model_settings("gemini-unknown", "", 1024).max_output == 1024


@pytest.mark.parametrize(
    "model,group,option",
    [
        ("gemini-4-argon", "reasoning", "minimal"),
        ("gemini-4-argon", "context", "1048k"),
        ("gemini-3.8-flash", "context", "900k"),
        ("gpt-oss-120b", "reasoning", "medium"),
        ("claude-sonnet-5-5", "reasoning", "max"),
    ],
)
def test_unsupported_variations_are_not_advertised(model, group, option):
    groups = preset(model).get("variation_groups", {})
    assert option not in groups.get(group, {})


@pytest.mark.parametrize(
    "model,selections,context,effort",
    [
        ("gemini-4-argon", {}, 256000, "medium"),
        ("gemini-4-argon", {"context": "512k"}, 512000, "medium"),
        ("gemini-4-argon", {"context": "900k", "reasoning": "low"}, 900000, "low"),
        ("gemini-3.8-flash", {"context": "1048k"}, 1048576, "medium"),
        ("claude-opus-5-5", {"reasoning": "high", "context": "840k"}, 840000, "high"),
        ("gpt-oss-120b", {"context": "131k"}, 131072, "medium"),
    ],
)
def test_context_window_selects_profile_budget(model, selections, context, effort):
    body = preset(model)
    resolved = apply_variation_groups(
        dict(body), body.get("variation_groups", {}), selections
    )
    assert resolved["max_context"] == context
    assert resolved["reasoning_effort"] == effort
    settings = model_settings(model, resolved["reasoning_effort"])
    assert settings.wire_model == f"{model}-{effort}"


def test_retired_presets_are_not_advertised():
    for old in DEPRECATED:
        assert (PROVIDER, old) not in PRESETS
