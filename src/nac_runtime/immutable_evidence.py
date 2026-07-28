from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
import weakref
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Literal, Mapping, Protocol, TypeVar
from uuid import UUID


EvidencePhase = Literal[
    "intent",
    "outcome",
    "readback",
    "reconciliation_required",
    "reconciliation_closed",
]

PHASES: tuple[EvidencePhase, ...] = (
    "intent",
    "outcome",
    "readback",
    "reconciliation_required",
    "reconciliation_closed",
)
_NORMAL_PHASE_ORDER = ("intent", "outcome", "readback")
_RECONCILIATION_PHASE_ORDERS = (
    (
        "intent",
        "outcome",
        "reconciliation_required",
        "readback",
        "reconciliation_closed",
    ),
    (
        "intent",
        "outcome",
        "readback",
        "reconciliation_required",
        "readback",
        "reconciliation_closed",
    ),
    (
        "intent",
        "outcome",
        "reconciliation_required",
        "readback",
        "reconciliation_closed",
        "readback",
        "reconciliation_closed",
    ),
)
_LEGAL_PHASE_ORDERS = (_NORMAL_PHASE_ORDER, *_RECONCILIATION_PHASE_ORDERS)
MUTATION_ACTIONS = frozenset(
    {"schema_apply", "backfill", "correction", "cutover", "rollback"}
)
S6_STATUS = "S6_OFFLINE_FOUNDATION"
LIVE_STATUS = "BLOCKED_PENDING_S7_APPROVAL"
MINIMUM_RETENTION_YEARS = 10
ZERO_HASH = "0" * 64

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTIFIER = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_ACTOR_REF = re.compile(r"actor-v1-k[0-9]+-[0-9a-f]{64}\Z")
_PRINCIPAL_REF = re.compile(r"principal-v1-[0-9a-f]{64}\Z")
_CLAIM_REF = re.compile(r"claim-v1-[0-9a-f]{64}\Z")
_CORRELATION_REF = re.compile(r"correlation-v1-k[0-9]+-[0-9a-f]{64}\Z")
_TOOL_ID = re.compile(r"tool-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_ROLE_ID = re.compile(r"role-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_BUSINESS_CASE_TYPE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_CATALOG_VERSION = _SHA256
_UTC_SECONDS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_RAW_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_SUCCESS_OUTCOME_CODES = frozenset({"confirmed"})
_UNCERTAIN_OUTCOME_CODE = "write-state-uncertain"
_SUCCESS_READBACK_CODES = frozenset({"confirmed", "verified"})
_RECONCILIATION_REASONS = frozenset(
    {"readback-missing", "provider-readback-required", "evidence-publication-incomplete"}
)
REGISTERED_TOOL_IDS = frozenset(
    {
        "tool-nac-cli",
        "tool-nac-kg-business-case-type-evidence",
        "tool-nac-kg-business-case-type-migration",
    }
)
REGISTERED_ROLE_IDS = frozenset(
    {"role-migration-operator", "role-automation", "role-migration-reviewer"}
)
REGISTERED_BUSINESS_CASE_TYPE_IDS = frozenset(
    {
        "adoption-familienrechtliche-erklaerungen",
        "bautraegervertrag",
        "ehevertrag-scheidungsfolgenvereinbarung",
        "erbausschlagung",
        "erbscheinsantrag-nachlass",
        "geschaeftsanteilsuebertragung-gmbh",
        "gesellschafterbeschluss-gmbh-ug",
        "grundschuld-hypothekenbestellung",
        "handelsregisteranmeldung",
        "immobilienkaufvertrag",
        "loeschungsbewilligung-grundbuchloeschung",
        "online-gmbh-gruendung",
        "pflichtteilsverzicht-erbverzicht",
        "schenkungsvertrag-uebertragungsvertrag",
        "teilungserklaerung-weg",
        "testament-erbvertrag",
        "unterschriftsbeglaubigung",
        "vereinsregisteranmeldung",
        "vollmacht-immobilien-gesellschaftsgeschaefte",
        "vorsorgevollmacht-patientenverfuegung",
    }
)
REGISTERED_CATALOG_VERSIONS = frozenset(
    {"fcf1c7ba1a35980f5f1d371381ae5c218cd3ce94372f2c1df821f2ad40d2fab0"}
)
ETAG_KEYS = frozenset({"matter", "registry", "process", "task", "deadline"})
_BROKER_ACK_REF = re.compile(r"broker-ack-v1-[0-9a-f]{64}\Z")
_ANCHOR_REF = re.compile(r"anchor-v1-[0-9a-f]{64}\Z")
_SIGNATURE_REF = re.compile(r"signature-v1-[0-9a-f]{64}\Z")
_WORM_RECEIPT_REF = re.compile(r"worm-receipt-v1-[0-9a-f]{64}\Z")
_FORBIDDEN_KEYS = frozenset(
    {
        "actor_object_id",
        "entra_object_id",
        "tenant_id",
        "actor_id",
        "user_id",
        "object_id",
        "owner_id",
        "private_key",
        "client_secret",
        "access_token",
        "refresh_token",
        "raw_payload",
        "document_content",
        "aktenzeichen",
        "mandatsdaten",
    }
)


class ImmutableEvidenceError(ValueError):
    """Raised when immutable evidence cannot be accepted without guessing."""


class _ReconciliationStateError(ImmutableEvidenceError):
    """Sanitized state-machine conflict produced by a trusted adapter."""


class _PortFailure(RuntimeError):
    """Redacted external-port failure; original provider detail is discarded."""


_TRUSTED_RECONCILIATION_STATE_ERRORS = frozenset(
    {
        "evidence publication is blocked by reconciliation",
        "publication chain head does not match persisted state",
        "publication security binding does not match persisted state",
        "evidence publication already has an active claim",
    }
)


_T = TypeVar("_T")


def _materialize_external_value(value: Any) -> Any:
    if isinstance(value, EvidenceRecord):
        return EvidenceRecord(
            event=_materialize_external_value(value.event),
            event_sha256=_materialize_external_value(value.event_sha256),
        )
    if isinstance(value, Mapping):
        return {
            _materialize_external_value(key): _materialize_external_value(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(_materialize_external_value(item) for item in value)
    if isinstance(value, list):
        return [_materialize_external_value(item) for item in value]
    if isinstance(value, str):
        return str(value)
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if value is None:
        return None
    if isinstance(value, Iterable):
        return tuple(_materialize_external_value(item) for item in value)
    raise TypeError("unsupported external value")


def _provider_call(call: Callable[[], _T]) -> _T:
    failed = False
    result: Any = None
    try:
        result = _materialize_external_value(call())
    except Exception:
        failed = True
    if failed:
        raise _PortFailure
    return result


def _store_call(call: Callable[[], _T]) -> _T:
    trusted_message: str | None = None
    failed = False
    result: Any = None
    try:
        result = _materialize_external_value(call())
    except _ReconciliationStateError as exc:
        if (
            type(exc) is _ReconciliationStateError
            and len(exc.args) == 1
            and type(exc.args[0]) is str
            and exc.args[0] in _TRUSTED_RECONCILIATION_STATE_ERRORS
        ):
            trusted_message = exc.args[0]
        else:
            failed = True
    except Exception:
        failed = True
    if trusted_message is not None:
        raise _ReconciliationStateError(trusted_message)
    if failed:
        raise _PortFailure
    return result


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    event: dict[str, Any]
    event_sha256: str


class OutboxPort(Protocol):
    def append(self, event: Mapping[str, Any]) -> EvidenceRecord: ...

    def records(self, correlation_id: str) -> tuple[EvidenceRecord, ...]: ...


class BrokerPort(Protocol):
    def publish(self, record: EvidenceRecord) -> Mapping[str, Any]: ...


class SignatureAnchorPort(Protocol):
    def anchor(
        self,
        records: tuple[EvidenceRecord, ...],
        *,
        idempotency_key_sha256: str,
    ) -> Mapping[str, Any]: ...

    def readback(self, anchor_ref: str) -> Mapping[str, Any]: ...


class WormJournalPort(Protocol):
    def commit(
        self,
        records: tuple[EvidenceRecord, ...],
        anchor: Mapping[str, Any],
        *,
        idempotency_key_sha256: str,
    ) -> Mapping[str, Any]: ...

    def readback(self, receipt_ref: str) -> Mapping[str, Any]: ...


class ReconciliationStorePort(Protocol):
    def claim_publication(
        self,
        correlation_id: str,
        chain_head_sha256: str,
        *,
        claim_id: str,
        tenant_binding_sha256: str,
        principal_key_binding_sha256: str,
        event_sha256s: tuple[str, ...],
    ) -> Mapping[str, Any]: ...

    def advance_publication(
        self,
        correlation_id: str,
        *,
        claim_id: str,
        publication_progress: Mapping[str, Any],
    ) -> None: ...

    def complete_publication(
        self,
        correlation_id: str,
        *,
        claim_id: str,
        result: Mapping[str, Any],
    ) -> None: ...

    def authorize_publication_retry(
        self,
        correlation_id: str,
        *,
        operator_ref: str,
        approver_ref: str,
    ) -> None: ...

    def require(
        self,
        correlation_id: str,
        reason_code: str,
        chain_head_sha256: str,
        *,
        claim_id: str | None = None,
        publication_progress: Mapping[str, Any] | None = None,
        tenant_binding_sha256: str | None = None,
        principal_key_binding_sha256: str | None = None,
        event_sha256s: tuple[str, ...] | None = None,
    ) -> None: ...

    def close(
        self,
        correlation_id: str,
        *,
        records: tuple[EvidenceRecord, ...],
        operator_ref: str,
        approver_ref: str,
    ) -> None: ...

    def is_required(self, correlation_id: str) -> bool: ...


_ACTOR_REF_FACTORY_TOKEN = object()
_CORRELATION_REF_FACTORY_TOKEN = object()
_EVIDENCE_EVENT_FACTORY_TOKEN = object()
_IDENTIFIER_REGISTRY_FACTORY_TOKEN = object()
_AUTHORITY_ENTRY = tuple[Any, ...]
_ACTOR_REF_AUTHORITY: dict[int, _AUTHORITY_ENTRY] = {}
_CORRELATION_REF_AUTHORITY: dict[int, _AUTHORITY_ENTRY] = {}
_EVIDENCE_EVENT_AUTHORITY: dict[int, _AUTHORITY_ENTRY] = {}
_IDENTIFIER_REGISTRY_AUTHORITY: dict[int, _AUTHORITY_ENTRY] = {}


def _bind_authority(
    registry: dict[int, _AUTHORITY_ENTRY],
    instance: Any,
    *metadata: Any,
) -> None:
    object_id = id(instance)

    def release(reference: weakref.ReferenceType[Any]) -> None:
        current = registry.get(object_id)
        if current is not None and current[0] is reference:
            registry.pop(object_id, None)

    reference = weakref.ref(instance, release)
    registry[object_id] = (reference, *metadata)


def _authority(
    registry: dict[int, _AUTHORITY_ENTRY],
    instance: Any,
    authority_name: str,
) -> _AUTHORITY_ENTRY:
    authority = registry.get(id(instance))
    if authority is None or authority[0]() is not instance:
        raise ImmutableEvidenceError(f"{authority_name} authority is unavailable")
    return authority


@dataclass(frozen=True, slots=True, weakref_slot=True)
class TypedIdentifierRegistry:
    business_case_type_ids: frozenset[str]
    catalog_versions: frozenset[str]
    _factory_token: object

    def __getattribute__(self, name: str) -> Any:
        indexes = {
            "business_case_type_ids": 1,
            "catalog_versions": 2,
            "_factory_token": 3,
        }
        if name in indexes:
            authority = _authority(
                _IDENTIFIER_REGISTRY_AUTHORITY,
                self,
                "identifier registry",
            )
            return authority[indexes[name]]
        return object.__getattribute__(self, name)


def typed_identifier_registry(
    *,
    business_case_type_ids: Iterable[str],
    catalog_versions: Iterable[str],
) -> TypedIdentifierRegistry:
    case_types = frozenset(
        _pattern_identifier(
            value,
            "business_case_type_id",
            _BUSINESS_CASE_TYPE_ID,
        )
        for value in business_case_type_ids
    )
    versions = frozenset(
        _sha256(value, "catalog_version")
        for value in catalog_versions
    )
    if (
        case_types != REGISTERED_BUSINESS_CASE_TYPE_IDS
        or versions != REGISTERED_CATALOG_VERSIONS
    ):
        raise ImmutableEvidenceError(
            "typed identifier registry must exactly match the S3 catalog"
        )
    registry = TypedIdentifierRegistry(
        business_case_type_ids=case_types,
        catalog_versions=versions,
        _factory_token=_IDENTIFIER_REGISTRY_FACTORY_TOKEN,
    )
    _bind_authority(
        _IDENTIFIER_REGISTRY_AUTHORITY,
        registry,
        case_types,
        versions,
        _IDENTIFIER_REGISTRY_FACTORY_TOKEN,
    )
    return registry


class _VerifiedActorRef(str):
    def __new__(
        cls,
        value: str,
        factory_token: object,
        principal_ref: str,
        tenant_binding_sha256: str,
        principal_key_binding_sha256: str,
    ) -> "_VerifiedActorRef":
        if factory_token is not _ACTOR_REF_FACTORY_TOKEN:
            raise ImmutableEvidenceError("ActorRef must be created by actor_ref")
        instance = str.__new__(cls, value)
        object.__setattr__(instance, "_sealed", False)
        object.__setattr__(
            instance, "_principal_ref", _principal_ref(principal_ref, "principal_ref")
        )
        object.__setattr__(
            instance,
            "_tenant_binding_sha256",
            _sha256(tenant_binding_sha256, "tenant_binding_sha256"),
        )
        object.__setattr__(
            instance,
            "_principal_key_binding_sha256",
            _sha256(
                principal_key_binding_sha256,
                "principal_key_binding_sha256",
            ),
        )
        object.__setattr__(instance, "_sealed", True)
        _bind_authority(
            _ACTOR_REF_AUTHORITY,
            instance,
            _principal_ref(principal_ref, "principal_ref"),
            _sha256(tenant_binding_sha256, "tenant_binding_sha256"),
            _sha256(
                principal_key_binding_sha256,
                "principal_key_binding_sha256",
            ),
        )
        return instance

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("verified ActorRef metadata is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("verified ActorRef metadata is immutable")

    def __getattribute__(self, name: str) -> Any:
        if name == "__dict__":
            raise AttributeError("verified ActorRef metadata is private")
        indexes = {
            "_principal_ref": 1,
            "_tenant_binding_sha256": 2,
            "_principal_key_binding_sha256": 3,
        }
        if name in indexes:
            authority = _authority(
                _ACTOR_REF_AUTHORITY, self, "ActorRef"
            )
            return authority[indexes[name]]
        return str.__getattribute__(self, name)


class _VerifiedCorrelationRef(str):
    def __new__(
        cls,
        value: str,
        factory_token: object,
        tenant_binding_sha256: str,
    ) -> "_VerifiedCorrelationRef":
        if factory_token is not _CORRELATION_REF_FACTORY_TOKEN:
            raise ImmutableEvidenceError(
                "CorrelationRef must be created by correlation_ref"
            )
        instance = str.__new__(cls, value)
        object.__setattr__(instance, "_sealed", False)
        object.__setattr__(
            instance,
            "_tenant_binding_sha256",
            _sha256(tenant_binding_sha256, "tenant_binding_sha256"),
        )
        object.__setattr__(instance, "_sealed", True)
        _bind_authority(
            _CORRELATION_REF_AUTHORITY,
            instance,
            _sha256(tenant_binding_sha256, "tenant_binding_sha256"),
        )
        return instance

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("verified CorrelationRef metadata is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("verified CorrelationRef metadata is immutable")

    def __getattribute__(self, name: str) -> Any:
        if name == "__dict__":
            raise AttributeError("verified CorrelationRef metadata is private")
        if name == "_tenant_binding_sha256":
            authority = _authority(
                _CORRELATION_REF_AUTHORITY, self, "CorrelationRef"
            )
            return authority[1]
        return str.__getattribute__(self, name)


class _VerifiedEvidenceEvent(dict[str, Any]):
    __slots__ = (
        "_factory_token", "_payload_sha256", "_sealed", "__weakref__"
    )

    def __init__(
        self,
        value: Mapping[str, Any],
        factory_token: object,
        payload_sha256: str,
    ) -> None:
        if factory_token is not _EVIDENCE_EVENT_FACTORY_TOKEN:
            raise ImmutableEvidenceError("event must be created by build_event")
        super().__init__(value)
        object.__setattr__(self, "_factory_token", factory_token)
        object.__setattr__(
            self, "_payload_sha256", _sha256(payload_sha256, "payload_sha256")
        )
        object.__setattr__(self, "_sealed", True)
        _bind_authority(
            _EVIDENCE_EVENT_AUTHORITY,
            self,
            factory_token,
            _sha256(payload_sha256, "payload_sha256"),
        )

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("verified event metadata is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("verified event metadata is immutable")

    def __getattribute__(self, name: str) -> Any:
        indexes = {"_factory_token": 1, "_payload_sha256": 2}
        if name in indexes:
            authority = _authority(
                _EVIDENCE_EVENT_AUTHORITY, self, "event"
            )
            return authority[indexes[name]]
        return dict.__getattribute__(self, name)


class ImmutableEvidencePublisher:
    """Port orchestrator; durability depends entirely on injected production ports."""

    def __init__(
        self,
        *,
        outbox: OutboxPort,
        broker: BrokerPort,
        signature_anchor: SignatureAnchorPort,
        worm_journal: WormJournalPort,
        reconciliation_store: ReconciliationStorePort,
    ) -> None:
        self._outbox = outbox
        self._broker = broker
        self._signature_anchor = signature_anchor
        self._worm_journal = worm_journal
        self._reconciliation_store = reconciliation_store

    def finalize(self, correlation_id: str) -> dict[str, Any]:
        correlation = _trusted_correlation_ref(correlation_id, "correlation_id")
        records: tuple[EvidenceRecord, ...] = ()
        chain_head = ZERO_HASH
        initial_progress: dict[str, Any] = {
            "stage": "outbox-snapshot",
            "acknowledged_event_sha256s": [],
            "anchor_ref_sha256": None,
            "signature_ref_sha256": None,
            "worm_receipt_ref_sha256": None,
        }
        try:
            def load_snapshot() -> tuple[
                tuple[EvidenceRecord, ...], dict[str, Any]
            ]:
                snapshot_records = _copy_records(
                    self._outbox.records(correlation)
                )
                return snapshot_records, verify_chain(snapshot_records)

            records, status = _provider_call(load_snapshot)
            chain_head = records[-1].event_sha256 if records else ZERO_HASH
            if status["correlation_id"] != correlation:
                raise ImmutableEvidenceError(
                    "evidence chain correlation does not match request"
                )
            if status["complete"] is not True:
                raise ImmutableEvidenceError("evidence chain is incomplete")
        except Exception as exc:
            try:
                _store_call(
                    lambda: self._reconciliation_store.require(
                        correlation,
                        "evidence-publication-incomplete",
                        chain_head,
                        publication_progress=initial_progress,
                        tenant_binding_sha256=(
                            records[0].event["tenant_binding_sha256"]
                            if records
                            else None
                        ),
                        principal_key_binding_sha256=(
                            records[0].event[
                                "principal_key_binding_sha256"
                            ]
                            if records
                            else None
                        ),
                        event_sha256s=tuple(
                            record.event_sha256 for record in records
                        ),
                    )
                )
            except Exception:
                raise ImmutableEvidenceError(
                    "evidence publication state is unavailable"
                ) from None
            if isinstance(exc, ImmutableEvidenceError):
                raise
            raise ImmutableEvidenceError(
                "evidence publication requires reconciliation"
            ) from None

        claim_id = "claim-v1-" + secrets.token_hex(32)
        try:
            claim = _store_call(
                lambda: self._reconciliation_store.claim_publication(
                    correlation,
                    chain_head,
                    claim_id=claim_id,
                    tenant_binding_sha256=records[0].event[
                        "tenant_binding_sha256"
                    ],
                    principal_key_binding_sha256=records[0].event[
                        "principal_key_binding_sha256"
                    ],
                    event_sha256s=tuple(
                        record.event_sha256 for record in records
                    ),
                )
            )
        except _ReconciliationStateError:
            raise
        except _PortFailure:
            raise ImmutableEvidenceError(
                "evidence publication state is unavailable"
            ) from None
        if not isinstance(claim, Mapping):
            raise ImmutableEvidenceError(
                "evidence publication claim is invalid"
            )
        if claim.get("status") == "completed":
            def validate_completed_claim() -> dict[str, Any]:
                if set(claim) != {
                    "status", "result", "publication_progress"
                }:
                    raise ImmutableEvidenceError(
                        "evidence publication claim is invalid"
                    )
                completed_progress = _publication_progress(
                    claim["publication_progress"]
                )
                completed_result = _validate_publication_result(
                    claim.get("result"),
                    correlation_id=correlation,
                    chain_head_sha256=chain_head,
                    event_count=len(records),
                )
                expected_hashes = [
                    record.event_sha256 for record in records
                ]
                if (
                    completed_progress["acknowledged_event_sha256s"]
                    != expected_hashes
                ):
                    raise ImmutableEvidenceError(
                        "completed publication acknowledgements do not match chain"
                    )
                _validate_completed_publication_binding(
                    completed_result,
                    completed_progress,
                    chain_head_sha256=chain_head,
                )
                return completed_result

            try:
                return _store_call(validate_completed_claim)
            except _PortFailure:
                raise ImmutableEvidenceError(
                    "evidence publication state is unavailable"
                ) from None
        if set(claim) != {"status", "publication_progress"} or (
            claim.get("status") != "publishing"
        ):
            raise ImmutableEvidenceError(
                "evidence publication claim is invalid"
            )
        publication_progress = _publication_progress(
            claim["publication_progress"]
        )
        expected_hashes = [record.event_sha256 for record in records]
        acknowledged = publication_progress[
            "acknowledged_event_sha256s"
        ]
        if acknowledged != expected_hashes[: len(acknowledged)]:
            raise ImmutableEvidenceError(
                "publication acknowledgements do not match chain order"
            )
        if (
            _PUBLICATION_STAGE_ORDER[publication_progress["stage"]]
            >= _PUBLICATION_STAGE_ORDER["broker-complete"]
            and acknowledged != expected_hashes
        ):
            raise ImmutableEvidenceError(
                "completed broker stage is missing acknowledgements"
            )

        def advance(stage: str) -> None:
            if (
                _PUBLICATION_STAGE_ORDER[publication_progress["stage"]]
                < _PUBLICATION_STAGE_ORDER[stage]
            ):
                publication_progress["stage"] = stage
            _store_call(
                lambda: self._reconciliation_store.advance_publication(
                    correlation,
                    claim_id=claim_id,
                    publication_progress=publication_progress,
                )
            )

        try:
            acknowledged_set = set(acknowledged)
            for record in records:
                if record.event_sha256 in acknowledged_set:
                    continue
                advance("broker-in-flight")
                self._validate_broker_ack(
                    _provider_call(
                        lambda: self._broker.publish(_copy_record(record))
                    ),
                    record,
                )
                publication_progress[
                    "acknowledged_event_sha256s"
                ].append(record.event_sha256)
                acknowledged_set.add(record.event_sha256)
                advance("broker-in-flight")
            advance("broker-complete")

            advance("anchor-in-flight")
            anchor_receipt = self._validate_anchor(
                _provider_call(
                    lambda: self._signature_anchor.anchor(
                        _copy_records(records),
                        idempotency_key_sha256=(
                            _publication_operation_key(
                                "signature-anchor", chain_head
                            )
                        ),
                    )
                ),
                records,
            )
            anchor_ref_sha256 = _reference_sha256(
                anchor_receipt["anchor_ref"]
            )
            signature_ref_sha256 = _reference_sha256(
                anchor_receipt["signature_ref"]
            )
            for field, value in (
                ("anchor_ref_sha256", anchor_ref_sha256),
                ("signature_ref_sha256", signature_ref_sha256),
            ):
                persisted = publication_progress[field]
                if persisted is not None and persisted != value:
                    raise ImmutableEvidenceError(
                        f"{field} does not match persisted publication"
                    )
                publication_progress[field] = value
            advance("anchor-readback-in-flight")
            anchor = self._validate_anchor_readback(
                _provider_call(
                    lambda: self._signature_anchor.readback(
                        anchor_receipt["anchor_ref"]
                    )
                ),
                anchor_receipt,
                records,
            )
            advance("anchor-readback-complete")

            advance("worm-commit-in-flight")
            receipt = self._validate_worm_receipt(
                _provider_call(
                    lambda: self._worm_journal.commit(
                        _copy_records(records),
                        dict(anchor),
                        idempotency_key_sha256=(
                            _publication_operation_key(
                                "worm-commit", chain_head
                            )
                        ),
                    )
                ),
                records,
            )
            worm_receipt_ref_sha256 = _reference_sha256(
                receipt["receipt_ref"]
            )
            persisted_worm = publication_progress[
                "worm_receipt_ref_sha256"
            ]
            if (
                persisted_worm is not None
                and persisted_worm != worm_receipt_ref_sha256
            ):
                raise ImmutableEvidenceError(
                    "WORM receipt does not match persisted publication"
                )
            publication_progress[
                "worm_receipt_ref_sha256"
            ] = worm_receipt_ref_sha256
            advance("worm-readback-in-flight")
            readback = self._validate_worm_readback(
                _provider_call(
                    lambda: self._worm_journal.readback(
                        receipt["receipt_ref"]
                    )
                ),
                receipt,
                records,
            )
            advance("worm-readback-complete")

            result = {
                "schema_version":
                    "nac.immutable-evidence-publication/v0.1",
                "status": "SYNTHETIC_PORT_ORCHESTRATION_COMPLETE",
                "correlation_id": str(correlation),
                "chain_head_sha256": chain_head,
                "event_count": len(records),
                "broker_ack_count": len(
                    publication_progress[
                        "acknowledged_event_sha256s"
                    ]
                ),
                "anchor_ref_sha256": anchor_ref_sha256,
                "signature_ref_sha256": signature_ref_sha256,
                "worm_receipt_ref_sha256":
                    worm_receipt_ref_sha256,
                "worm_readback_ref_sha256": _reference_sha256(
                    readback["receipt_ref"]
                ),
                "worm_readback_verified": True,
                "production_durability_claim": False,
            }
            _store_call(
                lambda: self._reconciliation_store.complete_publication(
                    correlation,
                    claim_id=claim_id,
                    result=result,
                )
            )
            return _validate_publication_result(
                result,
                correlation_id=correlation,
                chain_head_sha256=chain_head,
                event_count=len(records),
            )
        except Exception as exc:
            try:
                _store_call(
                    lambda: self._reconciliation_store.require(
                        correlation,
                        "evidence-publication-incomplete",
                        chain_head,
                        claim_id=claim_id,
                        publication_progress=publication_progress,
                    )
                )
            except Exception:
                raise ImmutableEvidenceError(
                    "evidence publication state is unavailable"
                ) from None
            if isinstance(exc, ImmutableEvidenceError):
                raise
            raise ImmutableEvidenceError(
                "evidence publication requires reconciliation"
            ) from None

    @staticmethod
    def _validate_broker_ack(
        acknowledgement: Mapping[str, Any], record: EvidenceRecord
    ) -> Mapping[str, Any]:
        if not isinstance(acknowledgement, Mapping) or frozenset(
            acknowledgement
        ) != {
            "ack_ref",
            "event_id",
            "event_sha256",
            "idempotency_key_sha256",
            "delivery_key_sha256",
        }:
            raise ImmutableEvidenceError("broker acknowledgement is invalid")
        ack_ref = _opaque_reference(
            acknowledgement["ack_ref"], "ack_ref", _BROKER_ACK_REF
        )
        if ack_ref != f"broker-ack-v1-{record.event_sha256}":
            raise ImmutableEvidenceError(
                "broker acknowledgement binding is invalid: ack_ref"
            )
        expected = {
            "event_id": record.event["event_id"],
            "event_sha256": record.event_sha256,
            "idempotency_key_sha256": record.event["idempotency_key_sha256"],
            "delivery_key_sha256": record.event["delivery_key_sha256"],
        }
        for field, value in expected.items():
            if acknowledgement[field] != value:
                raise ImmutableEvidenceError(
                    f"broker acknowledgement binding is invalid: {field}"
                )
        return acknowledgement

    @staticmethod
    def _validate_anchor(
        anchor: Mapping[str, Any], records: tuple[EvidenceRecord, ...]
    ) -> Mapping[str, Any]:
        if not isinstance(anchor, Mapping) or frozenset(anchor) != {
            "anchor_ref",
            "signature_ref",
            "record_count",
            "first_event_sha256",
            "last_event_sha256",
            "head_sha256",
        }:
            raise ImmutableEvidenceError("signature anchor receipt is invalid")
        _opaque_reference(anchor["anchor_ref"], "anchor_ref", _ANCHOR_REF)
        _opaque_reference(
            anchor["signature_ref"], "signature_ref", _SIGNATURE_REF
        )
        if anchor["record_count"] != len(records):
            raise ImmutableEvidenceError("signature anchor count is invalid")
        expected_hash = records[-1].event_sha256
        if (
            anchor["first_event_sha256"] != records[0].event_sha256
            or anchor["last_event_sha256"] != expected_hash
            or anchor["head_sha256"] != expected_hash
        ):
            raise ImmutableEvidenceError("signature anchor binding is invalid")
        return anchor

    @classmethod
    def _validate_anchor_readback(
        cls,
        readback: Mapping[str, Any],
        receipt: Mapping[str, Any],
        records: tuple[EvidenceRecord, ...],
    ) -> Mapping[str, Any]:
        validated = cls._validate_anchor(readback, records)
        if dict(validated) != dict(receipt):
            raise ImmutableEvidenceError(
                "signature anchor readback does not match receipt"
            )
        return validated

    @staticmethod
    def _validate_worm_receipt(
        receipt: Mapping[str, Any], records: tuple[EvidenceRecord, ...]
    ) -> Mapping[str, Any]:
        if not isinstance(receipt, Mapping) or frozenset(receipt) != {
            "receipt_ref",
            "head_sha256",
        }:
            raise ImmutableEvidenceError("WORM receipt is invalid")
        _opaque_reference(
            receipt["receipt_ref"], "receipt_ref", _WORM_RECEIPT_REF
        )
        if receipt["head_sha256"] != records[-1].event_sha256:
            raise ImmutableEvidenceError("WORM receipt head is invalid")
        return receipt

    @staticmethod
    def _validate_worm_readback(
        readback: Mapping[str, Any],
        receipt: Mapping[str, Any],
        records: tuple[EvidenceRecord, ...],
    ) -> Mapping[str, Any]:
        if not isinstance(readback, Mapping) or frozenset(readback) != {
            "receipt_ref",
            "head_sha256",
            "retention_years",
            "legal_hold_capable",
        }:
            raise ImmutableEvidenceError("WORM readback is invalid")
        if (
            readback["receipt_ref"] != receipt["receipt_ref"]
            or readback["head_sha256"] != records[-1].event_sha256
            or type(readback["retention_years"]) is not int
            or readback["retention_years"]
            < records[0].event["retention"]["minimum_years"]
            or readback["legal_hold_capable"] is not True
        ):
            raise ImmutableEvidenceError("WORM readback binding is invalid")
        return readback


def actor_ref(
    *,
    tenant_id: str,
    actor_object_id: str,
    key_version: int,
    key: bytes,
    principal_key: bytes,
) -> str:
    tenant = _uuid_text(tenant_id, "tenant_id")
    actor = _uuid_text(actor_object_id, "actor_object_id")
    version, secret = _key_material(key_version, key)
    if type(principal_key) is not bytes or len(principal_key) < 32:
        raise ImmutableEvidenceError(
            "principal binding key must be at least 32 bytes"
        )
    domain = (
        b"nac.actor-ref.v1\x00"
        + tenant.encode("ascii")
        + b"\x00k"
        + str(version).encode("ascii")
        + b"\x00"
    )
    digest = hmac.new(secret, domain + actor.encode("ascii"), hashlib.sha256).hexdigest()
    principal_digest = hmac.new(
        principal_key,
        b"nac.principal-ref.v1\x00"
        + tenant.encode("ascii")
        + b"\x00"
        + actor.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    tenant_binding_sha256 = hashlib.sha256(
        b"nac.tenant-binding.v1\x00" + tenant.encode("ascii")
    ).hexdigest()
    principal_key_binding_sha256 = hashlib.sha256(
        b"nac.principal-key-binding.v1\x00" + principal_key
    ).hexdigest()
    return _VerifiedActorRef(
        f"actor-v1-k{version}-{digest}",
        _ACTOR_REF_FACTORY_TOKEN,
        f"principal-v1-{principal_digest}",
        tenant_binding_sha256,
        principal_key_binding_sha256,
    )


def correlation_ref(
    *, tenant_id: str, source_object_id: str, key_version: int, key: bytes
) -> str:
    tenant = _uuid_text(tenant_id, "tenant_id")
    source = _uuid_text(source_object_id, "source_object_id")
    version, secret = _key_material(key_version, key)
    domain = (
        b"nac.correlation-ref.v1\x00"
        + tenant.encode("ascii")
        + b"\x00k"
        + str(version).encode("ascii")
        + b"\x00"
    )
    digest = hmac.new(
        secret, domain + source.encode("ascii"), hashlib.sha256
    ).hexdigest()
    tenant_binding_sha256 = hashlib.sha256(
        b"nac.tenant-binding.v1\x00" + tenant.encode("ascii")
    ).hexdigest()
    return _VerifiedCorrelationRef(
        f"correlation-v1-k{version}-{digest}",
        _CORRELATION_REF_FACTORY_TOKEN,
        tenant_binding_sha256,
    )


def build_event(
    *,
    correlation_id: str,
    phase: EvidencePhase,
    sequence: int,
    previous_event_sha256: str,
    actor_ref_value: str,
    tool_id: str,
    role_id: str,
    action: str,
    business_case_type_id: str,
    catalog_version: str,
    identifier_registry: TypedIdentifierRegistry,
    manifest_sha256: str,
    occurred_at: str,
    result_code: str | None = None,
    etags: Mapping[str, str] | None = None,
    etag_hmac_key: bytes,
    etag_hmac_key_version: int,
    retention_years: int = MINIMUM_RETENTION_YEARS,
    legal_hold: bool = True,
    reconciliation_reason_code: str | None = None,
    reconciliation_operator_ref: str | None = None,
    reconciliation_approver_ref: str | None = None,
) -> dict[str, Any]:
    if phase not in PHASES:
        raise ImmutableEvidenceError("phase is invalid")
    correlation = _trusted_correlation_ref(correlation_id, "correlation_id")
    if type(sequence) is not int or sequence < 1:
        raise ImmutableEvidenceError("sequence must be a positive integer")
    previous_hash = _sha256(previous_event_sha256, "previous_event_sha256")
    if sequence == 1 and previous_hash != ZERO_HASH:
        raise ImmutableEvidenceError("first event must use the zero hash")
    if sequence > 1 and previous_hash == ZERO_HASH:
        raise ImmutableEvidenceError("later events cannot use the zero hash")
    actor_value = _trusted_actor_ref(actor_ref_value, "actor_ref_value")
    if correlation._tenant_binding_sha256 != actor_value._tenant_binding_sha256:
        raise ImmutableEvidenceError(
            "correlation and actor tenant binding differ"
        )
    if action not in MUTATION_ACTIONS:
        raise ImmutableEvidenceError("action is invalid")
    if type(retention_years) is not int or retention_years < MINIMUM_RETENTION_YEARS:
        raise ImmutableEvidenceError("retention must be at least ten years")
    if legal_hold is not True:
        raise ImmutableEvidenceError("legal hold capability must be enabled")
    _utc_seconds(occurred_at)
    tool = _registered_identifier(tool_id, "tool_id", _TOOL_ID, REGISTERED_TOOL_IDS)
    role = _registered_identifier(role_id, "role_id", _ROLE_ID, REGISTERED_ROLE_IDS)
    registry = _trusted_identifier_registry(identifier_registry)
    case_type = _registered_identifier(
        business_case_type_id,
        "business_case_type_id",
        _BUSINESS_CASE_TYPE_ID,
        registry.business_case_type_ids,
    )
    catalog = _registered_identifier(
        catalog_version,
        "catalog_version",
        _CATALOG_VERSION,
        registry.catalog_versions,
    )
    manifest = _sha256(manifest_sha256, "manifest_sha256")
    operation_binding = {
        "correlation_id": str(correlation),
        "actor_ref": str(actor_value),
        "actor_principal_ref": actor_value._principal_ref,
        "tenant_binding_sha256": actor_value._tenant_binding_sha256,
        "principal_key_binding_sha256": (
            actor_value._principal_key_binding_sha256
        ),
        "tool_id": tool,
        "role_id": role,
        "action": action,
        "business_case_type_id": case_type,
        "catalog_version": catalog,
        "manifest_sha256": manifest,
    }
    idempotency_key_sha256 = hashlib.sha256(
        canonical_json_bytes(operation_binding)
    ).hexdigest()
    event: dict[str, Any] = {
        "schema_version": "nac.immutable-evidence-event/v0.1",
        "idempotency_key_sha256": idempotency_key_sha256,
        "correlation_id": str(correlation),
        "phase": phase,
        "sequence": sequence,
        "previous_event_sha256": previous_hash,
        "actor_ref": str(actor_value),
        "actor_principal_ref": actor_value._principal_ref,
        "tenant_binding_sha256": actor_value._tenant_binding_sha256,
        "principal_key_binding_sha256": (
            actor_value._principal_key_binding_sha256
        ),
        "tool_id": tool,
        "role_id": role,
        "action": action,
        "business_case_type_id": case_type,
        "catalog_version": catalog,
        "manifest_sha256": manifest,
        "occurred_at": occurred_at,
        "retention": {
            "minimum_years": retention_years,
            "legal_hold_capable": legal_hold,
        },
        "privacy": {
            "classification": "pseudonymous_personal_data",
            "read_role": "revision_audit",
            "monthly_access_review_required": True,
        },
        "etags": _etags(
            etags or {},
            etag_hmac_key,
            etag_hmac_key_version,
            actor_value._tenant_binding_sha256,
        ),
    }
    if phase == "intent":
        if result_code is not None or reconciliation_reason_code is not None:
            raise ImmutableEvidenceError("intent cannot contain an outcome")
    elif phase in {"outcome", "readback"}:
        event["result_code"] = _result_code(phase, result_code)
        if reconciliation_reason_code is not None:
            raise ImmutableEvidenceError("outcome/readback cannot contain reconciliation data")
    elif phase == "reconciliation_required":
        event["reason_code"] = _reason_code(reconciliation_reason_code)
        if result_code is not None:
            raise ImmutableEvidenceError("reconciliation_required cannot contain result_code")
    else:
        event["result_code"] = _result_code(phase, result_code)
        operator = _trusted_actor_ref(
            reconciliation_operator_ref, "reconciliation_operator_ref"
        )
        approver = _trusted_actor_ref(
            reconciliation_approver_ref, "reconciliation_approver_ref"
        )
        event["operator_ref"] = str(operator)
        event["operator_principal_ref"] = operator._principal_ref
        event["approver_ref"] = str(approver)
        event["approver_principal_ref"] = approver._principal_ref
        event["operator_tenant_binding_sha256"] = (
            operator._tenant_binding_sha256
        )
        event["approver_tenant_binding_sha256"] = (
            approver._tenant_binding_sha256
        )
        event["operator_principal_key_binding_sha256"] = (
            operator._principal_key_binding_sha256
        )
        event["approver_principal_key_binding_sha256"] = (
            approver._principal_key_binding_sha256
        )
        for principal in (operator, approver):
            if principal._tenant_binding_sha256 != actor_value._tenant_binding_sha256:
                raise ImmutableEvidenceError(
                    "reconciliation principal tenant binding differs"
                )
            if (
                principal._principal_key_binding_sha256
                != actor_value._principal_key_binding_sha256
            ):
                raise ImmutableEvidenceError(
                    "reconciliation principal key binding differs"
                )
        if _same_principal(
            reconciliation_operator_ref,
            reconciliation_approver_ref,
        ):
            raise ImmutableEvidenceError("reconciliation requires separate principals")
    _reject_sensitive(event)
    event["delivery_key_sha256"] = _delivery_key(event)
    event["event_id"] = _event_id(event)
    payload_sha256 = hashlib.sha256(canonical_json_bytes(event)).hexdigest()
    return _VerifiedEvidenceEvent(
        event,
        _EVIDENCE_EVENT_FACTORY_TOKEN,
        payload_sha256,
    )


class InMemoryEvidenceOutbox:
    """Synthetic test adapter; it makes no WORM or production durability claim."""

    def __init__(self) -> None:
        self._records: dict[str, list[EvidenceRecord]] = {}

    def append(self, event: Mapping[str, Any]) -> EvidenceRecord:
        if (
            type(event) is not _VerifiedEvidenceEvent
            or event._factory_token is not _EVIDENCE_EVENT_FACTORY_TOKEN
        ):
            raise ImmutableEvidenceError("event must be created by build_event")
        payload = canonical_json_bytes(event)
        if hashlib.sha256(payload).hexdigest() != event._payload_sha256:
            raise ImmutableEvidenceError("event changed after build_event")
        candidate = json.loads(payload.decode("ascii"))
        _validate_event_shape(candidate)
        correlation_id = _correlation_ref(candidate.get("correlation_id"), "correlation_id")
        existing = self._records.setdefault(correlation_id, [])
        expected_sequence = len(existing) + 1
        expected_previous = existing[-1].event_sha256 if existing else ZERO_HASH
        if candidate.get("sequence") != expected_sequence:
            raise ImmutableEvidenceError("outbox sequence is not contiguous")
        if candidate.get("previous_event_sha256") != expected_previous:
            raise ImmutableEvidenceError("outbox hash binding is invalid")
        _validate_transition(tuple(existing), candidate)
        event_hash = hashlib.sha256(payload).hexdigest()
        if any(record.event_sha256 == event_hash for record in existing):
            raise ImmutableEvidenceError("duplicate event is not allowed")
        record = EvidenceRecord(event=candidate, event_sha256=event_hash)
        existing.append(record)
        return _copy_record(record)

    def records(self, correlation_id: str) -> tuple[EvidenceRecord, ...]:
        return tuple(
            _copy_record(record)
            for record in self._records.get(
                _correlation_ref(correlation_id, "correlation_id"), ()
            )
        )


class InMemoryReconciliationStore:
    """Synthetic state adapter; production requires transactional persistence."""

    def __init__(self) -> None:
        self._required: dict[str, dict[str, Any]] = {}
        self._publications: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def claim_publication(
        self,
        correlation_id: str,
        chain_head_sha256: str,
        *,
        claim_id: str,
        tenant_binding_sha256: str,
        principal_key_binding_sha256: str,
        event_sha256s: tuple[str, ...],
    ) -> Mapping[str, Any]:
        correlation_value = _trusted_correlation_ref(
            correlation_id, "correlation_id"
        )
        correlation = str(correlation_value)
        tenant_binding = _sha256(
            tenant_binding_sha256, "tenant_binding_sha256"
        )
        principal_key_binding = _sha256(
            principal_key_binding_sha256,
            "principal_key_binding_sha256",
        )
        event_hashes = _event_sha256_sequence(
            event_sha256s, "event_sha256s", allow_empty=False
        )
        if correlation_value._tenant_binding_sha256 != tenant_binding:
            raise ImmutableEvidenceError(
                "publication tenant binding is invalid"
            )
        chain_head = _sha256(
            chain_head_sha256, "chain_head_sha256"
        )
        if event_hashes[-1] != chain_head:
            raise ImmutableEvidenceError(
                "publication event sequence does not match chain head"
            )
        claim = _claim_ref(claim_id)
        with self._lock:
            requirement = self._required.get(correlation)
            state = self._publications.get(correlation)
            pending_retry_authorizations: list[dict[str, str]] = []
            if requirement is not None:
                if (
                    requirement["reason_code"]
                    != "evidence-publication-incomplete"
                    or requirement.get("retry_authorized") is not True
                ):
                    raise _ReconciliationStateError(
                        "evidence publication is blocked by reconciliation"
                    )
                if (
                    requirement["tenant_binding_sha256"]
                    != tenant_binding
                    or requirement["principal_key_binding_sha256"]
                    != principal_key_binding
                    or event_hashes[
                        : len(requirement["event_sha256s"])
                    ]
                    != tuple(requirement["event_sha256s"])
                ):
                    raise _ReconciliationStateError(
                        "publication security binding does not match persisted state"
                    )
                if state is not None:
                    raise _ReconciliationStateError(
                        "evidence publication is blocked by reconciliation"
                    )
                pending_retry_authorizations = _copy_json(
                    requirement["retry_authorizations"]
                )
            if state is None:
                progress = _publication_progress(
                    {
                        "stage": "outbox-snapshot",
                        "acknowledged_event_sha256s": [],
                        "anchor_ref_sha256": None,
                        "signature_ref_sha256": None,
                        "worm_receipt_ref_sha256": None,
                    }
                )
                self._publications[correlation] = {
                    "status": "publishing",
                    "chain_head_sha256": chain_head,
                    "tenant_binding_sha256": tenant_binding,
                    "principal_key_binding_sha256": principal_key_binding,
                    "event_sha256s": list(event_hashes),
                    "claim_id": claim,
                    "progress": progress,
                    "retry_authorization_count": len(
                        pending_retry_authorizations
                    ),
                    "retry_authorizations": pending_retry_authorizations,
                }
                if requirement is not None:
                    del self._required[correlation]
                return {
                    "status": "publishing",
                    "publication_progress": _copy_json(progress),
                }
            if state["chain_head_sha256"] != chain_head:
                raise _ReconciliationStateError(
                    "publication chain head does not match persisted state"
                )
            if (
                state["tenant_binding_sha256"] != tenant_binding
                or state["principal_key_binding_sha256"]
                != principal_key_binding
                or tuple(state["event_sha256s"]) != event_hashes
            ):
                raise _ReconciliationStateError(
                    "publication security binding does not match persisted state"
                )
            if state["status"] == "completed":
                return {
                    "status": "completed",
                    "result": _copy_json(state["result"]),
                    "publication_progress": _copy_json(state["progress"]),
                }
            if state["claim_id"] is not None:
                raise _ReconciliationStateError(
                    "evidence publication already has an active claim"
                )
            state["claim_id"] = claim
            return {
                "status": "publishing",
                "publication_progress": _copy_json(state["progress"]),
            }

    def advance_publication(
        self,
        correlation_id: str,
        *,
        claim_id: str,
        publication_progress: Mapping[str, Any],
    ) -> None:
        correlation = _correlation_ref(correlation_id, "correlation_id")
        claim = _claim_ref(claim_id)
        with self._lock:
            state = self._active_claim(correlation, claim)
            candidate = _publication_progress(publication_progress)
            _validate_publication_progress_advance(
                state["progress"], candidate
            )
            _validate_publication_progress_event_binding(
                candidate, tuple(state["event_sha256s"])
            )
            state["progress"] = candidate

    def complete_publication(
        self,
        correlation_id: str,
        *,
        claim_id: str,
        result: Mapping[str, Any],
    ) -> None:
        correlation = _correlation_ref(correlation_id, "correlation_id")
        claim = _claim_ref(claim_id)
        with self._lock:
            state = self._active_claim(correlation, claim)
            progress = state["progress"]
            if progress["stage"] != "worm-readback-complete":
                raise ImmutableEvidenceError(
                    "publication completion evidence is incomplete"
                )
            event_sha256s = tuple(state["event_sha256s"])
            _validate_publication_progress_event_binding(
                progress, event_sha256s
            )
            safe_result = _validate_publication_result(
                result,
                correlation_id=correlation,
                chain_head_sha256=state["chain_head_sha256"],
                event_count=len(event_sha256s),
            )
            _validate_completed_publication_binding(
                safe_result,
                progress,
                chain_head_sha256=state["chain_head_sha256"],
            )
            state["status"] = "completed"
            state["claim_id"] = None
            state["result"] = safe_result

    def authorize_publication_retry(
        self,
        correlation_id: str,
        *,
        operator_ref: str,
        approver_ref: str,
    ) -> None:
        correlation_value = _trusted_correlation_ref(
            correlation_id, "correlation_id"
        )
        correlation = str(correlation_value)
        operator = _trusted_actor_ref(operator_ref, "operator_ref")
        approver = _trusted_actor_ref(approver_ref, "approver_ref")
        if _same_principal(operator, approver):
            raise ImmutableEvidenceError(
                "publication retry requires separate principals"
            )
        with self._lock:
            state = self._publications.get(correlation)
            requirement = self._required.get(correlation)
            if state is None and requirement is None:
                raise ImmutableEvidenceError(
                    "publication retry has no blocked state"
                )
            if (
                requirement is not None
                and requirement["reason_code"]
                != "evidence-publication-incomplete"
            ):
                raise ImmutableEvidenceError(
                    "reconciliation reason is not publication-retry eligible"
                )
            expected_tenant = (
                state["tenant_binding_sha256"]
                if state is not None
                else requirement["tenant_binding_sha256"]
            )
            if correlation_value._tenant_binding_sha256 != expected_tenant:
                raise ImmutableEvidenceError(
                    "publication retry tenant binding differs"
                )
            expected_principal_key = (
                state["principal_key_binding_sha256"]
                if state is not None
                else requirement["principal_key_binding_sha256"]
            )
            if expected_principal_key is None:
                raise ImmutableEvidenceError(
                    "publication retry security binding is unavailable"
                )
            if (
                state is None
                and (
                    not requirement["event_sha256s"]
                    or requirement["event_sha256s"][-1]
                    != requirement["chain_head_sha256"]
                )
            ):
                raise ImmutableEvidenceError(
                    "publication retry event prefix is unavailable"
                )
            for principal in (operator, approver):
                if principal._tenant_binding_sha256 != expected_tenant:
                    raise ImmutableEvidenceError(
                        "publication retry principal tenant binding differs"
                    )
                if (
                    principal._principal_key_binding_sha256
                    != expected_principal_key
                ):
                    raise ImmutableEvidenceError(
                        "publication retry principal key binding differs"
                    )
            if state is not None and state["status"] == "completed":
                raise ImmutableEvidenceError(
                    "completed publication cannot be retried"
                )
            authorization = {
                "operator_principal_ref": operator._principal_ref,
                "approver_principal_ref": approver._principal_ref,
            }
            if requirement is not None and state is None:
                requirement["retry_authorized"] = True
                requirement["retry_authorizations"].append(authorization)
            elif requirement is not None:
                del self._required[correlation]
            if state is not None:
                state["claim_id"] = None
                state["retry_authorization_count"] += 1
                state["retry_authorizations"].append(authorization)

    def require(
        self,
        correlation_id: str,
        reason_code: str,
        chain_head_sha256: str,
        *,
        claim_id: str | None = None,
        publication_progress: Mapping[str, Any] | None = None,
        tenant_binding_sha256: str | None = None,
        principal_key_binding_sha256: str | None = None,
        event_sha256s: tuple[str, ...] | None = None,
    ) -> None:
        correlation_value = _trusted_correlation_ref(
            correlation_id, "correlation_id"
        )
        correlation = str(correlation_value)
        with self._lock:
            publication = self._publications.get(correlation)
            if publication is not None:
                if publication["status"] == "completed":
                    raise ImmutableEvidenceError(
                        "completed publication cannot require reconciliation"
                    )
                if (
                    claim_id is not None
                    and publication["claim_id"] != _claim_ref(claim_id)
                ):
                    raise ImmutableEvidenceError(
                        "publication claim ownership is invalid"
                    )
                publication_progress = publication["progress"]
            supplied_tenant_binding = (
                _sha256(tenant_binding_sha256, "tenant_binding_sha256")
                if tenant_binding_sha256 is not None
                else None
            )
            supplied_principal_key_binding = (
                _sha256(
                    principal_key_binding_sha256,
                    "principal_key_binding_sha256",
                )
                if principal_key_binding_sha256 is not None
                else None
            )
            supplied_event_hashes = _event_sha256_sequence(
                event_sha256s or (),
                "event_sha256s",
                allow_empty=True,
            )
            effective_tenant_binding = (
                publication["tenant_binding_sha256"]
                if publication is not None
                else supplied_tenant_binding
                or correlation_value._tenant_binding_sha256
            )
            effective_principal_key_binding = (
                publication["principal_key_binding_sha256"]
                if publication is not None
                else supplied_principal_key_binding
            )
            effective_event_hashes = (
                tuple(publication["event_sha256s"])
                if publication is not None
                else supplied_event_hashes
            )
            if (
                effective_tenant_binding
                != correlation_value._tenant_binding_sha256
                or (
                    publication is not None
                    and supplied_tenant_binding is not None
                    and supplied_tenant_binding
                    != publication["tenant_binding_sha256"]
                )
                or (
                    publication is not None
                    and supplied_principal_key_binding is not None
                    and supplied_principal_key_binding
                    != publication["principal_key_binding_sha256"]
                )
                or (
                    publication is not None
                    and supplied_event_hashes
                    and supplied_event_hashes
                    != tuple(publication["event_sha256s"])
                )
                or (
                    effective_event_hashes
                    and effective_event_hashes[-1]
                    != _sha256(chain_head_sha256, "chain_head_sha256")
                )
            ):
                raise ImmutableEvidenceError(
                    "reconciliation security binding is invalid"
                )
            requirement = {
                "reason_code": _reason_code(reason_code),
                "chain_head_sha256": _sha256(
                    chain_head_sha256, "chain_head_sha256"
                ),
                "publication_progress": _publication_progress(
                    publication_progress
                ),
                "tenant_binding_sha256": effective_tenant_binding,
                "principal_key_binding_sha256": (
                    effective_principal_key_binding
                ),
                "event_sha256s": list(effective_event_hashes),
                "retry_authorized": False,
                "retry_authorizations": [],
            }
            previous = self._required.setdefault(
                correlation, requirement
            )
            if previous != requirement:
                raise ImmutableEvidenceError(
                    "reconciliation requirement cannot be replaced"
                )

    def requirement(self, correlation_id: str) -> dict[str, Any]:
        correlation = _correlation_ref(correlation_id, "correlation_id")
        with self._lock:
            try:
                requirement = self._required[correlation]
            except KeyError as exc:
                raise ImmutableEvidenceError(
                    "reconciliation is not required"
                ) from exc
            return _copy_json(requirement)

    def close(
        self,
        correlation_id: str,
        *,
        records: tuple[EvidenceRecord, ...],
        operator_ref: str,
        approver_ref: str,
    ) -> None:
        correlation = _correlation_ref(correlation_id, "correlation_id")
        operator = _trusted_actor_ref(operator_ref, "operator_ref")
        approver = _trusted_actor_ref(approver_ref, "approver_ref")
        if _same_principal(operator, approver):
            raise ImmutableEvidenceError(
                "reconciliation requires separate principals"
            )
        with self._lock:
            if correlation not in self._required:
                raise ImmutableEvidenceError(
                    "reconciliation is not required"
                )
            snapshot = _copy_records(records)
            status = verify_chain(snapshot)
            if status["correlation_id"] != correlation:
                raise ImmutableEvidenceError(
                    "reconciliation evidence correlation is invalid"
                )
            if status["complete"] is not True:
                raise ImmutableEvidenceError(
                    "reconciliation closure evidence is incomplete"
                )
            requirement = self._required[correlation]
            reason = requirement["reason_code"]
            required_head = requirement["chain_head_sha256"]
            matching_indexes = [
                index
                for index, record in enumerate(snapshot)
                if record.event_sha256 == required_head
            ]
            if len(matching_indexes) != 1:
                raise ImmutableEvidenceError(
                    "reconciliation evidence chain head is not bound"
                )
            reason_index = matching_indexes[0] + 1
            if (
                reason_index >= len(snapshot)
                or snapshot[reason_index].event["phase"]
                != "reconciliation_required"
            ):
                raise ImmutableEvidenceError(
                    "reconciliation requirement does not follow bound chain head"
                )
            closure = snapshot[-1].event
            if (
                closure["operator_ref"] != operator
                or closure["approver_ref"] != approver
                or closure["operator_principal_ref"]
                != operator._principal_ref
                or closure["approver_principal_ref"]
                != approver._principal_ref
            ):
                raise ImmutableEvidenceError(
                    "reconciliation closure principals do not match"
                )
            if snapshot[reason_index].event["reason_code"] != reason:
                raise ImmutableEvidenceError(
                    "reconciliation closure reason does not match"
                )
            if (
                snapshot[-2].event["result_code"]
                not in _SUCCESS_READBACK_CODES
            ):
                raise ImmutableEvidenceError(
                    "reconciliation readback did not succeed"
                )
            if closure["result_code"] != "reconciled":
                raise ImmutableEvidenceError(
                    "reconciliation closure did not succeed"
                )
            del self._required[correlation]

    def is_required(self, correlation_id: str) -> bool:
        correlation = _correlation_ref(correlation_id, "correlation_id")
        with self._lock:
            publication = self._publications.get(correlation)
            return (
                correlation in self._required
                or (
                    publication is not None
                    and publication["status"] == "publishing"
                )
            )

    def _active_claim(
        self, correlation: str, claim_id: str
    ) -> dict[str, Any]:
        state = self._publications.get(correlation)
        if (
            state is None
            or state["status"] != "publishing"
            or state["claim_id"] != claim_id
        ):
            raise ImmutableEvidenceError(
                "publication progress has no active claim"
            )
        return state



def verify_chain(records: Iterable[EvidenceRecord]) -> dict[str, Any]:
    ordered = tuple(records)
    if not ordered:
        raise ImmutableEvidenceError("evidence chain is empty")
    previous = ZERO_HASH
    correlation_id: str | None = None
    verified: list[EvidenceRecord] = []
    for sequence, record in enumerate(ordered, start=1):
        if type(record) is not EvidenceRecord:
            raise ImmutableEvidenceError("evidence record is invalid")
        payload = canonical_json_bytes(record.event)
        event_hash = hashlib.sha256(payload).hexdigest()
        if record.event_sha256 != event_hash:
            raise ImmutableEvidenceError("event hash is invalid")
        if record.event.get("sequence") != sequence:
            raise ImmutableEvidenceError("event sequence is invalid")
        if record.event.get("previous_event_sha256") != previous:
            raise ImmutableEvidenceError("event chain is invalid")
        current_correlation = record.event.get("correlation_id")
        if correlation_id is None:
            correlation_id = _correlation_ref(current_correlation, "correlation_id")
        elif current_correlation != correlation_id:
            raise ImmutableEvidenceError("correlation binding changed")
        _validate_transition(tuple(verified), record.event)
        _validate_event_shape(record.event)
        verified.append(record)
        previous = event_hash

    phases = tuple(record.event["phase"] for record in verified)
    normal_complete = (
        phases == _NORMAL_PHASE_ORDER
        and verified[1].event["result_code"]
        in (_SUCCESS_OUTCOME_CODES | {"failed"})
        and verified[2].event["result_code"] in _SUCCESS_READBACK_CODES
    )
    reconciliation_complete = (
        phases in _RECONCILIATION_PHASE_ORDERS
        and verified[-2].event["result_code"] in _SUCCESS_READBACK_CODES
        and verified[-1].event["result_code"] == "reconciled"
    )
    complete = normal_complete or reconciliation_complete
    reconciliation_required = not complete
    return {
        "schema_version": "nac.immutable-evidence-chain-status/v0.1",
        "s6_status": S6_STATUS,
        "live_status": LIVE_STATUS,
        "correlation_id": correlation_id,
        "event_count": len(verified),
        "head_sha256": previous,
        "phases": list(phases),
        "complete": complete,
        "reconciliation_required": reconciliation_required,
        "mutation_result": (
            verified[1].event["result_code"] if len(verified) > 1 else "not-recorded"
        ),
        "production_worm_claim": False,
    }


def canonical_json_bytes(value: Any) -> bytes:
    _reject_sensitive(value)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise ImmutableEvidenceError("value must be canonical JSON") from exc


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _copy_json(value: Any) -> Any:
    return json.loads(canonical_json_bytes(value).decode("ascii"))


def _validate_publication_result(
    value: Any,
    *,
    correlation_id: str,
    chain_head_sha256: str,
    event_count: int,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ImmutableEvidenceError("publication result is invalid")
    safe_result = _copy_json(value)
    expected_fields = {
        "schema_version",
        "status",
        "correlation_id",
        "chain_head_sha256",
        "event_count",
        "broker_ack_count",
        "anchor_ref_sha256",
        "signature_ref_sha256",
        "worm_receipt_ref_sha256",
        "worm_readback_ref_sha256",
        "worm_readback_verified",
        "production_durability_claim",
    }
    if (
        set(safe_result) != expected_fields
        or safe_result.get("schema_version")
        != "nac.immutable-evidence-publication/v0.1"
        or safe_result.get("status")
        != "SYNTHETIC_PORT_ORCHESTRATION_COMPLETE"
        or safe_result.get("correlation_id")
        != _correlation_ref(correlation_id, "correlation_id")
        or safe_result.get("chain_head_sha256")
        != _sha256(chain_head_sha256, "chain_head_sha256")
        or type(event_count) is not int
        or event_count < 1
        or safe_result.get("event_count") != event_count
        or safe_result.get("broker_ack_count")
        != safe_result["event_count"]
        or safe_result.get("worm_readback_verified") is not True
        or safe_result.get("production_durability_claim") is not False
    ):
        raise ImmutableEvidenceError("publication result is invalid")
    for field in (
        "anchor_ref_sha256",
        "signature_ref_sha256",
        "worm_receipt_ref_sha256",
        "worm_readback_ref_sha256",
    ):
        _sha256(safe_result.get(field), field)
    return safe_result


def _validate_completed_publication_binding(
    result: Mapping[str, Any],
    progress: Mapping[str, Any],
    *,
    chain_head_sha256: str,
) -> None:
    safe_progress = _publication_progress(progress)
    chain_head = _sha256(chain_head_sha256, "chain_head_sha256")
    acknowledged = safe_progress["acknowledged_event_sha256s"]
    if (
        safe_progress["stage"] != "worm-readback-complete"
        or not acknowledged
        or acknowledged[-1] != chain_head
        or result["broker_ack_count"] != len(acknowledged)
        or result["anchor_ref_sha256"]
        != safe_progress["anchor_ref_sha256"]
        or result["signature_ref_sha256"]
        != safe_progress["signature_ref_sha256"]
        or result["worm_receipt_ref_sha256"]
        != safe_progress["worm_receipt_ref_sha256"]
        or result["worm_readback_ref_sha256"]
        != safe_progress["worm_receipt_ref_sha256"]
    ):
        raise ImmutableEvidenceError(
            "publication result does not match persisted progress"
        )


def _copy_record(record: EvidenceRecord) -> EvidenceRecord:
    return EvidenceRecord(
        event=json.loads(canonical_json_bytes(record.event).decode("ascii")),
        event_sha256=record.event_sha256,
    )


def _copy_records(
    records: tuple[EvidenceRecord, ...],
) -> tuple[EvidenceRecord, ...]:
    return tuple(_copy_record(record) for record in records)


def _validate_transition(
    records: tuple[EvidenceRecord, ...], event: Mapping[str, Any]
) -> None:
    phases = tuple(record.event.get("phase") for record in records)
    candidate = event.get("phase")
    allowed = False
    if not records:
        allowed = candidate == "intent"
    elif phases == ("intent",):
        allowed = candidate == "outcome"
    elif candidate == "readback":
        allowed = (
            (
                phases[-1] == "outcome"
                and records[-1].event.get("result_code")
                != _UNCERTAIN_OUTCOME_CODE
            )
            or phases[-1] == "reconciliation_required"
            or (
                phases[-1] == "reconciliation_closed"
                and records[-1].event.get("result_code") == "failed"
            )
        )
    elif candidate == "reconciliation_required":
        if phases[-1] == "outcome":
            outcome_code = records[-1].event.get("result_code")
            reason_code = event.get("reason_code")
            allowed = (
                outcome_code == _UNCERTAIN_OUTCOME_CODE
                or reason_code
                in {"readback-missing", "provider-readback-required"}
            )
        elif phases[-1] == "readback":
            allowed = (
                records[-1].event.get("result_code") == "failed"
                and event.get("reason_code")
                == "provider-readback-required"
            )
    elif candidate == "reconciliation_closed":
        allowed = (
            phases[-1] == "readback"
            and "reconciliation_required" in phases
            and (
                event.get("result_code") == "failed"
                or records[-1].event.get("result_code")
                in _SUCCESS_READBACK_CODES
            )
        )
    candidate_phases = phases + (candidate,)
    declared_prefix = any(
        order[: len(candidate_phases)] == candidate_phases
        for order in _LEGAL_PHASE_ORDERS
    )
    if type(candidate) is not str or not allowed or not declared_prefix:
        raise ImmutableEvidenceError("evidence phase transition is invalid")
    if (
        candidate == "readback"
        and event.get("result_code") in _SUCCESS_READBACK_CODES
    ):
        outcome = next(
            (
                record.event
                for record in reversed(records)
                if record.event.get("phase") == "outcome"
            ),
            None,
        )
        if not event.get("etags"):
            raise ImmutableEvidenceError(
                "successful readback requires provider ETags"
            )
        if (
            outcome is not None
            and outcome.get("result_code") != _UNCERTAIN_OUTCOME_CODE
            and event.get("etags") != outcome.get("etags")
        ):
            raise ImmutableEvidenceError(
                "successful readback ETags do not match outcome"
            )
    if records:
        first = records[0].event
        for key in (
            "correlation_id",
            "actor_ref",
            "actor_principal_ref",
            "tenant_binding_sha256",
            "principal_key_binding_sha256",
            "tool_id",
            "role_id",
            "action",
            "business_case_type_id",
            "catalog_version",
            "manifest_sha256",
            "idempotency_key_sha256",
            "retention",
            "privacy",
        ):
            if event.get(key) != first.get(key):
                raise ImmutableEvidenceError(f"evidence binding changed: {key}")


def _validate_event_shape(event: Mapping[str, Any]) -> None:
    if not isinstance(event, Mapping):
        raise ImmutableEvidenceError("evidence event must be an object")
    phase = event.get("phase")
    if phase not in PHASES:
        raise ImmutableEvidenceError("phase is invalid")
    phase_fields = {
        "intent": frozenset(),
        "outcome": frozenset({"result_code"}),
        "readback": frozenset({"result_code"}),
        "reconciliation_required": frozenset({"reason_code"}),
        "reconciliation_closed": frozenset(
            {
                "result_code",
                "operator_ref",
                "operator_principal_ref",
                "approver_ref",
                "approver_principal_ref",
                "operator_tenant_binding_sha256",
                "approver_tenant_binding_sha256",
                "operator_principal_key_binding_sha256",
                "approver_principal_key_binding_sha256",
            }
        ),
    }
    base_fields = frozenset(
        {
            "schema_version",
            "event_id",
            "idempotency_key_sha256",
            "delivery_key_sha256",
            "correlation_id",
            "phase",
            "sequence",
            "previous_event_sha256",
            "actor_ref",
            "actor_principal_ref",
            "tenant_binding_sha256",
            "principal_key_binding_sha256",
            "tool_id",
            "role_id",
            "action",
            "business_case_type_id",
            "catalog_version",
            "manifest_sha256",
            "occurred_at",
            "retention",
            "privacy",
            "etags",
        }
    )
    if frozenset(event) != base_fields | phase_fields[phase]:
        raise ImmutableEvidenceError("evidence envelope fields are invalid")
    if event["schema_version"] != "nac.immutable-evidence-event/v0.1":
        raise ImmutableEvidenceError("evidence schema version is invalid")
    correlation = _correlation_ref(event["correlation_id"], "correlation_id")
    sequence = event["sequence"]
    if type(sequence) is not int or sequence < 1:
        raise ImmutableEvidenceError("sequence must be a positive integer")
    _sha256(event["previous_event_sha256"], "previous_event_sha256")
    actor = _actor_ref(event["actor_ref"], "actor_ref")
    actor_principal = _principal_ref(
        event["actor_principal_ref"], "actor_principal_ref"
    )
    tenant_binding = _sha256(
        event["tenant_binding_sha256"], "tenant_binding_sha256"
    )
    principal_key_binding = _sha256(
        event["principal_key_binding_sha256"],
        "principal_key_binding_sha256",
    )
    tool = _registered_identifier(event["tool_id"], "tool_id", _TOOL_ID, REGISTERED_TOOL_IDS)
    role = _registered_identifier(event["role_id"], "role_id", _ROLE_ID, REGISTERED_ROLE_IDS)
    if event["action"] not in MUTATION_ACTIONS:
        raise ImmutableEvidenceError("action is invalid")
    business_case_type_id = _pattern_identifier(
        event["business_case_type_id"],
        "business_case_type_id",
        _BUSINESS_CASE_TYPE_ID,
    )
    catalog_version = _sha256(
        event["catalog_version"], "catalog_version"
    )
    manifest_sha256 = _sha256(event["manifest_sha256"], "manifest_sha256")
    _utc_seconds(event["occurred_at"])
    retention = event["retention"]
    if not isinstance(retention, Mapping) or frozenset(retention) != {
        "minimum_years",
        "legal_hold_capable",
    }:
        raise ImmutableEvidenceError("retention metadata is invalid")
    if (
        type(retention["minimum_years"]) is not int
        or retention["minimum_years"] < MINIMUM_RETENTION_YEARS
        or retention["legal_hold_capable"] is not True
    ):
        raise ImmutableEvidenceError("retention policy is invalid")
    if event["privacy"] != {
        "classification": "pseudonymous_personal_data",
        "read_role": "revision_audit",
        "monthly_access_review_required": True,
    }:
        raise ImmutableEvidenceError("privacy metadata is invalid")
    _validate_etag_hashes(event["etags"])
    if phase in {"outcome", "readback", "reconciliation_closed"}:
        _result_code(phase, event["result_code"])
    if phase == "reconciliation_required":
        _reason_code(event["reason_code"])
    if phase == "reconciliation_closed":
        _actor_ref(event["operator_ref"], "operator_ref")
        _actor_ref(event["approver_ref"], "approver_ref")
        operator_principal = _principal_ref(
            event["operator_principal_ref"],
            "operator_principal_ref",
        )
        approver_principal = _principal_ref(
            event["approver_principal_ref"],
            "approver_principal_ref",
        )
        if operator_principal == approver_principal:
            raise ImmutableEvidenceError(
                "reconciliation requires separate principals"
            )
        for field in (
            "operator_tenant_binding_sha256",
            "approver_tenant_binding_sha256",
        ):
            if _sha256(event[field], field) != tenant_binding:
                raise ImmutableEvidenceError(
                    "reconciliation principal tenant binding differs"
                )
        for field in (
            "operator_principal_key_binding_sha256",
            "approver_principal_key_binding_sha256",
        ):
            if _sha256(event[field], field) != principal_key_binding:
                raise ImmutableEvidenceError(
                    "reconciliation principal key binding differs"
                )
    operation_binding = {
        "correlation_id": str(correlation),
        "actor_ref": actor,
        "actor_principal_ref": actor_principal,
        "tenant_binding_sha256": tenant_binding,
        "principal_key_binding_sha256": principal_key_binding,
        "tool_id": tool,
        "role_id": role,
        "action": event["action"],
        "business_case_type_id": business_case_type_id,
        "catalog_version": catalog_version,
        "manifest_sha256": manifest_sha256,
    }
    expected_idempotency = hashlib.sha256(
        canonical_json_bytes(operation_binding)
    ).hexdigest()
    if event["idempotency_key_sha256"] != expected_idempotency:
        raise ImmutableEvidenceError("idempotency binding is invalid")
    expected_delivery = _delivery_key(event)
    if event["delivery_key_sha256"] != expected_delivery:
        raise ImmutableEvidenceError("delivery binding is invalid")
    expected_event_id = _event_id(event)
    if event["event_id"] != expected_event_id:
        raise ImmutableEvidenceError("event identity is invalid")


def _reject_sensitive(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise ImmutableEvidenceError("JSON object keys must be strings")
            if key.lower() in _FORBIDDEN_KEYS:
                raise ImmutableEvidenceError(f"sensitive evidence field is forbidden: {path}.{key}")
            _reject_sensitive(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_sensitive(item, f"{path}[{index}]")
    elif isinstance(value, str):
        if (
            _RAW_UUID.search(value)
            or _EMAIL.search(value)
            or _JWT.search(value)
            or "-----BEGIN " in value
            or value.lower().startswith("bearer ")
        ):
            raise ImmutableEvidenceError(
                f"sensitive evidence value is forbidden: {path}"
            )
        return
    elif value is None or type(value) in {int, bool}:
        return
    else:
        raise ImmutableEvidenceError(f"unsupported evidence value at {path}")


def _key_material(key_version: Any, key: Any) -> tuple[int, bytes]:
    if type(key_version) is not int or key_version < 1:
        raise ImmutableEvidenceError("key_version must be a positive integer")
    if type(key) is not bytes or len(key) < 32:
        raise ImmutableEvidenceError("reference key must contain at least 32 bytes")
    return key_version, key


def _correlation_ref(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _CORRELATION_REF.fullmatch(value):
        raise ImmutableEvidenceError(f"{field} must be an opaque correlation reference")
    return value


def _trusted_correlation_ref(
    value: Any, field: str
) -> _VerifiedCorrelationRef:
    if (
        type(value) is not _VerifiedCorrelationRef
        or not _CORRELATION_REF.fullmatch(str(value))
    ):
        raise ImmutableEvidenceError(
            f"{field} must be created by correlation_ref"
        )
    return value


def _trusted_actor_ref(value: Any, field: str) -> _VerifiedActorRef:
    if (
        type(value) is not _VerifiedActorRef
        or not _ACTOR_REF.fullmatch(str(value))
    ):
        raise ImmutableEvidenceError(f"{field} must be created by actor_ref")
    return value


def _same_principal(left: Any, right: Any) -> bool:
    first = _trusted_actor_ref(left, "principal_ref")
    second = _trusted_actor_ref(right, "principal_ref")
    if first._tenant_binding_sha256 != second._tenant_binding_sha256:
        raise ImmutableEvidenceError("principal tenant binding differs")
    if (
        first._principal_key_binding_sha256
        != second._principal_key_binding_sha256
    ):
        raise ImmutableEvidenceError("principal key binding differs")
    return first._principal_ref == second._principal_ref


def _identifier(value: Any, field: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ImmutableEvidenceError(f"{field} is invalid")
    if _RAW_UUID.fullmatch(value):
        raise ImmutableEvidenceError(f"{field} cannot contain a raw identity")
    return value


def _pattern_identifier(
    value: Any,
    field: str,
    pattern: re.Pattern[str],
) -> str:
    if type(value) is not str or not pattern.fullmatch(value):
        raise ImmutableEvidenceError(f"{field} is invalid")
    return value


def _trusted_identifier_registry(
    value: Any,
) -> TypedIdentifierRegistry:
    if (
        type(value) is not TypedIdentifierRegistry
        or value._factory_token is not _IDENTIFIER_REGISTRY_FACTORY_TOKEN
    ):
        raise ImmutableEvidenceError(
            "identifier registry must be factory verified"
        )
    return value


def _registered_identifier(
    value: Any,
    field: str,
    pattern: re.Pattern[str],
    registered_values: frozenset[str],
) -> str:
    if (
        type(value) is not str
        or not pattern.fullmatch(value)
        or value not in registered_values
    ):
        raise ImmutableEvidenceError(
            f"{field} is not a registered typed identifier"
        )
    return value


def _result_code(phase: Any, value: Any) -> str:
    allowed = {
        "outcome": _SUCCESS_OUTCOME_CODES | {_UNCERTAIN_OUTCOME_CODE, "failed"},
        "readback": _SUCCESS_READBACK_CODES | {"failed"},
        "reconciliation_closed": frozenset({"reconciled", "failed"}),
    }
    if type(value) is not str or value not in allowed.get(phase, frozenset()):
        raise ImmutableEvidenceError(f"{phase} result_code is invalid")
    return value


def _reason_code(value: Any) -> str:
    if type(value) is not str or value not in _RECONCILIATION_REASONS:
        raise ImmutableEvidenceError("reconciliation reason code is invalid")
    return value


def _event_sha256_sequence(
    value: Any, field: str, *, allow_empty: bool
) -> tuple[str, ...]:
    if type(value) is not tuple or (not allow_empty and not value):
        raise ImmutableEvidenceError(f"{field} is invalid")
    return tuple(_sha256(item, field) for item in value)


def _sha256(value: Any, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ImmutableEvidenceError(f"{field} is invalid")
    return value


def _actor_ref(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _ACTOR_REF.fullmatch(value):
        raise ImmutableEvidenceError(f"{field} is invalid")
    return str(value)


def _principal_ref(value: Any, field: str) -> str:
    if type(value) is not str or not _PRINCIPAL_REF.fullmatch(value):
        raise ImmutableEvidenceError(f"{field} is invalid")
    return value


def _claim_ref(value: Any, field: str = "claim_id") -> str:
    if type(value) is not str or not _CLAIM_REF.fullmatch(value):
        raise ImmutableEvidenceError(f"{field} is invalid")
    return value


def _uuid_text(value: Any, field: str) -> str:
    if type(value) is not str:
        raise ImmutableEvidenceError(f"{field} is invalid")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ImmutableEvidenceError(f"{field} is invalid") from exc
    if str(parsed) != value.lower():
        raise ImmutableEvidenceError(f"{field} must be canonical")
    return str(parsed)


def _utc_seconds(value: Any) -> str:
    if type(value) is not str or not _UTC_SECONDS.fullmatch(value):
        raise ImmutableEvidenceError("occurred_at is invalid")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise ImmutableEvidenceError("occurred_at is invalid") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ImmutableEvidenceError("occurred_at is invalid")
    return value


def _etags(
    value: Mapping[str, str],
    hmac_key: bytes,
    key_version: int,
    tenant_binding_sha256: str,
) -> dict[str, str]:
    if type(hmac_key) is not bytes or len(hmac_key) < 32:
        raise ImmutableEvidenceError("ETag HMAC key must be at least 32 bytes")
    if type(key_version) is not int or key_version < 1:
        raise ImmutableEvidenceError("ETag HMAC key version is invalid")
    tenant_binding = _sha256(
        tenant_binding_sha256, "tenant_binding_sha256"
    )
    if not isinstance(value, Mapping) or len(value) > 16:
        raise ImmutableEvidenceError("etags are invalid")
    result: dict[str, str] = {}
    for key, etag in value.items():
        safe_key = _identifier(key, "etag key")
        if safe_key not in ETAG_KEYS:
            raise ImmutableEvidenceError("ETag key is not registered")
        if type(etag) is not str or not etag or len(etag) > 256:
            raise ImmutableEvidenceError("etag value is invalid")
        _reject_sensitive(etag, f"$.etags.{safe_key}")
        digest = hmac.new(
            hmac_key,
            b"nac.etag-evidence.v1\x00"
            + tenant_binding.encode("ascii")
            + b"\x00k"
            + str(key_version).encode("ascii")
            + b"\x00"
            + safe_key.encode("ascii")
            + b"\x00"
            + etag.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        result[safe_key] = f"hmac-sha256:k{key_version}:" + digest
    return dict(sorted(result.items()))


def _validate_etag_hashes(value: Any) -> None:
    if not isinstance(value, Mapping) or len(value) > 16:
        raise ImmutableEvidenceError("ETag hashes are invalid")
    for key, etag_hash in value.items():
        safe_key = _identifier(key, "etag key")
        if safe_key not in ETAG_KEYS:
            raise ImmutableEvidenceError("ETag key is not registered")
        if type(etag_hash) is not str:
            raise ImmutableEvidenceError("ETag hash is invalid")
        match = re.fullmatch(
            r"hmac-sha256:k([1-9][0-9]*):([0-9a-f]{64})",
            etag_hash,
        )
        if match is None:
            raise ImmutableEvidenceError("ETag hash is invalid")


def _publication_progress(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if value is None:
        return {
            "stage": "not-applicable",
            "acknowledged_event_sha256s": [],
            "anchor_ref_sha256": None,
            "signature_ref_sha256": None,
            "worm_receipt_ref_sha256": None,
        }
    expected_fields = {
        "stage",
        "acknowledged_event_sha256s",
        "anchor_ref_sha256",
        "signature_ref_sha256",
        "worm_receipt_ref_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != expected_fields:
        raise ImmutableEvidenceError("publication progress is invalid")
    stage = value["stage"]
    if stage not in {
        "outbox-snapshot",
        "broker-in-flight",
        "broker-complete",
        "anchor-in-flight",
        "anchor-readback-in-flight",
        "anchor-readback-complete",
        "worm-commit-in-flight",
        "worm-readback-in-flight",
        "worm-readback-complete",
    }:
        raise ImmutableEvidenceError("publication progress stage is invalid")
    acknowledged = value["acknowledged_event_sha256s"]
    if not isinstance(acknowledged, (list, tuple)):
        raise ImmutableEvidenceError("publication progress acknowledgements are invalid")
    hashes = [
        _sha256(item, "acknowledged_event_sha256")
        for item in acknowledged
    ]
    if len(hashes) != len(set(hashes)):
        raise ImmutableEvidenceError(
            "publication progress acknowledgements are not unique"
        )
    optional_hashes: dict[str, str | None] = {}
    for field in (
        "anchor_ref_sha256",
        "signature_ref_sha256",
        "worm_receipt_ref_sha256",
    ):
        item = value[field]
        optional_hashes[field] = (
            None if item is None else _sha256(item, field)
        )
    stage_index = _PUBLICATION_STAGE_ORDER[stage]
    anchor_index = _PUBLICATION_STAGE_ORDER["anchor-readback-in-flight"]
    worm_index = _PUBLICATION_STAGE_ORDER["worm-readback-in-flight"]
    if stage_index >= _PUBLICATION_STAGE_ORDER["broker-complete"] and not hashes:
        raise ImmutableEvidenceError(
            "completed broker stage requires acknowledgements"
        )
    if (stage_index >= anchor_index) != (
        optional_hashes["anchor_ref_sha256"] is not None
        and optional_hashes["signature_ref_sha256"] is not None
    ):
        raise ImmutableEvidenceError(
            "anchor reference does not match publication stage"
        )
    if (stage_index >= worm_index) != (
        optional_hashes["worm_receipt_ref_sha256"] is not None
    ):
        raise ImmutableEvidenceError(
            "WORM reference does not match publication stage"
        )
    return {
        "stage": stage,
        "acknowledged_event_sha256s": hashes,
        **optional_hashes,
    }



_PUBLICATION_STAGE_ORDER = {
    "outbox-snapshot": 0,
    "broker-in-flight": 1,
    "broker-complete": 2,
    "anchor-in-flight": 3,
    "anchor-readback-in-flight": 4,
    "anchor-readback-complete": 5,
    "worm-commit-in-flight": 6,
    "worm-readback-in-flight": 7,
    "worm-readback-complete": 8,
}


def _validate_publication_progress_advance(
    previous: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> None:
    previous_stage = _PUBLICATION_STAGE_ORDER[previous["stage"]]
    candidate_stage = _PUBLICATION_STAGE_ORDER[candidate["stage"]]
    if candidate_stage < previous_stage:
        raise ImmutableEvidenceError("publication progress cannot regress")
    if candidate_stage > previous_stage + 1:
        raise ImmutableEvidenceError("publication progress cannot skip stages")
    prior_acks = previous["acknowledged_event_sha256s"]
    current_acks = candidate["acknowledged_event_sha256s"]
    if current_acks[: len(prior_acks)] != prior_acks:
        raise ImmutableEvidenceError(
            "publication acknowledgements are not append-only"
        )
    for field in (
        "anchor_ref_sha256",
        "signature_ref_sha256",
        "worm_receipt_ref_sha256",
    ):
        prior = previous[field]
        current = candidate[field]
        if prior is not None and current != prior:
            raise ImmutableEvidenceError(
                "publication reference cannot be replaced"
            )


def _validate_publication_progress_event_binding(
    progress: Mapping[str, Any],
    event_sha256s: tuple[str, ...],
) -> None:
    expected = _event_sha256_sequence(
        event_sha256s, "publication_event_sha256s", allow_empty=False
    )
    acknowledged = tuple(progress["acknowledged_event_sha256s"])
    if acknowledged != expected[: len(acknowledged)]:
        raise ImmutableEvidenceError(
            "publication acknowledgements do not match claimed event sequence"
        )
    if (
        _PUBLICATION_STAGE_ORDER[progress["stage"]]
        >= _PUBLICATION_STAGE_ORDER["broker-complete"]
        and acknowledged != expected
    ):
        raise ImmutableEvidenceError(
            "completed broker stage requires the full claimed event sequence"
        )


def _opaque_reference(
    value: Any,
    field: str,
    pattern: re.Pattern[str],
) -> str:
    if type(value) is not str or not pattern.fullmatch(value):
        raise ImmutableEvidenceError(f"{field} is not an opaque reference")
    return value


def _publication_operation_key(operation: str, chain_head_sha256: str) -> str:
    if operation not in {"signature-anchor", "worm-commit"}:
        raise ImmutableEvidenceError("publication operation is invalid")
    chain_head = _sha256(chain_head_sha256, "chain_head_sha256")
    return hashlib.sha256(
        b"nac.immutable-evidence-publication-operation.v1\x00"
        + operation.encode("ascii")
        + b"\x00"
        + chain_head.encode("ascii")
    ).hexdigest()


def _reference_sha256(value: Any) -> str:
    if type(value) is not str:
        raise ImmutableEvidenceError("receipt reference is invalid")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _delivery_key(event: Mapping[str, Any]) -> str:
    delivery_payload = dict(event)
    delivery_payload.pop("event_id", None)
    delivery_payload.pop("delivery_key_sha256", None)
    return hashlib.sha256(
        b"nac.delivery-key.v1\x00"
        + canonical_json_bytes(delivery_payload)
    ).hexdigest()


def _event_id(event: Mapping[str, Any]) -> str:
    identity_payload = dict(event)
    identity_payload.pop("event_id", None)
    return "event-" + hashlib.sha256(canonical_json_bytes(identity_payload)).hexdigest()
