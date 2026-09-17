from __future__ import annotations

from .activation_security_backend import PlatformSecurityBackendUnavailable


class LinuxActivationSecurityBackend:
    """Adapter placeholder until the existing Linux primitives are isolated here.

    It intentionally has no capabilities instead of silently weakening the
    established live-execution boundary.
    """

    def capabilities(self):
        raise PlatformSecurityBackendUnavailable()


__all__ = ["LinuxActivationSecurityBackend"]
