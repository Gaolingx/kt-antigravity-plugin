"""Sign-in status for the ``google-antigravity-plugin`` backend.

The backend borrows whatever credential the official ``agy`` CLI already owns,
so "signed in" means "a usable local credential exists". Nothing here mints,
writes or logs credential material.
"""

import asyncio

from kohakuterrarium.utils.logging import get_logger

from . import auth
from .presets import MODELS

logger = get_logger(__name__)

LOGIN_HINT = "Run agy to sign in."
REFRESH_TIMEOUT_S = 20
# agy-side refresh failures mapped onto states the core already understands.
REFRESH_STATES = {
    "refresh_busy": "refresh_busy",
    "login_required": "login_required",
    "refresh_required": "expired",
}


class AntigravityAuth:
    """Report and renew the borrowed agy credential for Settings -> Providers."""

    @classmethod
    def status(cls) -> dict:
        """Current sign-in state; sync and cheap, so the core runs it off-loop."""
        try:
            token = auth.load_credential()
            state, source = ("ready" if token.fresh() else "expired"), token.source
        except auth.AntigravityError as exc:
            state, source = str(exc.code), ""
        except Exception as exc:
            logger.warning("Antigravity credential read failed", error=str(exc))
            state, source = "unavailable", ""
        return {
            "state": state,
            "source": source,
            "refresh_available": bool(auth.agy_executable()),
            "hint": "" if state == "ready" else LOGIN_HINT,
        }

    @classmethod
    def available(cls) -> bool:
        """True when a turn can start without any user action."""
        status = cls.status()
        return status["state"] == "ready" or (
            status["state"] == "expired" and status["refresh_available"]
        )

    @classmethod
    async def refresh(cls) -> dict:
        """Ask agy to renew the token, then report the resulting state."""
        failure = ""
        try:
            await asyncio.wait_for(
                auth.AgyCredentials.ensure_fresh(), timeout=REFRESH_TIMEOUT_S
            )
        except asyncio.TimeoutError:
            failure = "refresh_busy"
        except auth.AntigravityError as exc:
            failure = str(exc.code)
        except Exception as exc:
            logger.warning("Antigravity refresh failed", error=str(exc))
            failure = "unavailable"
        result = cls.status()
        mapped = REFRESH_STATES.get(failure)
        if mapped:
            result["state"] = mapped
        elif failure:
            result["hint"] = LOGIN_HINT
        return result

    @classmethod
    def models(cls) -> dict:
        """The model families this backend drives, from the bundled catalogue."""
        return {
            "models": [
                {
                    "id": name,
                    "name": name,
                    "max_context": spec.max_context,
                    "max_output": spec.max_output,
                    "reasoning_efforts": list(spec.efforts),
                }
                for name, spec in MODELS.items()
            ]
        }
