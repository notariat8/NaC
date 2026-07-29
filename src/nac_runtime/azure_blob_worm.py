from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Protocol, TypeVar

from nac_runtime.immutable_evidence import (
    LIVE_STATUS,
    MINIMUM_RETENTION_YEARS,
    EvidenceRecord,
    canonical_json_bytes,
    verify_chain,
    _publication_operation_key,
)


S6B_STATUS = "S6B_AZURE_WORM_ADAPTER_READY_OFFLINE"
_SCHEMA_VERSION = "nac.azure-blob-worm-object/v0.3"
_PUBLIC_ERROR = "Azure Blob WORM operation rejected"
_MAX_BLOB_BYTES = 4 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_RECEIPT = re.compile(r"worm-receipt-v1-[0-9a-f]{64}\Z")
_ANCHOR = re.compile(r"anchor-v1-[0-9a-f]{64}\Z")
_SIGNATURE = re.compile(r"signature-v1-[0-9a-f]{64}\Z")
_AZURE_NAME = re.compile(r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?\Z")
_VERSION_ID = re.compile(r"[A-Za-z0-9._~:%+-]{1,256}\Z")
_TENANT_ID = re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\Z")
_SUBSCRIPTION_RESOURCE_ID = re.compile(
    r"/subscriptions/[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\Z"
)
_STORAGE_RESOURCE_ID = re.compile(
    r"/subscriptions/[0-9a-fA-F-]{36}/resourceGroups/[^/]{1,90}"
    r"/providers/Microsoft\.Storage/storageAccounts/[a-z0-9]{3,24}\Z"
)
_UTC_SECONDS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_RECEIPT_BODY = re.compile(r"[0-9a-f]{64}\Z")
_BINDING_128 = re.compile(r"[0-9a-f]{32}\Z")
_LOCK_ACTOR = re.compile(r"(?:operator|approver)-v1-[0-9a-f]{64}\Z")
_PROVIDER_CONTEXT_SOURCE = "azure-subscription-resource-tenant-readback"
_PROVIDER_ATTESTATION_SCHEMA = "nac.azure-provider-context-attestation/v0.1"
_PROVIDER_ATTESTATION_SOURCE = (
    "owner-approved-commit-hash-bound-deployment-attestation"
)
_LOCK_API_VERSION = "2023-05-01"
_LOCK_OPERATION = "POST immutabilityPolicies/default/lock"
_T = TypeVar("_T")
_NO_RESULT = object()


def build_azure_blob_worm_readiness() -> Mapping[str, Any]:
    return {
        "status": S6B_STATUS,
        "live_status": LIVE_STATUS,
        "scope": "OFFLINE_ONLY",
        "adapter": "AzureBlobWormJournal",
        "authoritative_evidence_copy": "azure_blob_immutable_storage",
        "publisher_location": "onprem",
        "minimum_retention_days": minimum_retention_days(MINIMUM_RETENTION_YEARS),
        "provider_context_binding_source": _PROVIDER_CONTEXT_SOURCE,
        "version_bound_receipts": True,
        "writer_delete_allowed": False,
        "irreversible_lock_status": "PREPARED_OFFLINE_NOT_EXECUTED",
        "bicep_compile_status": "CI_REQUIRED",
        "network_calls": 0,
        "provider_calls": 0,
        "tenant_writes": 0,
        "credential_reads": 0,
        "lock_actions": 0,
    }


class AzureBlobWormError(ValueError):
    """Stable public failure without provider, payload, or credential detail."""


class _Rejected(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AzureBlobProviderContext:
    tenant_id: str
    subscription_resource_id: str
    resource_id: str
    readback_source: str


@dataclass(frozen=True, slots=True)
class AzureProviderContextAttestation:
    schema_version: str
    source: str
    owner_approval_sha256: str
    deployment_commit_sha256: str
    deployment_tree_sha256: str
    deployment_plan_sha256: str
    provider_context_binding_sha256: str


@dataclass(frozen=True, slots=True)
class AzureBlobContainerPolicy:
    default_immutability_policy_mode: str
    default_retention_days: int
    legal_hold_capable: bool
    legal_hold_capability_source: str
    encryption_scope: str
    encryption_key_source: str
    customer_managed_key_ref_sha256: str
    provider_tenant_binding_sha256: str
    provider_subscription_binding_sha256: str
    provider_resource_binding_sha256: str
    provider_context_binding_sha256: str
    provider_context_binding_source: str


@dataclass(frozen=True, slots=True)
class AzureBlobPutResult:
    status_code: int
    etag: str | None
    version_id: str | None


@dataclass(frozen=True, slots=True)
class AzureBlobVersionItem:
    version_id: str


@dataclass(frozen=True, slots=True)
class AzureBlobObject:
    body: bytes
    metadata: Mapping[str, str]
    etag: str
    version_id: str
    created_at: str
    immutability_policy_mode: str
    retention_until: str
    legal_hold_active: bool
    encryption_scope: str
    encryption_key_source: str
    customer_managed_key_ref_sha256: str


@dataclass(frozen=True, slots=True)
class AzureBlobImmutabilityPolicySnapshot:
    target_resource_id_sha256: str
    provider_context_binding_sha256: str
    policy_resource_id_sha256: str
    policy_state: str
    retention_days: int
    etag: str


class AzureBlobWormTransport(Protocol):
    """Offline REST-shaped port; credentials and HTTP clients are out of scope."""

    def get_provider_context(
        self, container_name: str
    ) -> AzureBlobProviderContext: ...

    def get_container_policy(
        self, container_name: str
    ) -> AzureBlobContainerPolicy: ...

    def put_blob_if_absent(
        self,
        container_name: str,
        blob_name: str,
        body: bytes,
        metadata: Mapping[str, str],
        *,
        encryption_scope: str,
        if_none_match: str,
    ) -> AzureBlobPutResult: ...

    def list_blob_versions(
        self, container_name: str, blob_name: str
    ) -> tuple[AzureBlobVersionItem, ...]: ...

    def get_blob(
        self,
        container_name: str,
        blob_name: str,
        *,
        version_id: str,
    ) -> AzureBlobObject: ...


class AzureBlobWormJournal:
    """Offline-ready Azure Blob adapter behind the unchanged WORM port."""

    def __init__(
        self,
        *,
        transport: AzureBlobWormTransport,
        container_name: str,
        tenant_binding_sha256: str,
        encryption_scope: str,
        customer_managed_key_ref_sha256: str,
        provider_context_attestation: AzureProviderContextAttestation,
        approved_provider_context_attestation_sha256: str,
    ) -> None:
        try:
            self._transport = transport
            self._container_name = _azure_name(container_name)
            self._tenant_binding_sha256 = _sha256(tenant_binding_sha256)
            self._encryption_scope = _azure_name(encryption_scope)
            self._customer_managed_key_ref_sha256 = _sha256(
                customer_managed_key_ref_sha256
            )
            attestation = _copy_provider_context_attestation(
                provider_context_attestation
            )
            approved_attestation_sha256 = _sha256(
                approved_provider_context_attestation_sha256
            )
            actual_attestation_sha256 = _provider_context_attestation_sha256(
                attestation
            )
            if actual_attestation_sha256 != approved_attestation_sha256:
                raise _Rejected
            self._provider_context_attestation_sha256 = (
                approved_attestation_sha256
            )
            self._attested_provider_context_binding_sha256 = (
                attestation.provider_context_binding_sha256
            )
        except Exception:
            raise AzureBlobWormError(_PUBLIC_ERROR) from None

    def commit(
        self,
        records: tuple[EvidenceRecord, ...],
        anchor: Mapping[str, Any],
        *,
        idempotency_key_sha256: str,
    ) -> Mapping[str, Any]:
        failed = False
        result: Mapping[str, Any] | None = None
        try:
            result = self._commit(
                records,
                anchor,
                idempotency_key_sha256=idempotency_key_sha256,
            )
        except Exception:
            failed = True
        if failed or result is None:
            raise AzureBlobWormError(_PUBLIC_ERROR)
        return result

    def readback(self, receipt_ref: str) -> Mapping[str, Any]:
        failed = False
        result: Mapping[str, Any] | None = None
        try:
            result = self._readback(receipt_ref)
        except Exception:
            failed = True
        if failed or result is None:
            raise AzureBlobWormError(_PUBLIC_ERROR)
        return result

    def _commit(
        self,
        records: tuple[EvidenceRecord, ...],
        anchor: Mapping[str, Any],
        *,
        idempotency_key_sha256: str,
    ) -> Mapping[str, Any]:
        idempotency_key = _sha256(idempotency_key_sha256)
        safe_records = _copy_records(records)
        chain = verify_chain(safe_records)
        if chain.get("complete") is not True:
            raise _Rejected
        head_sha256 = safe_records[-1].event_sha256
        if idempotency_key != worm_commit_idempotency_key(head_sha256):
            raise _Rejected
        safe_anchor = _copy_json(anchor)
        _validate_anchor(safe_anchor, safe_records)

        retention_years = _preflight_records(
            safe_records,
            tenant_binding_sha256=self._tenant_binding_sha256,
        )
        required_retention_days = minimum_retention_days(retention_years)
        _retention_deadline(
            datetime.now(timezone.utc).replace(microsecond=0),
            required_retention_days,
        )
        provider_evidence = self._provider_evidence()
        policy = self._container_policy()
        self._validate_policy(
            policy,
            provider_evidence=provider_evidence,
            required_retention_days=required_retention_days,
        )

        blob_locator = _blob_locator(
            container_name=self._container_name,
            tenant_binding_sha256=self._tenant_binding_sha256,
            idempotency_key_sha256=idempotency_key,
        )
        envelope = {
            "schema_version": _SCHEMA_VERSION,
            "blob_locator": blob_locator,
            "idempotency_key_sha256": idempotency_key,
            "tenant_binding_sha256": self._tenant_binding_sha256,
            **provider_evidence,
            "provider_context_attestation_sha256": (
                self._provider_context_attestation_sha256
            ),
            "encryption_scope": self._encryption_scope,
            "encryption_key_source": policy.encryption_key_source,
            "customer_managed_key_ref_sha256": self._customer_managed_key_ref_sha256,
            "record_count": len(safe_records),
            "first_event_sha256": safe_records[0].event_sha256,
            "head_sha256": head_sha256,
            "retention_years": retention_years,
            "minimum_retention_days": required_retention_days,
            "legal_hold_capable": policy.legal_hold_capable,
            "legal_hold_capability_source": policy.legal_hold_capability_source,
            "anchor": safe_anchor,
            "records": [
                {"event": record.event, "event_sha256": record.event_sha256}
                for record in safe_records
            ],
        }
        body = canonical_json_bytes(envelope)
        if not body or len(body) > _MAX_BLOB_BYTES:
            raise _Rejected
        metadata = _metadata(envelope, body)
        blob_name = _blob_name(self._tenant_binding_sha256, blob_locator)

        put_result = _transport_call(
            lambda: _copy_put_result(
                self._transport.put_blob_if_absent(
                    self._container_name,
                    blob_name,
                    body,
                    metadata,
                    encryption_scope=self._encryption_scope,
                    if_none_match="*",
                )
            )
        )
        if put_result.status_code == 201:
            version_id = _version_id(put_result.version_id)
            receipt_ref = _receipt_ref(blob_locator, version_id)
            blob = self._get_blob(blob_name, version_id=version_id)
            self._validate_blob(
                blob,
                expected_receipt_ref=receipt_ref,
                expected_body=body,
                expected_version_id=version_id,
            )
        elif put_result.status_code == 412:
            receipt_ref = self._discover_conflict_version(
                blob_name=blob_name,
                blob_locator=blob_locator,
                expected_body=body,
            )
        else:
            raise _Rejected
        return {"receipt_ref": receipt_ref, "head_sha256": head_sha256}

    def _readback(self, receipt_ref: str) -> Mapping[str, Any]:
        receipt = _receipt(receipt_ref)
        blob_locator, version_binding = _receipt_parts(receipt)
        blob_name = _blob_name(self._tenant_binding_sha256, blob_locator)
        matching = [
            item.version_id
            for item in self._list_blob_versions(blob_name)
            if _version_binding(item.version_id) == version_binding
        ]
        if len(matching) != 1:
            raise _Rejected
        blob = self._get_blob(blob_name, version_id=matching[0])
        envelope, policy = self._validate_blob(
            blob,
            expected_receipt_ref=receipt,
            expected_version_id=matching[0],
        )
        return {
            "receipt_ref": receipt,
            "head_sha256": envelope["head_sha256"],
            "retention_years": policy.default_retention_days // 365,
            "legal_hold_capable": policy.legal_hold_capable,
        }

    def _discover_conflict_version(
        self,
        *,
        blob_name: str,
        blob_locator: str,
        expected_body: bytes,
    ) -> str:
        matches: list[str] = []
        for item in self._list_blob_versions(blob_name):
            version_id = item.version_id
            blob = self._get_blob(blob_name, version_id=version_id)
            receipt = _receipt_ref(blob_locator, version_id)
            try:
                self._validate_blob(
                    blob,
                    expected_receipt_ref=receipt,
                    expected_body=expected_body,
                    expected_version_id=version_id,
                )
            except _Rejected:
                continue
            matches.append(receipt)
        if len(matches) != 1:
            raise _Rejected
        return matches[0]

    def _provider_evidence(self) -> dict[str, str]:
        context = _transport_call(
            lambda: _copy_provider_context(
                self._transport.get_provider_context(self._container_name)
            )
        )
        evidence = _provider_context_evidence(context)
        if (
            evidence["provider_context_binding_sha256"]
            != self._attested_provider_context_binding_sha256
        ):
            raise _Rejected
        return evidence

    def _container_policy(self) -> AzureBlobContainerPolicy:
        return _transport_call(
            lambda: _copy_policy(
                self._transport.get_container_policy(self._container_name)
            )
        )

    def _list_blob_versions(
        self, blob_name: str
    ) -> tuple[AzureBlobVersionItem, ...]:
        return _transport_call(
            lambda: _copy_version_items(
                self._transport.list_blob_versions(
                    self._container_name, blob_name
                )
            )
        )

    def _get_blob(self, blob_name: str, *, version_id: str) -> AzureBlobObject:
        exact_version = _version_id(version_id)
        return _transport_call(
            lambda: _copy_blob(
                self._transport.get_blob(
                    self._container_name,
                    blob_name,
                    version_id=exact_version,
                )
            )
        )

    def _validate_policy(
        self,
        policy: AzureBlobContainerPolicy,
        *,
        provider_evidence: Mapping[str, str],
        required_retention_days: int,
    ) -> None:
        _retention_deadline(
            datetime.now(timezone.utc).replace(microsecond=0),
            policy.default_retention_days,
        )
        if (
            policy.default_immutability_policy_mode != "Locked"
            or policy.default_retention_days < required_retention_days
            or policy.legal_hold_capable is not True
            or policy.legal_hold_capability_source != "container-policy-properties"
            or policy.encryption_scope != self._encryption_scope
            or policy.encryption_key_source != "Microsoft.Keyvault"
            or policy.customer_managed_key_ref_sha256
            != self._customer_managed_key_ref_sha256
            or policy.provider_tenant_binding_sha256
            != provider_evidence["provider_tenant_binding_sha256"]
            or policy.provider_subscription_binding_sha256
            != provider_evidence["provider_subscription_binding_sha256"]
            or policy.provider_resource_binding_sha256
            != provider_evidence["provider_resource_binding_sha256"]
            or policy.provider_context_binding_sha256
            != provider_evidence["provider_context_binding_sha256"]
            or policy.provider_context_binding_source != _PROVIDER_CONTEXT_SOURCE
        ):
            raise _Rejected

    def _validate_blob(
        self,
        blob: AzureBlobObject,
        *,
        expected_receipt_ref: str,
        expected_body: bytes | None = None,
        expected_version_id: str,
    ) -> tuple[dict[str, Any], AzureBlobContainerPolicy]:
        version_id = _version_id(blob.version_id)
        blob_locator, receipt_version_binding = _receipt_parts(
            expected_receipt_ref
        )
        if (
            not blob.body
            or len(blob.body) > _MAX_BLOB_BYTES
            or version_id != _version_id(expected_version_id)
            or _version_binding(version_id) != receipt_version_binding
            or _receipt_ref(blob_locator, version_id) != expected_receipt_ref
            or (expected_body is not None and blob.body != expected_body)
            or blob.immutability_policy_mode != "Locked"
            or blob.encryption_scope != self._encryption_scope
            or blob.encryption_key_source != "Microsoft.Keyvault"
            or blob.customer_managed_key_ref_sha256
            != self._customer_managed_key_ref_sha256
        ):
            raise _Rejected
        created_at = _utc_datetime(blob.created_at)
        retention_until = _utc_datetime(blob.retention_until)
        try:
            envelope = json.loads(blob.body.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise _Rejected
        if canonical_json_bytes(envelope) != blob.body:
            raise _Rejected

        expected_fields = {
            "schema_version",
            "blob_locator",
            "idempotency_key_sha256",
            "tenant_binding_sha256",
            "provider_tenant_binding_sha256",
            "provider_subscription_binding_sha256",
            "provider_resource_binding_sha256",
            "provider_context_binding_sha256",
            "provider_context_binding_source",
            "provider_context_attestation_sha256",
            "encryption_scope",
            "encryption_key_source",
            "customer_managed_key_ref_sha256",
            "record_count",
            "first_event_sha256",
            "head_sha256",
            "retention_years",
            "minimum_retention_days",
            "legal_hold_capable",
            "legal_hold_capability_source",
            "anchor",
            "records",
        }
        if not isinstance(envelope, dict) or set(envelope) != expected_fields:
            raise _Rejected
        if (
            envelope["schema_version"] != _SCHEMA_VERSION
            or envelope["blob_locator"] != blob_locator
            or envelope["tenant_binding_sha256"] != self._tenant_binding_sha256
            or envelope["provider_context_attestation_sha256"]
            != self._provider_context_attestation_sha256
            or envelope["encryption_scope"] != self._encryption_scope
            or envelope["encryption_key_source"] != "Microsoft.Keyvault"
            or envelope["customer_managed_key_ref_sha256"]
            != self._customer_managed_key_ref_sha256
            or envelope["legal_hold_capable"] is not True
            or envelope["legal_hold_capability_source"]
            != "container-policy-properties"
        ):
            raise _Rejected
        provider_evidence = self._provider_evidence()
        if any(
            envelope[key] != value
            for key, value in provider_evidence.items()
        ):
            raise _Rejected

        idempotency_key = _sha256(envelope["idempotency_key_sha256"])
        if _blob_locator(
            container_name=self._container_name,
            tenant_binding_sha256=self._tenant_binding_sha256,
            idempotency_key_sha256=idempotency_key,
        ) != blob_locator:
            raise _Rejected
        raw_records = envelope["records"]
        if not isinstance(raw_records, list) or not raw_records:
            raise _Rejected
        records: list[EvidenceRecord] = []
        for item in raw_records:
            if not isinstance(item, dict) or set(item) != {
                "event",
                "event_sha256",
            }:
                raise _Rejected
            records.append(
                EvidenceRecord(
                    event=_copy_json(item["event"]),
                    event_sha256=_sha256(item["event_sha256"]),
                )
            )
        safe_records = tuple(records)
        chain = verify_chain(safe_records)
        head_sha256 = safe_records[-1].event_sha256
        retention_years = _preflight_records(
            safe_records,
            tenant_binding_sha256=self._tenant_binding_sha256,
        )
        required_retention_days = minimum_retention_days(retention_years)
        if (
            chain.get("complete") is not True
            or envelope["record_count"] != len(safe_records)
            or envelope["first_event_sha256"] != safe_records[0].event_sha256
            or envelope["head_sha256"] != head_sha256
            or idempotency_key != worm_commit_idempotency_key(head_sha256)
            or envelope["retention_years"] != retention_years
            or envelope["minimum_retention_days"] != required_retention_days
            or retention_until
            < _retention_deadline(created_at, required_retention_days)
        ):
            raise _Rejected
        _validate_anchor(envelope["anchor"], safe_records)
        if dict(blob.metadata) != _metadata(envelope, blob.body):
            raise _Rejected
        policy = self._container_policy()
        self._validate_policy(
            policy,
            provider_evidence=provider_evidence,
            required_retention_days=required_retention_days,
        )
        return envelope, policy


class FakeAzureBlobWormTransport:
    """Thread-safe Azure REST model with no network or credential I/O."""

    def __init__(
        self,
        *,
        container_name: str,
        tenant_binding_sha256: str,
        policy: AzureBlobContainerPolicy,
        provider_context: AzureBlobProviderContext,
    ) -> None:
        self._container_name = container_name
        self._tenant_binding_sha256 = _sha256(tenant_binding_sha256)
        self._policy = _copy_policy(policy)
        self._provider_context = _copy_provider_context(provider_context)
        self._blobs: dict[str, dict[str, AzureBlobObject]] = {}
        self._failures: dict[str, BaseException] = {}
        self._results: dict[str, object] = {}
        self._lose_put_response = False
        self._put_barrier: threading.Barrier | None = None
        self._lock = threading.RLock()
        self.put_calls = 0
        self.get_calls = 0
        self.list_versions_calls = 0
        self.policy_calls = 0
        self.provider_context_calls = 0
        self.create_effects = 0
        self.put_history: list[dict[str, str]] = []
        self.get_history: list[dict[str, str]] = []
        self.network_calls = 0
        self.azure_calls = 0
        self.credential_reads = 0

    def get_provider_context(
        self, container_name: str
    ) -> AzureBlobProviderContext:
        with self._lock:
            self.provider_context_calls += 1
            self._maybe_fail("get_provider_context")
            override = self._next_result("get_provider_context")
            if override is not _NO_RESULT:
                return override  # type: ignore[return-value]
            self._require_container(container_name)
            return _copy_provider_context(self._provider_context)

    def get_container_policy(
        self, container_name: str
    ) -> AzureBlobContainerPolicy:
        with self._lock:
            self.policy_calls += 1
            self._maybe_fail("get_container_policy")
            override = self._next_result("get_container_policy")
            if override is not _NO_RESULT:
                return override  # type: ignore[return-value]
            self._require_container(container_name)
            return _copy_policy(self._policy)

    def put_blob_if_absent(
        self,
        container_name: str,
        blob_name: str,
        body: bytes,
        metadata: Mapping[str, str],
        *,
        encryption_scope: str,
        if_none_match: str,
    ) -> AzureBlobPutResult:
        barrier = self._put_barrier
        if barrier is not None:
            try:
                barrier.wait(timeout=5)
            except threading.BrokenBarrierError as error:
                raise RuntimeError("synthetic put barrier failed") from error
            with self._lock:
                if self._put_barrier is barrier:
                    self._put_barrier = None
        with self._lock:
            self.put_calls += 1
            self.put_history.append(
                {
                    "container_name": str(container_name),
                    "blob_name": str(blob_name),
                    "if_none_match": str(if_none_match),
                }
            )
            self._maybe_fail("put_blob_if_absent")
            override = self._next_result("put_blob_if_absent")
            if override is not _NO_RESULT:
                return override  # type: ignore[return-value]
            self._require_container(container_name)
            if if_none_match != "*":
                raise RuntimeError("create-only precondition missing")
            if self._blobs.get(blob_name):
                return AzureBlobPutResult(
                    status_code=412,
                    etag=None,
                    version_id=None,
                )
            safe_body = bytes(body)
            created_at_dt = datetime.now(timezone.utc).replace(microsecond=0)
            created_at = _utc_text(created_at_dt)
            retention_until = _utc_text(
                _retention_deadline(
                    created_at_dt,
                    self._policy.default_retention_days,
                )
            )
            digest = hashlib.sha256(
                blob_name.encode("ascii") + b"\x00" + safe_body
            ).hexdigest()
            version_id = f"version-v1-{digest}"
            etag = '"' + hashlib.sha256(safe_body).hexdigest() + '"'
            blob = AzureBlobObject(
                body=safe_body,
                metadata={str(k): str(v) for k, v in metadata.items()},
                etag=etag,
                version_id=version_id,
                created_at=created_at,
                immutability_policy_mode=self._policy.default_immutability_policy_mode,
                retention_until=retention_until,
                legal_hold_active=False,
                encryption_scope=str(encryption_scope),
                encryption_key_source=self._policy.encryption_key_source,
                customer_managed_key_ref_sha256=(
                    self._policy.customer_managed_key_ref_sha256
                ),
            )
            self._blobs[str(blob_name)] = {version_id: blob}
            self.create_effects += 1
            if self._lose_put_response:
                self._lose_put_response = False
                raise RuntimeError("synthetic post-create response loss")
            return AzureBlobPutResult(
                status_code=201,
                etag=etag,
                version_id=version_id,
            )

    def list_blob_versions(
        self, container_name: str, blob_name: str
    ) -> tuple[AzureBlobVersionItem, ...]:
        with self._lock:
            self.list_versions_calls += 1
            self._maybe_fail("list_blob_versions")
            override = self._next_result("list_blob_versions")
            if override is not _NO_RESULT:
                return override  # type: ignore[return-value]
            self._require_container(container_name)
            versions = self._blobs.get(blob_name, {})
            return tuple(
                AzureBlobVersionItem(version_id=version_id)
                for version_id in sorted(versions)
            )

    def get_blob(
        self,
        container_name: str,
        blob_name: str,
        *,
        version_id: str,
    ) -> AzureBlobObject:
        with self._lock:
            self.get_calls += 1
            self.get_history.append(
                {"blob_name": str(blob_name), "version_id": str(version_id)}
            )
            self._maybe_fail("get_blob")
            override = self._next_result("get_blob")
            if override is not _NO_RESULT:
                return override  # type: ignore[return-value]
            self._require_container(container_name)
            return _copy_blob(self._blobs[blob_name][_version_id(version_id)])

    def fail_next(self, operation: str, error: BaseException) -> None:
        with self._lock:
            self._failures[str(operation)] = error

    def return_next(self, operation: str, result: object) -> None:
        with self._lock:
            self._results[str(operation)] = result

    def lose_next_put_response(self) -> None:
        with self._lock:
            self._lose_put_response = True

    def block_next_puts(self, parties: int) -> None:
        if type(parties) is not int or parties < 2:
            raise ValueError("put barrier requires at least two parties")
        with self._lock:
            self._put_barrier = threading.Barrier(parties)

    def replace_policy_for_test(self, policy: AzureBlobContainerPolicy) -> None:
        with self._lock:
            self._policy = _copy_policy(policy)

    def replace_provider_context_for_test(
        self, context: AzureBlobProviderContext
    ) -> None:
        with self._lock:
            self._provider_context = _copy_provider_context(context)

    def blob_snapshot(self, receipt_ref: str) -> AzureBlobObject:
        with self._lock:
            blob_locator, version_binding = _receipt_parts(receipt_ref)
            versions = self._blobs[
                _blob_name(self._tenant_binding_sha256, blob_locator)
            ]
            matches = [
                blob
                for version_id, blob in versions.items()
                if _version_binding(version_id) == version_binding
            ]
            if len(matches) != 1:
                raise RuntimeError("receipt version unavailable")
            return _copy_blob(matches[0])

    def replace_blob_for_test(
        self,
        receipt_ref: str,
        *,
        body: bytes | None = None,
        metadata: Mapping[str, str] | None = None,
        encryption_scope: str | None = None,
        encryption_key_source: str | None = None,
        customer_managed_key_ref_sha256: str | None = None,
        version_id: str | None = None,
        created_at: str | None = None,
        immutability_policy_mode: str | None = None,
        retention_until: str | None = None,
        legal_hold_active: object | None = None,
    ) -> None:
        with self._lock:
            blob_locator, version_binding = _receipt_parts(receipt_ref)
            name = _blob_name(self._tenant_binding_sha256, blob_locator)
            versions = self._blobs[name]
            keys = [
                key
                for key in versions
                if _version_binding(key) == version_binding
            ]
            if len(keys) != 1:
                raise RuntimeError("receipt version unavailable")
            old_key = keys[0]
            current = versions.pop(old_key)
            replacement_body = current.body if body is None else bytes(body)
            new_version = current.version_id if version_id is None else version_id
            versions[str(new_version)] = AzureBlobObject(
                body=replacement_body,
                metadata=(dict(current.metadata) if metadata is None else dict(metadata)),
                etag='"' + hashlib.sha256(replacement_body).hexdigest() + '"',
                version_id=str(new_version),
                created_at=current.created_at if created_at is None else str(created_at),
                immutability_policy_mode=(
                    current.immutability_policy_mode
                    if immutability_policy_mode is None
                    else str(immutability_policy_mode)
                ),
                retention_until=(
                    current.retention_until
                    if retention_until is None
                    else str(retention_until)
                ),
                legal_hold_active=(
                    current.legal_hold_active
                    if legal_hold_active is None
                    else legal_hold_active  # type: ignore[arg-type]
                ),
                encryption_scope=(
                    current.encryption_scope
                    if encryption_scope is None
                    else str(encryption_scope)
                ),
                encryption_key_source=(
                    current.encryption_key_source
                    if encryption_key_source is None
                    else str(encryption_key_source)
                ),
                customer_managed_key_ref_sha256=(
                    current.customer_managed_key_ref_sha256
                    if customer_managed_key_ref_sha256 is None
                    else str(customer_managed_key_ref_sha256)
                ),
            )

    def clone_blob_version_for_test(
        self, receipt_ref: str, *, version_id: str
    ) -> None:
        with self._lock:
            current = self.blob_snapshot(receipt_ref)
            blob_locator, _ = _receipt_parts(receipt_ref)
            name = _blob_name(self._tenant_binding_sha256, blob_locator)
            exact = _version_id(version_id)
            self._blobs[name][exact] = replace(current, version_id=exact)

    def replace_all_versions_with_foreign_for_test(
        self, receipt_ref: str, *, version_id: str
    ) -> None:
        with self._lock:
            current = self.blob_snapshot(receipt_ref)
            blob_locator, _ = _receipt_parts(receipt_ref)
            name = _blob_name(self._tenant_binding_sha256, blob_locator)
            exact = _version_id(version_id)
            foreign_metadata = dict(current.metadata)
            foreign_metadata["nac_head_sha256"] = "f" * 64
            self._blobs[name] = {
                exact: replace(
                    current,
                    version_id=exact,
                    metadata=foreign_metadata,
                )
            }

    def _require_container(self, container_name: str) -> None:
        if container_name != self._container_name:
            raise RuntimeError("container unavailable")

    def _maybe_fail(self, operation: str) -> None:
        error = self._failures.pop(operation, None)
        if error is not None:
            raise error

    def _next_result(self, operation: str) -> object:
        return self._results.pop(operation, _NO_RESULT)


def azure_provider_context_attestation_sha256(
    attestation: AzureProviderContextAttestation,
) -> str:
    try:
        return _provider_context_attestation_sha256(
            _copy_provider_context_attestation(attestation)
        )
    except Exception:
        raise AzureBlobWormError(_PUBLIC_ERROR) from None


def azure_provider_context_binding_sha256(
    context: AzureBlobProviderContext,
) -> str:
    try:
        return _provider_context_evidence(
            _copy_provider_context(context)
        )["provider_context_binding_sha256"]
    except Exception:
        raise AzureBlobWormError(_PUBLIC_ERROR) from None


def _provider_context_attestation_sha256(
    attestation: AzureProviderContextAttestation,
) -> str:
    payload = {
        "schema_version": attestation.schema_version,
        "source": attestation.source,
        "owner_approval_sha256": attestation.owner_approval_sha256,
        "deployment_commit_sha256": attestation.deployment_commit_sha256,
        "deployment_tree_sha256": attestation.deployment_tree_sha256,
        "deployment_plan_sha256": attestation.deployment_plan_sha256,
        "provider_context_binding_sha256": (
            attestation.provider_context_binding_sha256
        ),
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _provider_context_evidence(
    context: AzureBlobProviderContext,
) -> dict[str, str]:
    tenant = _provider_raw(context.tenant_id)
    if _TENANT_ID.fullmatch(tenant) is None:
        raise _Rejected
    subscription_id = _provider_resource_id(
        context.subscription_resource_id,
        require_storage=False,
    )
    resource_id = _provider_resource_id(
        context.resource_id,
        require_storage=True,
    )
    if not resource_id.startswith(subscription_id + "/"):
        raise _Rejected
    if context.readback_source != _PROVIDER_CONTEXT_SOURCE:
        raise _Rejected
    tenant_binding = _domain_hash("nac.azure-provider-tenant.v1", tenant)
    subscription_binding = _domain_hash(
        "nac.azure-subscription-resource.v1", subscription_id
    )
    resource_binding = _domain_hash("nac.azure-storage-resource.v1", resource_id)
    context_binding = hashlib.sha256(
        (
            "nac.azure-provider-context.v1|"
            + tenant_binding
            + "|"
            + subscription_binding
            + "|"
            + resource_binding
        ).encode("ascii")
    ).hexdigest()
    return {
        "provider_tenant_binding_sha256": tenant_binding,
        "provider_subscription_binding_sha256": subscription_binding,
        "provider_resource_binding_sha256": resource_binding,
        "provider_context_binding_sha256": context_binding,
        "provider_context_binding_source": _PROVIDER_CONTEXT_SOURCE,
    }


def _domain_hash(domain: str, value: str) -> str:
    return hashlib.sha256((domain + "|" + value).encode("ascii")).hexdigest()


def _provider_raw(value: Any) -> str:
    if type(value) is not str or not value or len(value) > 2048:
        raise _Rejected
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        raise _Rejected
    return value


def _provider_resource_id(value: Any, *, require_storage: bool) -> str:
    resource_id = _provider_raw(value)
    pattern = (
        _STORAGE_RESOURCE_ID if require_storage else _SUBSCRIPTION_RESOURCE_ID
    )
    if pattern.fullmatch(resource_id) is None:
        raise _Rejected
    return resource_id


def _transport_call(call: Callable[[], _T]) -> _T:
    try:
        result = call()
    except Exception:
        raise _Rejected
    if result is None:
        raise _Rejected
    return result


def _copy_provider_context_attestation(
    value: Any,
) -> AzureProviderContextAttestation:
    if (
        type(value) is not AzureProviderContextAttestation
        or value.schema_version != _PROVIDER_ATTESTATION_SCHEMA
        or value.source != _PROVIDER_ATTESTATION_SOURCE
    ):
        raise _Rejected
    return AzureProviderContextAttestation(
        schema_version=value.schema_version,
        source=value.source,
        owner_approval_sha256=_sha256(value.owner_approval_sha256),
        deployment_commit_sha256=_sha256(value.deployment_commit_sha256),
        deployment_tree_sha256=_sha256(value.deployment_tree_sha256),
        deployment_plan_sha256=_sha256(value.deployment_plan_sha256),
        provider_context_binding_sha256=_sha256(
            value.provider_context_binding_sha256
        ),
    )


def _copy_provider_context(value: Any) -> AzureBlobProviderContext:
    if (
        type(value) is not AzureBlobProviderContext
        or type(value.tenant_id) is not str
        or type(value.subscription_resource_id) is not str
        or type(value.resource_id) is not str
        or type(value.readback_source) is not str
    ):
        raise _Rejected
    return AzureBlobProviderContext(
        tenant_id=value.tenant_id,
        subscription_resource_id=value.subscription_resource_id,
        resource_id=value.resource_id,
        readback_source=value.readback_source,
    )


def _copy_put_result(value: Any) -> AzureBlobPutResult:
    if type(value) is not AzureBlobPutResult or type(value.status_code) is not int:
        raise _Rejected
    if value.status_code == 201:
        if type(value.etag) is not str or not value.etag:
            raise _Rejected
        version_id = _version_id(value.version_id)
        return AzureBlobPutResult(201, value.etag, version_id)
    if value.status_code == 412:
        if value.etag is not None or value.version_id is not None:
            raise _Rejected
        return AzureBlobPutResult(412, None, None)
    raise _Rejected


def _copy_version_items(value: Any) -> tuple[AzureBlobVersionItem, ...]:
    if type(value) is not tuple:
        raise _Rejected
    copied: list[AzureBlobVersionItem] = []
    seen: set[str] = set()
    for item in value:
        if type(item) is not AzureBlobVersionItem:
            raise _Rejected
        version_id = _version_id(item.version_id)
        if version_id in seen:
            raise _Rejected
        seen.add(version_id)
        copied.append(AzureBlobVersionItem(version_id))
    return tuple(copied)


def _copy_policy(value: Any) -> AzureBlobContainerPolicy:
    fields = (
        "default_immutability_policy_mode",
        "default_retention_days",
        "legal_hold_capable",
        "legal_hold_capability_source",
        "encryption_scope",
        "encryption_key_source",
        "customer_managed_key_ref_sha256",
        "provider_tenant_binding_sha256",
        "provider_subscription_binding_sha256",
        "provider_resource_binding_sha256",
        "provider_context_binding_sha256",
        "provider_context_binding_source",
    )
    if type(value) is not AzureBlobContainerPolicy:
        raise _Rejected
    if type(value.default_retention_days) is not int or type(value.legal_hold_capable) is not bool:
        raise _Rejected
    if any(type(getattr(value, field)) is not str for field in fields if field not in {"default_retention_days", "legal_hold_capable"}):
        raise _Rejected
    return replace(value)


def _copy_blob(value: Any) -> AzureBlobObject:
    if (
        type(value) is not AzureBlobObject
        or type(value.body) is not bytes
        or not isinstance(value.metadata, Mapping)
        or not all(type(k) is str and type(v) is str for k, v in value.metadata.items())
        or type(value.etag) is not str
        or not value.etag
        or type(value.version_id) is not str
        or type(value.created_at) is not str
        or type(value.immutability_policy_mode) is not str
        or type(value.retention_until) is not str
        or type(value.legal_hold_active) is not bool
        or type(value.encryption_scope) is not str
        or type(value.encryption_key_source) is not str
        or type(value.customer_managed_key_ref_sha256) is not str
    ):
        raise _Rejected
    return AzureBlobObject(
        body=bytes(value.body),
        metadata=dict(value.metadata),
        etag=value.etag,
        version_id=value.version_id,
        created_at=value.created_at,
        immutability_policy_mode=value.immutability_policy_mode,
        retention_until=value.retention_until,
        legal_hold_active=value.legal_hold_active,
        encryption_scope=value.encryption_scope,
        encryption_key_source=value.encryption_key_source,
        customer_managed_key_ref_sha256=value.customer_managed_key_ref_sha256,
    )


def _copy_records(
    records: tuple[EvidenceRecord, ...],
) -> tuple[EvidenceRecord, ...]:
    if type(records) is not tuple or not records:
        raise _Rejected
    copied: list[EvidenceRecord] = []
    for record in records:
        if type(record) is not EvidenceRecord:
            raise _Rejected
        copied.append(
            EvidenceRecord(
                event=_copy_json(record.event),
                event_sha256=_sha256(record.event_sha256),
            )
        )
    return tuple(copied)


def _copy_json(value: Any) -> Any:
    return json.loads(canonical_json_bytes(value).decode("ascii"))


def _preflight_records(
    records: tuple[EvidenceRecord, ...], *, tenant_binding_sha256: str
) -> int:
    expected_retention: int | None = None
    for record in records:
        event = record.event
        _utc_datetime(event.get("occurred_at"))
        retention = event.get("retention")
        if not isinstance(retention, Mapping):
            raise _Rejected
        years = retention.get("minimum_years")
        if type(years) is not int or retention.get("legal_hold_capable") is not True:
            raise _Rejected
        minimum_retention_days(years)
        if expected_retention is None:
            expected_retention = years
        if (
            years != expected_retention
            or event.get("tenant_binding_sha256") != tenant_binding_sha256
        ):
            raise _Rejected
    if expected_retention is None:
        raise _Rejected
    return expected_retention


def _retention_deadline(created_at: datetime, days: int) -> datetime:
    if type(days) is not int or days < 3653 or created_at.tzinfo is None:
        raise _Rejected
    try:
        return created_at + timedelta(days=days)
    except (OverflowError, ValueError):
        raise _Rejected


def _validate_anchor(
    anchor: Mapping[str, Any],
    records: tuple[EvidenceRecord, ...],
) -> None:
    if not isinstance(anchor, Mapping) or set(anchor) != {
        "anchor_ref",
        "signature_ref",
        "record_count",
        "first_event_sha256",
        "last_event_sha256",
        "head_sha256",
    }:
        raise _Rejected
    head = records[-1].event_sha256
    if (
        type(anchor["anchor_ref"]) is not str
        or _ANCHOR.fullmatch(anchor["anchor_ref"]) is None
        or type(anchor["signature_ref"]) is not str
        or _SIGNATURE.fullmatch(anchor["signature_ref"]) is None
        or anchor["record_count"] != len(records)
        or anchor["first_event_sha256"] != records[0].event_sha256
        or anchor["last_event_sha256"] != head
        or anchor["head_sha256"] != head
    ):
        raise _Rejected


def _metadata(envelope: Mapping[str, Any], body: bytes) -> dict[str, str]:
    fields = (
        "blob_locator",
        "idempotency_key_sha256",
        "tenant_binding_sha256",
        "provider_tenant_binding_sha256",
        "provider_subscription_binding_sha256",
        "provider_resource_binding_sha256",
        "provider_context_binding_sha256",
        "provider_context_binding_source",
        "provider_context_attestation_sha256",
        "encryption_scope",
        "encryption_key_source",
        "customer_managed_key_ref_sha256",
        "record_count",
        "first_event_sha256",
        "head_sha256",
        "retention_years",
        "minimum_retention_days",
        "legal_hold_capable",
        "legal_hold_capability_source",
    )
    result = {"nac_schema_version": _SCHEMA_VERSION}
    for field in fields:
        value = envelope[field]
        if type(value) is bool:
            rendered = "true" if value else "false"
        else:
            rendered = str(value)
        result["nac_" + field] = rendered
    result["nac_body_sha256"] = hashlib.sha256(body).hexdigest()
    return result


def minimum_retention_days(retention_years: int) -> int:
    if type(retention_years) is not int or retention_years < MINIMUM_RETENTION_YEARS:
        raise _Rejected
    return (retention_years * 1461 + 3) // 4


def worm_commit_idempotency_key(chain_head_sha256: str) -> str:
    return _publication_operation_key("worm-commit", _sha256(chain_head_sha256))
def prepare_irreversible_lock_plan(
    pre_readback: AzureBlobImmutabilityPolicySnapshot,
    *,
    operator_ref: str,
    approver_ref: str,
) -> Mapping[str, Any]:
    failed = False
    result: Mapping[str, Any] | None = None
    try:
        result = _prepare_irreversible_lock_plan(
            pre_readback,
            operator_ref=operator_ref,
            approver_ref=approver_ref,
        )
    except Exception:
        failed = True
    if failed or result is None:
        raise AzureBlobWormError(_PUBLIC_ERROR)
    return result


def verify_irreversible_lock_evidence(
    plan: Mapping[str, Any],
    pre_readback: AzureBlobImmutabilityPolicySnapshot,
    post_readback: AzureBlobImmutabilityPolicySnapshot,
) -> Mapping[str, Any]:
    failed = False
    result: Mapping[str, Any] | None = None
    try:
        result = _verify_irreversible_lock_evidence(
            plan,
            pre_readback,
            post_readback,
        )
    except Exception:
        failed = True
    if failed or result is None:
        raise AzureBlobWormError(_PUBLIC_ERROR)
    return result


def _prepare_irreversible_lock_plan(
    pre_readback: AzureBlobImmutabilityPolicySnapshot,
    *,
    operator_ref: str,
    approver_ref: str,
) -> Mapping[str, Any]:
    pre = _copy_policy_snapshot(pre_readback)
    operator = _lock_actor(operator_ref, "operator")
    approver = _lock_actor(approver_ref, "approver")
    if (
        pre.policy_state != "Unlocked"
        or pre.retention_days < minimum_retention_days(10)
        or operator.removeprefix("operator-v1-")
        == approver.removeprefix("approver-v1-")
    ):
        raise _Rejected
    request = {
        "schema_version": "nac.azure-blob-worm-lock-request/v0.1",
        "operation_exact": _LOCK_OPERATION,
        "api_version_exact": _LOCK_API_VERSION,
        "target_resource_id_sha256": pre.target_resource_id_sha256,
        "provider_context_binding_sha256": (
            pre.provider_context_binding_sha256
        ),
        "policy_resource_id_sha256": pre.policy_resource_id_sha256,
        "if_match_etag": pre.etag,
        "retention_days": pre.retention_days,
    }
    request_hash = hashlib.sha256(canonical_json_bytes(request)).hexdigest()
    return {
        "schema_version": "nac.azure-blob-worm-lock-plan/v0.1",
        "request": request,
        "prepared_request_sha256": request_hash,
        "operator_ref": operator,
        "approver_ref": approver,
        "dual_control_verified": True,
        "execution_performed": False,
    }


def _verify_irreversible_lock_evidence(
    plan: Mapping[str, Any],
    pre_readback: AzureBlobImmutabilityPolicySnapshot,
    post_readback: AzureBlobImmutabilityPolicySnapshot,
) -> Mapping[str, Any]:
    safe_plan = _copy_json(plan)
    if not isinstance(safe_plan, dict) or set(safe_plan) != {
        "schema_version",
        "request",
        "prepared_request_sha256",
        "operator_ref",
        "approver_ref",
        "dual_control_verified",
        "execution_performed",
    }:
        raise _Rejected
    expected_plan = _prepare_irreversible_lock_plan(
        pre_readback,
        operator_ref=safe_plan.get("operator_ref"),
        approver_ref=safe_plan.get("approver_ref"),
    )
    if safe_plan != expected_plan:
        raise _Rejected
    pre = _copy_policy_snapshot(pre_readback)
    post = _copy_policy_snapshot(post_readback)
    if (
        post.target_resource_id_sha256 != pre.target_resource_id_sha256
        or post.provider_context_binding_sha256
        != pre.provider_context_binding_sha256
        or post.policy_resource_id_sha256
        != pre.policy_resource_id_sha256
        or post.policy_state != "Locked"
        or post.retention_days < pre.retention_days
        or post.etag == pre.etag
    ):
        raise _Rejected
    return {
        "schema_version": "nac.azure-blob-worm-lock-evidence/v0.1",
        "target_resource_id_sha256": pre.target_resource_id_sha256,
        "provider_context_binding_sha256": (
            pre.provider_context_binding_sha256
        ),
        "policy_resource_id_sha256": pre.policy_resource_id_sha256,
        "prepared_request_sha256": safe_plan[
            "prepared_request_sha256"
        ],
        "operator_ref": safe_plan["operator_ref"],
        "approver_ref": safe_plan["approver_ref"],
        "pre_readback_sha256": _snapshot_sha256(pre),
        "post_readback_sha256": _snapshot_sha256(post),
        "result": "LOCKED_READBACK_VERIFIED",
    }


def _copy_policy_snapshot(
    value: Any,
) -> AzureBlobImmutabilityPolicySnapshot:
    if (
        type(value) is not AzureBlobImmutabilityPolicySnapshot
        or type(value.target_resource_id_sha256) is not str
        or type(value.provider_context_binding_sha256) is not str
        or type(value.policy_resource_id_sha256) is not str
        or type(value.policy_state) is not str
        or type(value.retention_days) is not int
        or type(value.etag) is not str
        or not value.etag
    ):
        raise _Rejected
    return AzureBlobImmutabilityPolicySnapshot(
        target_resource_id_sha256=_sha256(
            value.target_resource_id_sha256
        ),
        provider_context_binding_sha256=_sha256(
            value.provider_context_binding_sha256
        ),
        policy_resource_id_sha256=_sha256(
            value.policy_resource_id_sha256
        ),
        policy_state=value.policy_state,
        retention_days=value.retention_days,
        etag=value.etag,
    )


def _snapshot_sha256(
    value: AzureBlobImmutabilityPolicySnapshot,
) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            {
                "target_resource_id_sha256": (
                    value.target_resource_id_sha256
                ),
                "provider_context_binding_sha256": (
                    value.provider_context_binding_sha256
                ),
                "policy_resource_id_sha256": (
                    value.policy_resource_id_sha256
                ),
                "policy_state": value.policy_state,
                "retention_days": value.retention_days,
                "etag": value.etag,
            }
        )
    ).hexdigest()


def _lock_actor(value: Any, kind: str) -> str:
    if (
        type(value) is not str
        or _LOCK_ACTOR.fullmatch(value) is None
        or not value.startswith(f"{kind}-v1-")
    ):
        raise _Rejected
    return value
def _utc_datetime(value: Any) -> datetime:
    if type(value) is not str or _UTC_SECONDS.fullmatch(value) is None:
        raise _Rejected
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        raise _Rejected


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise _Rejected
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _version_id(value: Any) -> str:
    if type(value) is not str or _VERSION_ID.fullmatch(value) is None:
        raise _Rejected
    return value


def _blob_locator(
    *,
    container_name: str,
    tenant_binding_sha256: str,
    idempotency_key_sha256: str,
) -> str:
    digest = hashlib.sha256(
        canonical_json_bytes(
            {
                "schema_version": "nac.azure-blob-worm-locator/v0.1",
                "container_name": _azure_name(container_name),
                "tenant_binding_sha256": _sha256(
                    tenant_binding_sha256
                ),
                "idempotency_key_sha256": _sha256(
                    idempotency_key_sha256
                ),
            }
        )
    ).hexdigest()
    return digest[:32]


def _binding_128(value: Any) -> str:
    if type(value) is not str or _BINDING_128.fullmatch(value) is None:
        raise _Rejected
    return value


def _version_binding(version_id: str) -> str:
    digest = hashlib.sha256(
        b"nac.azure-blob-version-binding.v1\x00"
        + _version_id(version_id).encode("ascii")
    ).hexdigest()
    return digest[:32]


def _receipt_ref(blob_locator: str, version_id: str) -> str:
    locator = _binding_128(blob_locator)
    return f"worm-receipt-v1-{locator}{_version_binding(version_id)}"


def _receipt_parts(receipt_ref: str) -> tuple[str, str]:
    receipt = _receipt(receipt_ref)
    body = receipt.removeprefix("worm-receipt-v1-")
    if _RECEIPT_BODY.fullmatch(body) is None:
        raise _Rejected
    return _binding_128(body[:32]), _binding_128(body[32:])


def worm_receipt_version_binding(receipt_ref: str) -> str:
    return _receipt_parts(receipt_ref)[1]


def _blob_name(tenant_binding_sha256: str, blob_locator: str) -> str:
    tenant = _sha256(tenant_binding_sha256)
    locator = _binding_128(blob_locator)
    return f"tenant/{tenant}/journal/commit-v1-{locator}.json"


def _sha256(value: Any) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _Rejected
    return value


def _receipt(value: Any) -> str:
    if type(value) is not str or _RECEIPT.fullmatch(value) is None:
        raise _Rejected
    return value


def _azure_name(value: Any) -> str:
    if type(value) is not str or _AZURE_NAME.fullmatch(value) is None:
        raise _Rejected
    return value
