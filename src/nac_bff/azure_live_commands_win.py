"""Disabled compatibility surface for the superseded Windows live runner.

Windows supports the portable NaC offline CLI only. Live execution, recovery
and reconciliation require the complete Linux security backend.
"""

from __future__ import annotations

from .azure_activation_contract import (
    PLATFORM_SECURITY_BACKEND_UNAVAILABLE,
    ActivationStepError,
)


def _blocked(*_args: object, **_kwargs: object) -> None:
    raise ActivationStepError(PLATFORM_SECURITY_BACKEND_UNAVAILABLE)


verified_sha256 = _blocked
launch_in_job_object = _blocked
acquire_windows_mutex = _blocked
release_windows_mutex = _blocked


__all__ = [
    "acquire_windows_mutex",
    "launch_in_job_object",
    "release_windows_mutex",
    "verified_sha256",
]
