"""Sign-in reporting for the borrowed agy credential."""

import asyncio
import time

import pytest

from kt_antigravity_login import auth
from kt_antigravity_login import status as status_mod
from kt_antigravity_login.auth import AntigravityError, BorrowedCredential
from kt_antigravity_login.presets import MODELS
from kt_antigravity_login.status import AntigravityAuth


def credential(seconds=3600, source="windows_keyring"):
    return BorrowedCredential("access-token", time.time() + seconds, source)


@pytest.fixture
def agy(monkeypatch):
    monkeypatch.setattr(auth, "read_sources", lambda: [credential()])
    monkeypatch.setattr(auth, "agy_executable", lambda: "C:/bin/agy.exe")


def test_ready_state_hides_the_login_hint(agy):
    assert AntigravityAuth.status() == {
        "state": "ready",
        "source": "windows_keyring",
        "refresh_available": True,
        "hint": "",
    }


def test_expired_credential_reports_the_login_hint(monkeypatch):
    monkeypatch.setattr(auth, "read_sources", lambda: [credential(-60, "agy_file")])
    monkeypatch.setattr(auth, "agy_executable", lambda: None)
    result = AntigravityAuth.status()
    assert (result["state"], result["source"]) == ("expired", "agy_file")
    assert result["refresh_available"] is False
    assert result["hint"] == status_mod.LOGIN_HINT


def test_missing_credential_reports_login_required(monkeypatch):
    monkeypatch.setattr(auth, "read_sources", list)
    monkeypatch.setattr(auth, "agy_executable", lambda: "C:/bin/agy.exe")
    assert AntigravityAuth.status()["state"] == "login_required"


def test_unreadable_store_keeps_its_diagnostic_code(monkeypatch):
    def boom():
        raise AntigravityError("credential_store_unavailable")

    monkeypatch.setattr(auth, "read_sources", boom)
    monkeypatch.setattr(auth, "agy_executable", lambda: "C:/bin/agy.exe")
    assert AntigravityAuth.status()["state"] == "credential_store_unavailable"


def test_unexpected_failure_degrades_to_unavailable(monkeypatch):
    def boom():
        raise RuntimeError("ctypes exploded")

    monkeypatch.setattr(auth, "read_sources", boom)
    monkeypatch.setattr(auth, "agy_executable", lambda: "C:/bin/agy.exe")
    assert AntigravityAuth.status()["state"] == "unavailable"


def test_availability_needs_a_fresh_or_renewable_token(monkeypatch):
    monkeypatch.setattr(auth, "read_sources", lambda: [credential()])
    monkeypatch.setattr(auth, "agy_executable", lambda: None)
    assert AntigravityAuth.available() is True
    monkeypatch.setattr(auth, "read_sources", lambda: [credential(-60)])
    assert AntigravityAuth.available() is False
    monkeypatch.setattr(auth, "agy_executable", lambda: "C:/bin/agy.exe")
    assert AntigravityAuth.available() is True


@pytest.mark.parametrize(
    "failure,state",
    [
        (AntigravityError("refresh_busy"), "refresh_busy"),
        (AntigravityError("login_required"), "login_required"),
        (AntigravityError("refresh_required"), "expired"),
        (AntigravityError("agy_refresh_failed"), "expired"),
    ],
)
async def test_refresh_maps_agy_failures_onto_states(agy, monkeypatch, failure, state):
    async def fail():
        raise failure

    monkeypatch.setattr(auth, "read_sources", lambda: [credential(-60)])
    monkeypatch.setattr(auth.AgyCredentials, "ensure_fresh", staticmethod(fail))
    assert (await AntigravityAuth.refresh())["state"] == state


async def test_refresh_reports_the_renewed_credential(agy, monkeypatch):
    async def renew():
        return credential()

    monkeypatch.setattr(auth.AgyCredentials, "ensure_fresh", staticmethod(renew))
    assert (await AntigravityAuth.refresh())["state"] == "ready"


async def test_stalled_refresh_reports_busy(agy, monkeypatch):
    async def stall():
        await asyncio.sleep(5)

    monkeypatch.setattr(auth.AgyCredentials, "ensure_fresh", staticmethod(stall))
    monkeypatch.setattr(status_mod, "REFRESH_TIMEOUT_S", 0.01)
    assert (await AntigravityAuth.refresh())["state"] == "refresh_busy"


def test_models_view_matches_the_catalogue():
    models = AntigravityAuth.models()["models"]
    assert [entry["id"] for entry in models] == list(MODELS)
    assert all(
        entry["max_context"] == spec.max_context
        for entry, spec in zip(models, MODELS.values())
    )
