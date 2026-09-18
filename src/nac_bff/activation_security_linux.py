from __future__ import annotations

from .activation_security_backend import PlatformSecurityBackendUnavailable


class LinuxActivationSecurityBackend:
    """Fail-closed marker for the unsupported full Linux live backend.

    Existing hermetic POSIX file, memfd, descriptor and lock primitives remain
    available to their bounded consumers. They do not constitute a complete
    live activation backend and must never be advertised as one.
    """

    def capabilities(self):
        raise PlatformSecurityBackendUnavailable()


__all__ = ["LinuxActivationSecurityBackend"]
