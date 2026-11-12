"""Manifest contents that make the backend visible in Settings -> Providers."""

from pathlib import Path

import yaml

from kt_antigravity_login.presets import PRESETS, PROVIDER

ROOT = Path(__file__).resolve().parents[1]
ENTRY_KEYS = {"module", "class", "display_name", "description", "credentials"}
BUILTIN_TYPE = "google-antigravity"


def manifest():
    return yaml.safe_load((ROOT / "kohaku.yaml").read_text(encoding="utf-8"))


def test_provider_is_the_builtin_type_the_package_owns():
    assert PROVIDER == BUILTIN_TYPE


def test_backend_entry_owns_the_builtin_type_and_its_local_auth():
    entry = manifest()["llm_backends"][0]
    assert entry["name"] == BUILTIN_TYPE
    assert entry["class"] == "AntigravityProvider"
    assert entry["display_name"] == "Google Antigravity"
    assert entry["description"] == "Reuse the local agy login."
    assert entry["credentials"] == "external"
    assert entry["provider_native_tools"] == []
    assert entry["owns_builtin"] is True
    assert entry["auth"] == {
        "module": "kt_antigravity_login.status",
        "class": "AntigravityAuth",
        "local_only": True,
        "login_hint": "Run agy to sign in.",
    }
    assert ENTRY_KEYS <= set(entry)


def test_manifest_declares_one_backend_so_settings_shows_one_row():
    assert len(manifest()["llm_backends"]) == 1


def test_presets_are_generated_from_the_catalogue():
    expected = [
        {"name": name, "provider": provider, **body}
        for (provider, name), body in PRESETS.items()
    ]
    assert manifest()["llm_presets"] == expected


def test_every_preset_targets_this_backend():
    presets = manifest()["llm_presets"]
    assert presets and {preset["provider"] for preset in presets} == {PROVIDER}
    assert all(preset["model"] == preset["name"] for preset in presets)
