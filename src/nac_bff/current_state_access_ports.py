from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from .current_state_access_gate import CurrentStateRunAuthorization


@dataclass(frozen=True)
class PortReadResult:
    data: Mapping[str, Any]
    receipt_sha256: str
    operation: str


class ClientObservationReceiptPort(Protocol):
    def read(self, authorization: CurrentStateRunAuthorization) -> PortReadResult: ...


class TeamsTabMetadataReadPort(Protocol):
    def read(self, authorization: CurrentStateRunAuthorization) -> PortReadResult: ...


class SharePointAppCatalogReadPort(Protocol):
    def read(self, authorization: CurrentStateRunAuthorization) -> PortReadResult: ...


class EntraApiPermissionReadPort(Protocol):
    def read(self, authorization: CurrentStateRunAuthorization) -> PortReadResult: ...


class AzureFunctionMetadataReadPort(Protocol):
    def read(self, authorization: CurrentStateRunAuthorization) -> PortReadResult: ...


class AzureFunctionRequestLogReadPort(Protocol):
    def read(self, authorization: CurrentStateRunAuthorization) -> PortReadResult: ...


class SharePointAccessDecisionReadPort(Protocol):
    def read(self, authorization: CurrentStateRunAuthorization) -> PortReadResult: ...


@dataclass(frozen=True)
class CurrentStateAccessPorts:
    client_observation: ClientObservationReceiptPort
    teams_tab: TeamsTabMetadataReadPort
    app_catalog: SharePointAppCatalogReadPort
    entra_permissions: EntraApiPermissionReadPort
    function_metadata: AzureFunctionMetadataReadPort
    request_log: AzureFunctionRequestLogReadPort
    access_decision: SharePointAccessDecisionReadPort


__all__ = [
    "AzureFunctionMetadataReadPort",
    "AzureFunctionRequestLogReadPort",
    "ClientObservationReceiptPort",
    "CurrentStateAccessPorts",
    "EntraApiPermissionReadPort",
    "PortReadResult",
    "SharePointAccessDecisionReadPort",
    "SharePointAppCatalogReadPort",
    "TeamsTabMetadataReadPort",
]
