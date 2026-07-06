from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable, Protocol

from nac_identity.onboarding_requests import OnboardingRequestStoreUnavailable


class RuntimeSessionStoreAdapter(Protocol):
    def get_session_record(self, session_id: str) -> Mapping[str, Any] | None:
        """Return a server-side session record for a signed session id."""


class RuntimeSessionWriteStoreAdapter(RuntimeSessionStoreAdapter, Protocol):
    def create_session_record(
        self,
        *,
        session_id: str,
        tenant_slug: str,
        subject_hash: str,
        role_class: str,
        usecase_slug: str,
        purpose: str,
        issued_at: int,
        expires_at: int,
        audit_event_id: str = "",
    ) -> Mapping[str, Any]:
        """Persist a redacted server-side session record."""


class MappingSessionStoreAdapter:
    def __init__(self, records: Mapping[str, Mapping[str, Any]]) -> None:
        self._records = records

    def get_session_record(self, session_id: str) -> Mapping[str, Any] | None:
        return self._records.get(session_id)


class DisabledSessionStore:
    def get_session_record(self, _session_id: str) -> Mapping[str, Any] | None:
        raise OnboardingRequestStoreUnavailable("session_store_disabled")


def build_session_store_from_env(
    environ: dict[str, str] | None = None,
    *,
    secret_text_provider: Callable[[str], str] | None = None,
    secret_bytes_provider: Callable[[str], bytes] | None = None,
    object_bytes_provider: Callable[[str, str, str], bytes] | None = None,
    connector: Callable[..., Any] | None = None,
) -> DisabledSessionStore:
    del environ, secret_text_provider, secret_bytes_provider, object_bytes_provider, connector
    return DisabledSessionStore()
