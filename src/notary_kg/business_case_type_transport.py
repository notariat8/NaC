from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


RegistryFetchStatus = Literal["OK", "NOT_MODIFIED", "UNAVAILABLE"]


@dataclass(frozen=True, slots=True)
class BusinessCaseTypeRegistryRow:
    business_case_type_id: str
    lifecycle_status: str
    selectable: bool
    catalog_version: str
    etag: str


@dataclass(frozen=True, slots=True)
class RegistryFetchResult:
    status: RegistryFetchStatus
    rows: tuple[BusinessCaseTypeRegistryRow, ...] = ()
    reason_code: str = ""
    pages_complete: bool = True

    @classmethod
    def ok(
        cls,
        *rows: BusinessCaseTypeRegistryRow,
        pages_complete: bool = True,
    ) -> "RegistryFetchResult":
        return cls(status="OK", rows=tuple(rows), pages_complete=pages_complete)

    @classmethod
    def not_modified(cls) -> "RegistryFetchResult":
        return cls(status="NOT_MODIFIED")

    @classmethod
    def unavailable(cls, reason_code: str = "transport_unavailable") -> "RegistryFetchResult":
        return cls(status="UNAVAILABLE", reason_code=reason_code)


class BusinessCaseTypeRegistryReadPort(Protocol):
    def fetch_registry(
        self,
        *,
        site_id: str,
        business_case_type_id: str,
        catalog_version: str,
        if_none_match: str | None,
    ) -> RegistryFetchResult: ...


@dataclass(frozen=True, slots=True)
class ViewerMetadataFetchResult:
    status: RegistryFetchStatus
    etag: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()
    reason_code: str = ""


class BusinessCaseTypeViewerReadPort(Protocol):
    def fetch_viewer_metadata(
        self,
        *,
        site_id: str,
        business_case_type_id: str,
        if_none_match: str | None,
    ) -> ViewerMetadataFetchResult: ...
