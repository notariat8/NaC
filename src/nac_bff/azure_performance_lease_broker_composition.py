from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import os
from typing import Any, Mapping

from .azure_performance_lease_broker import (
    AttestedStorageBinding,
    AzurePerformanceLeaseBroker,
    RsaCertificateTicketSignatureVerifier,
)
from .azure_performance_lease_broker_storage import AzureBlobAtomicLeaseStateMachine


PERFORMANCE_LEASE_APP_ROLE = "Performance.Lease"
PERFORMANCE_LEASE_TICKET_SCOPE = "nac.performance.lease"


class PerformanceLeaseBrokerCompositionError(ValueError):
    """Generic failure for invalid broker deployment configuration."""


@dataclass(frozen=True, slots=True)
class PerformanceLeaseBrokerSettings:
    tenant_id: str
    audience: str
    actor_id: str
    owner_subject: str
    owner_binding_sha256: str
    commit_sha: str
    tree_sha: str
    function_package_sha256: str
    plan_sha256: str
    target_binding_sha256: str
    blob_path: str
    blob_url: str
    storage_binding_id: str
    storage_attestation: bytes
    ticket_issuer: str
    ticket_key_id: str
    ticket_certificate: bytes
    ticket_certificate_sha256: str

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None
    ) -> PerformanceLeaseBrokerSettings:
        values = os.environ if env is None else env
        if values.get("NAC_BFF_PERFORMANCE_LEASE_ENABLED") != "true":
            raise PerformanceLeaseBrokerCompositionError(
                "performance lease broker is disabled"
            )
        try:
            return cls(
                tenant_id=_required(values, "NAC_BFF_PERFORMANCE_LEASE_TENANT_ID"),
                audience=_required(values, "NAC_BFF_AUDIENCE"),
                actor_id=_required(values, "NAC_BFF_PERFORMANCE_LEASE_ACTOR_ID"),
                owner_subject=_required(
                    values, "NAC_BFF_PERFORMANCE_LEASE_OWNER_SUBJECT"
                ),
                owner_binding_sha256=_required(
                    values, "NAC_BFF_PERFORMANCE_LEASE_OWNER_BINDING_SHA256"
                ),
                commit_sha=_required(
                    values, "NAC_BFF_PERFORMANCE_LEASE_COMMIT_SHA"
                ),
                tree_sha=_required(values, "NAC_BFF_PERFORMANCE_LEASE_TREE_SHA"),
                function_package_sha256=_required(
                    values, "NAC_BFF_PERFORMANCE_LEASE_FUNCTION_PACKAGE_SHA256"
                ),
                plan_sha256=_required(
                    values, "NAC_BFF_PERFORMANCE_LEASE_PLAN_SHA256"
                ),
                target_binding_sha256=_required(
                    values, "NAC_BFF_PERFORMANCE_LEASE_TARGET_BINDING_SHA256"
                ),
                blob_path=_required(values, "NAC_BFF_PERFORMANCE_LEASE_BLOB_PATH"),
                blob_url=_required(values, "NAC_BFF_PERFORMANCE_LEASE_BLOB_URL"),
                storage_binding_id=_required(
                    values, "NAC_BFF_PERFORMANCE_LEASE_STORAGE_BINDING_ID"
                ),
                storage_attestation=_decode(
                    values, "NAC_BFF_PERFORMANCE_LEASE_STORAGE_ATTESTATION_B64"
                ),
                ticket_issuer=_required(
                    values, "NAC_BFF_PERFORMANCE_LEASE_TICKET_ISSUER"
                ),
                ticket_key_id=_required(
                    values, "NAC_BFF_PERFORMANCE_LEASE_TICKET_KEY_ID"
                ),
                ticket_certificate=_decode(
                    values, "NAC_BFF_PERFORMANCE_LEASE_TICKET_CERTIFICATE_B64"
                ),
                ticket_certificate_sha256=_required(
                    values,
                    "NAC_BFF_PERFORMANCE_LEASE_TICKET_CERTIFICATE_SHA256",
                ),
            )
        except Exception:
            raise PerformanceLeaseBrokerCompositionError(
                "performance lease broker configuration is invalid"
            ) from None


class _FixedBindingProvider:
    def __init__(self, binding: AttestedStorageBinding) -> None:
        self._binding = binding

    def load(self) -> AttestedStorageBinding:
        return self._binding


def build_performance_lease_broker(
    env: Mapping[str, str] | None = None,
    *,
    credential_factory: Any | None = None,
    opener: Any | None = None,
) -> AzurePerformanceLeaseBroker:
    settings = PerformanceLeaseBrokerSettings.from_env(env)
    if credential_factory is None:
        try:
            from azure.identity import ManagedIdentityCredential
        except ImportError:
            raise PerformanceLeaseBrokerCompositionError(
                "managed identity runtime is unavailable"
            ) from None
        credential_factory = ManagedIdentityCredential
    try:
        # Resource-instance Storage rules authorize the Function's
        # system-assigned identity. Graph and host storage remain on the UAMI.
        credential = credential_factory()
        verifier = RsaCertificateTicketSignatureVerifier(
            key_id=settings.ticket_key_id,
            certificate_bytes=settings.ticket_certificate,
            certificate_sha256=settings.ticket_certificate_sha256,
        )
        binding = AttestedStorageBinding(
            settings.storage_binding_id,
            settings.storage_attestation,
        )
        state_machine = AzureBlobAtomicLeaseStateMachine(
            blob_url=settings.blob_url,
            expected_blob_path=(
                f"/nac-bff-performance-leases/{settings.blob_path}"
            ),
            token_provider=credential,
            opener=opener,
        )
        return AzurePerformanceLeaseBroker(
            signature_verifier=verifier,
            binding_provider=_FixedBindingProvider(binding),
            state_machine=state_machine,
            issuer=settings.ticket_issuer,
            tenant_id=settings.tenant_id,
            audience=settings.audience,
            actor_id=settings.actor_id,
            owner_subject=settings.owner_subject,
            owner_binding_sha256=settings.owner_binding_sha256,
            commit_sha=settings.commit_sha,
            tree_sha=settings.tree_sha,
            function_package_sha256=settings.function_package_sha256,
            plan_sha256=settings.plan_sha256,
            target_binding_sha256=settings.target_binding_sha256,
            blob_path=settings.blob_path,
            required_role=PERFORMANCE_LEASE_APP_ROLE,
            required_scope=PERFORMANCE_LEASE_TICKET_SCOPE,
        )
    except PerformanceLeaseBrokerCompositionError:
        raise
    except Exception:
        raise PerformanceLeaseBrokerCompositionError(
            "performance lease broker composition failed"
        ) from None


def _required(values: Mapping[str, str], name: str) -> str:
    value = values.get(name)
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 4096
        or any(character in value for character in "\r\n\x00")
    ):
        raise ValueError(name)
    return value


def _decode(values: Mapping[str, str], name: str) -> bytes:
    value = _required(values, name)
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError(name) from None
    if not 32 <= len(decoded) <= 8192:
        raise ValueError(name)
    return decoded
