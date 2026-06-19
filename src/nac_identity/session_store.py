from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class RuntimeSessionStoreAdapter(Protocol):
    def get_session_record(self, session_id: str) -> Mapping[str, Any] | None:
        """Return a server-side session record for a signed session id."""


class MappingSessionStoreAdapter:
    def __init__(self, records: Mapping[str, Mapping[str, Any]]) -> None:
        self._records = records

    def get_session_record(self, session_id: str) -> Mapping[str, Any] | None:
        return self._records.get(session_id)
