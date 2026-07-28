from __future__ import annotations

import hashlib
import inspect
import json
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_runtime.azure_blob_worm import (  # noqa: E402
    LIVE_STATUS,
    S6B_STATUS,
    AzureBlobContainerPolicy,
    AzureBlobImmutabilityPolicySnapshot,
    AzureBlobProviderContext,
    AzureBlobPutResult,
    AzureBlobVersionItem,
    AzureBlobWormError,
    AzureBlobWormJournal,
    FakeAzureBlobWormTransport,
    azure_provider_context_binding_sha256,
    minimum_retention_days,
    prepare_irreversible_lock_plan,
    verify_irreversible_lock_evidence,
    worm_commit_idempotency_key,
)
from nac_runtime.immutable_evidence import (  # noqa: E402
    REGISTERED_BUSINESS_CASE_TYPE_IDS,
    REGISTERED_CATALOG_VERSIONS,
    ZERO_HASH,
    EvidenceRecord,
    InMemoryEvidenceOutbox,
    WormJournalPort,
    actor_ref,
    build_event,
    canonical_json_bytes,
    correlation_ref,
    typed_identifier_registry,
)


TENANT_ID = "11111111-1111-4111-8111-111111111111"
ACTOR_OBJECT_ID = "22222222-2222-4222-8222-222222222222"
SOURCE_OBJECT_ID = "33333333-3333-4333-8333-333333333333"
ACTOR_KEY = b"actor-key-for-immutable-evidence"
PRINCIPAL_KEY = b"stable-principal-binding-key-0001"
CATALOG_VERSION = next(iter(REGISTERED_CATALOG_VERSIONS))
IDENTIFIER_REGISTRY = typed_identifier_registry(
    business_case_type_ids=REGISTERED_BUSINESS_CASE_TYPE_IDS,
    catalog_versions=REGISTERED_CATALOG_VERSIONS,
)
ENCRYPTION_SCOPE = "nac-worm-tenant-a"
CONTAINER_NAME = "nac-worm-tenant-a"
CMK_REF_SHA256 = "c" * 64

PROVIDER_TENANT_ID = "44444444-4444-4444-8444-444444444444"
PROVIDER_SUBSCRIPTION_ID = "/subscriptions/55555555-5555-4555-8555-555555555555"
PROVIDER_RESOURCE_ID = (
    PROVIDER_SUBSCRIPTION_ID
    + "/resourceGroups/rg-nac-worm/providers/Microsoft.Storage/"
    + "storageAccounts/stnacwormoffline001"
)
PROVIDER_TENANT_BINDING_SHA256 = hashlib.sha256(
    ("nac.azure-provider-tenant.v1|" + PROVIDER_TENANT_ID).encode("ascii")
).hexdigest()
PROVIDER_SUBSCRIPTION_BINDING_SHA256 = hashlib.sha256(
    ("nac.azure-subscription-resource.v1|" + PROVIDER_SUBSCRIPTION_ID).encode("ascii")
).hexdigest()
PROVIDER_RESOURCE_BINDING_SHA256 = hashlib.sha256(
    ("nac.azure-storage-resource.v1|" + PROVIDER_RESOURCE_ID).encode("ascii")
).hexdigest()
PROVIDER_CONTEXT = AzureBlobProviderContext(
    tenant_id=PROVIDER_TENANT_ID,
    subscription_resource_id=PROVIDER_SUBSCRIPTION_ID,
    resource_id=PROVIDER_RESOURCE_ID,
    readback_source="azure-subscription-resource-tenant-readback",
)
PROVIDER_CONTEXT_BINDING_SHA256 = azure_provider_context_binding_sha256(
    PROVIDER_CONTEXT
)

class AzureBlobWormJournalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actor = actor_ref(
            tenant_id=TENANT_ID,
            actor_object_id=ACTOR_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
            principal_key=PRINCIPAL_KEY,
        )
        cls.correlation = correlation_ref(
            tenant_id=TENANT_ID,
            source_object_id=SOURCE_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
        )

    def setUp(self) -> None:
        self.records = self._normal_chain("2026-07-28T09:00:00Z")
        self.tenant_binding = self.records[0].event["tenant_binding_sha256"]
        self.anchor = self._anchor(self.records)
        self.idempotency_key = worm_commit_idempotency_key(
            self.records[-1].event_sha256
        )
        self.policy = AzureBlobContainerPolicy(
            default_immutability_policy_mode="Locked",
            default_retention_days=3653,
            legal_hold_capable=True,
            legal_hold_capability_source="container-policy-properties",
            encryption_scope=ENCRYPTION_SCOPE,
            encryption_key_source="Microsoft.Keyvault",
            customer_managed_key_ref_sha256=CMK_REF_SHA256,
            provider_tenant_binding_sha256=PROVIDER_TENANT_BINDING_SHA256,
            provider_subscription_binding_sha256=(
                PROVIDER_SUBSCRIPTION_BINDING_SHA256
            ),
            provider_resource_binding_sha256=PROVIDER_RESOURCE_BINDING_SHA256,
            provider_context_binding_sha256=PROVIDER_CONTEXT_BINDING_SHA256,
            provider_context_binding_source="azure-subscription-resource-tenant-readback",
        )
        self.transport = FakeAzureBlobWormTransport(
            container_name=CONTAINER_NAME,
            tenant_binding_sha256=self.tenant_binding,
            policy=self.policy,
            provider_context=PROVIDER_CONTEXT,
        )
        self.journal = AzureBlobWormJournal(
            transport=self.transport,
            container_name=CONTAINER_NAME,
            tenant_binding_sha256=self.tenant_binding,
            encryption_scope=ENCRYPTION_SCOPE,
            customer_managed_key_ref_sha256=CMK_REF_SHA256,
            expected_provider_context_binding_sha256=(
                PROVIDER_CONTEXT_BINDING_SHA256
            ),
        )

    def _normal_chain(
        self, occurred_at: str, *, retention_years: int = 10
    ) -> tuple[EvidenceRecord, ...]:
        outbox = InMemoryEvidenceOutbox()
        for phase in ("intent", "outcome", "readback"):
            records = outbox.records(self.correlation)
            values: dict[str, Any] = {
                "correlation_id": self.correlation,
                "phase": phase,
                "sequence": len(records) + 1,
                "previous_event_sha256": (
                    records[-1].event_sha256 if records else ZERO_HASH
                ),
                "actor_ref_value": self.actor,
                "tool_id": "tool-nac-cli",
                "role_id": "role-migration-operator",
                "action": "schema_apply",
                "business_case_type_id": "immobilienkaufvertrag",
                "catalog_version": CATALOG_VERSION,
                "identifier_registry": IDENTIFIER_REGISTRY,
                "manifest_sha256": "a" * 64,
                "etag_hmac_key": ACTOR_KEY,
                "etag_hmac_key_version": 1,
                "occurred_at": occurred_at,
                "retention_years": retention_years,
            }
            if phase in {"outcome", "readback"}:
                values["result_code"] = "confirmed"
                values["etags"] = {"matter": "synthetic-state-etag"}
            outbox.append(build_event(**values))
        return outbox.records(self.correlation)

    @staticmethod
    def _anchor(records: tuple[EvidenceRecord, ...]) -> dict[str, Any]:
        head = records[-1].event_sha256
        return {
            "anchor_ref": f"anchor-v1-{head}",
            "signature_ref": f"signature-v1-{head}",
            "record_count": len(records),
            "first_event_sha256": records[0].event_sha256,
            "last_event_sha256": head,
            "head_sha256": head,
        }

    def test_status_and_port_surface_remain_exactly_offline(self) -> None:
        self.assertEqual(S6B_STATUS, "S6B_AZURE_WORM_ADAPTER_READY_OFFLINE")
        self.assertEqual(LIVE_STATUS, "BLOCKED_PENDING_S7_APPROVAL")
        self.assertEqual(
            inspect.signature(AzureBlobWormJournal.commit),
            inspect.signature(WormJournalPort.commit),
        )
        self.assertEqual(
            inspect.signature(AzureBlobWormJournal.readback),
            inspect.signature(WormJournalPort.readback),
        )
        self.assertEqual(self.transport.network_calls, 0)
        self.assertEqual(self.transport.azure_calls, 0)
        self.assertEqual(self.transport.credential_reads, 0)

    def test_commit_is_create_only_idempotent_and_fully_read_back(self) -> None:
        receipt = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        retry = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )

        self.assertEqual(receipt, retry)
        self.assertEqual(set(receipt), {"receipt_ref", "head_sha256"})
        self.assertEqual(receipt["head_sha256"], self.records[-1].event_sha256)
        self.assertEqual(self.transport.put_calls, 2)
        self.assertEqual(self.transport.create_effects, 1)
        self.assertTrue(
            all(call["if_none_match"] == "*" for call in self.transport.put_history)
        )

        readback = self.journal.readback(receipt["receipt_ref"])
        self.assertEqual(
            readback,
            {
                **receipt,
                "retention_years": 10,
                "legal_hold_capable": True,
            },
        )
        stored = json.loads(
            self.transport.blob_snapshot(receipt["receipt_ref"]).body.decode("utf-8")
        )
        self.assertEqual(stored["record_count"], 3)
        self.assertEqual(
            [item["event_sha256"] for item in stored["records"]],
            [record.event_sha256 for record in self.records],
        )
        self.assertEqual(stored["anchor"], self.anchor)
        self.assertNotIn(TENANT_ID, json.dumps(stored, sort_keys=True))

    def test_same_idempotency_key_cannot_create_conflicting_payload(self) -> None:
        self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        other_records = self._normal_chain("2026-07-28T09:00:01Z")

        with self.assertRaises(AzureBlobWormError):
            self.journal.commit(
                other_records,
                self._anchor(other_records),
                idempotency_key_sha256=self.idempotency_key,
            )

        self.assertEqual(self.transport.create_effects, 1)

    def test_full_readback_rejects_body_metadata_and_chain_tampering(self) -> None:
        receipt = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        original = self.transport.blob_snapshot(receipt["receipt_ref"])
        payload = json.loads(original.body.decode("utf-8"))
        payload["records"][1]["event"]["tool_id"] = "tool-mutated"
        self.transport.replace_blob_for_test(
            receipt["receipt_ref"],
            body=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            ),
        )

        with self.assertRaises(AzureBlobWormError):
            self.journal.readback(receipt["receipt_ref"])

        self.transport.replace_blob_for_test(
            receipt["receipt_ref"],
            body=original.body,
            metadata={**original.metadata, "nac_head_sha256": "f" * 64},
        )
        with self.assertRaises(AzureBlobWormError):
            self.journal.readback(receipt["receipt_ref"])

    def test_policy_retention_legal_hold_encryption_and_tenant_are_fail_closed(
        self,
    ) -> None:
        variants = {
            "policy": replace(
                self.policy, default_immutability_policy_mode="Unlocked"
            ),
            "retention": replace(self.policy, default_retention_days=3649),
            "legal_hold": replace(self.policy, legal_hold_capable=False),
            "encryption": replace(
                self.policy, encryption_scope="foreign-encryption-scope"
            ),
            "tenant": replace(
                self.policy, provider_context_binding_sha256="f" * 64
            ),
            "tenant_source": replace(
                self.policy,
                provider_context_binding_source="self-asserted",
            ),
        }
        for name, policy in variants.items():
            with self.subTest(name=name):
                transport = FakeAzureBlobWormTransport(
                    container_name=CONTAINER_NAME,
                    tenant_binding_sha256=self.tenant_binding,
                    policy=policy,
            provider_context=PROVIDER_CONTEXT,
                )
                journal = AzureBlobWormJournal(
                    transport=transport,
                    container_name=CONTAINER_NAME,
                    tenant_binding_sha256=self.tenant_binding,
                    encryption_scope=ENCRYPTION_SCOPE,
                    customer_managed_key_ref_sha256=CMK_REF_SHA256,
            expected_provider_context_binding_sha256=(
                PROVIDER_CONTEXT_BINDING_SHA256
            ),
                )
                with self.assertRaises(AzureBlobWormError):
                    journal.commit(
                        self.records,
                        self.anchor,
                        idempotency_key_sha256=self.idempotency_key,
                    )
                self.assertEqual(transport.put_calls, 0)
                self.assertEqual(transport.create_effects, 0)

    def test_readback_rechecks_policy_and_reports_stronger_retention(self) -> None:
        receipt = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        self.transport.return_next(
            "get_container_policy",
            replace(self.policy, default_retention_days=4018)
        )
        self.assertEqual(
            self.journal.readback(receipt["receipt_ref"])["retention_years"],
            11,
        )

        self.transport.replace_policy_for_test(
            replace(self.policy, default_immutability_policy_mode="Unlocked")
        )
        with self.assertRaises(AzureBlobWormError):
            self.journal.readback(receipt["receipt_ref"])

    def test_event_tenant_binding_must_match_dedicated_container(self) -> None:
        journal = AzureBlobWormJournal(
            transport=self.transport,
            container_name=CONTAINER_NAME,
            tenant_binding_sha256="f" * 64,
            encryption_scope=ENCRYPTION_SCOPE,
            customer_managed_key_ref_sha256=CMK_REF_SHA256,
            expected_provider_context_binding_sha256=(
                PROVIDER_CONTEXT_BINDING_SHA256
            ),
        )

        with self.assertRaises(AzureBlobWormError):
            journal.commit(
                self.records,
                self.anchor,
                idempotency_key_sha256=self.idempotency_key,
            )
        self.assertEqual(self.transport.create_effects, 0)

    def test_provider_failures_are_fully_redacted_without_exception_chain(
        self,
    ) -> None:
        secret = "Bearer provider-secret tenant-real.example"
        self.transport.fail_next(
            "put_blob_if_absent",
            RuntimeError(secret),
        )

        with self.assertRaises(AzureBlobWormError) as caught:
            self.journal.commit(
                self.records,
                self.anchor,
                idempotency_key_sha256=self.idempotency_key,
            )

        rendered = str(caught.exception) + repr(caught.exception)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("Bearer", rendered)
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)

    def test_fake_transport_is_offline_and_returns_defensive_copies(self) -> None:
        receipt = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        first = self.transport.blob_snapshot(receipt["receipt_ref"])
        mutable = dict(first.metadata)
        mutable["nac_head_sha256"] = "f" * 64
        second = self.transport.blob_snapshot(receipt["receipt_ref"])

        self.assertNotEqual(mutable, second.metadata)
        self.assertEqual(self.transport.network_calls, 0)
        self.assertEqual(self.transport.azure_calls, 0)
        self.assertEqual(self.transport.credential_reads, 0)

    def _new_stack(
        self,
    ) -> tuple[FakeAzureBlobWormTransport, AzureBlobWormJournal]:
        transport = FakeAzureBlobWormTransport(
            container_name=CONTAINER_NAME,
            tenant_binding_sha256=self.tenant_binding,
            policy=self.policy,
            provider_context=PROVIDER_CONTEXT,
        )
        journal = AzureBlobWormJournal(
            transport=transport,
            container_name=CONTAINER_NAME,
            tenant_binding_sha256=self.tenant_binding,
            encryption_scope=ENCRYPTION_SCOPE,
            customer_managed_key_ref_sha256=CMK_REF_SHA256,
            expected_provider_context_binding_sha256=(
                PROVIDER_CONTEXT_BINDING_SHA256
            ),
        )
        return transport, journal

    def test_commit_requires_exact_s6a_worm_operation_key(self) -> None:
        self.assertEqual(minimum_retention_days(10), 3653)
        self.assertEqual(minimum_retention_days(11), 4018)
        self.assertEqual(
            self.idempotency_key,
            worm_commit_idempotency_key(self.records[-1].event_sha256),
        )
        other_records = self._normal_chain("2026-07-28T09:00:01Z")
        for candidate in (
            "d" * 64,
            worm_commit_idempotency_key(other_records[-1].event_sha256),
        ):
            with self.subTest(candidate=candidate):
                with self.assertRaises(AzureBlobWormError):
                    self.journal.commit(
                        self.records,
                        self.anchor,
                        idempotency_key_sha256=candidate,
                    )
        self.assertEqual(self.transport.create_effects, 0)
        self.assertEqual(self.transport.policy_calls, 0)
        self.assertEqual(self.transport.put_calls, 0)
        self.assertEqual(self.transport.get_calls, 0)

    def test_post_create_response_loss_recovers_via_conflict_read(self) -> None:
        self.transport.lose_next_put_response()
        with self.assertRaises(AzureBlobWormError):
            self.journal.commit(
                self.records,
                self.anchor,
                idempotency_key_sha256=self.idempotency_key,
            )
        self.assertEqual(self.transport.create_effects, 1)

        receipt = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        self.assertEqual(receipt["head_sha256"], self.records[-1].event_sha256)
        self.assertEqual(self.transport.create_effects, 1)

    def test_concurrent_same_and_different_payloads_never_overwrite(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(
                    self.journal.commit,
                    self.records,
                    self.anchor,
                    idempotency_key_sha256=self.idempotency_key,
                )
                for _ in range(8)
            ]
        receipts = [future.result() for future in futures]
        self.assertTrue(all(receipt == receipts[0] for receipt in receipts))
        self.assertEqual(self.transport.create_effects, 1)

        other_records = self._normal_chain("2026-07-28T09:00:01Z")
        barrier = threading.Barrier(2)

        def commit(records: tuple[EvidenceRecord, ...]) -> object:
            barrier.wait()
            try:
                return self.journal.commit(
                    records,
                    self._anchor(records),
                    idempotency_key_sha256=self.idempotency_key,
                )
            except AzureBlobWormError as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(commit, (self.records, other_records)))
        self.assertEqual(sum(isinstance(item, dict) for item in results), 1)
        self.assertEqual(
            sum(isinstance(item, AzureBlobWormError) for item in results), 1
        )
        self.assertEqual(self.transport.create_effects, 1)

    def test_conflict_read_failure_is_redacted_and_fail_closed(self) -> None:
        self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        self.transport.fail_next("get_blob", RuntimeError("provider-secret"))
        with self.assertRaises(AzureBlobWormError) as caught:
            self.journal.commit(
                self.records,
                self.anchor,
                idempotency_key_sha256=self.idempotency_key,
            )
        self.assertNotIn("provider-secret", repr(caught.exception))
        self.assertEqual(self.transport.create_effects, 1)

    def test_blob_version_policy_and_encryption_tamper_fail_closed(self) -> None:
        cases = (
            {"encryption_scope": "foreign-scope"},
            {"encryption_key_source": "Microsoft.Storage"},
            {"customer_managed_key_ref_sha256": "f" * 64},
            {"version_id": "not opaque version/id"},
            {"immutability_policy_mode": "Unlocked"},
            {"retention_until": "2026-07-29T09:00:00Z"},
            {"legal_hold_active": "true"},
        )
        for change in cases:
            with self.subTest(change=change):
                transport, journal = self._new_stack()
                receipt = journal.commit(
                    self.records,
                    self.anchor,
                    idempotency_key_sha256=self.idempotency_key,
                )
                transport.replace_blob_for_test(receipt["receipt_ref"], **change)
                with self.assertRaises(AzureBlobWormError):
                    journal.readback(receipt["receipt_ref"])

    def test_anchor_receipt_and_canonical_byte_tamper_fail_closed(self) -> None:
        for field in ("anchor", "receipt_ref", "canonical_bytes"):
            with self.subTest(field=field):
                transport, journal = self._new_stack()
                receipt = journal.commit(
                    self.records,
                    self.anchor,
                    idempotency_key_sha256=self.idempotency_key,
                )
                original = transport.blob_snapshot(receipt["receipt_ref"])
                payload = json.loads(original.body.decode("ascii"))
                if field == "anchor":
                    payload["anchor"]["head_sha256"] = "f" * 64
                elif field == "receipt_ref":
                    payload["receipt_ref"] = "worm-receipt-v1-" + "f" * 64
                body = (
                    original.body + b"\n"
                    if field == "canonical_bytes"
                    else json.dumps(
                        payload, sort_keys=True, separators=(",", ":")
                    ).encode("ascii")
                )
                transport.replace_blob_for_test(
                    receipt["receipt_ref"], body=body
                )
                with self.assertRaises(AzureBlobWormError):
                    journal.readback(receipt["receipt_ref"])

    def test_legal_hold_capability_is_derived_and_active_state_is_separate(
        self,
    ) -> None:
        receipt = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        snapshot = self.transport.blob_snapshot(receipt["receipt_ref"])
        self.assertFalse(snapshot.legal_hold_active)
        self.assertTrue(self.journal.readback(receipt["receipt_ref"])["legal_hold_capable"])

        self.transport.replace_blob_for_test(
            receipt["receipt_ref"], legal_hold_active=True
        )
        self.assertTrue(self.journal.readback(receipt["receipt_ref"])["legal_hold_capable"])

    def test_malformed_transport_results_are_fully_rejected(self) -> None:
        malformed_cases = (
            ("get_provider_context", object()),
            ("get_container_policy", object()),
            ("put_blob_if_absent", object()),
        )
        for operation, result in malformed_cases:
            with self.subTest(operation=operation):
                transport, journal = self._new_stack()
                transport.return_next(operation, result)
                with self.assertRaises(AzureBlobWormError):
                    journal.commit(
                        self.records,
                        self.anchor,
                        idempotency_key_sha256=self.idempotency_key,
                    )

        for operation, result in (
            ("list_blob_versions", (object(),)),
            ("get_blob", object()),
        ):
            with self.subTest(read_operation=operation):
                transport, journal = self._new_stack()
                receipt = journal.commit(
                    self.records,
                    self.anchor,
                    idempotency_key_sha256=self.idempotency_key,
                )
                transport.return_next(operation, result)
                with self.assertRaises(AzureBlobWormError):
                    journal.readback(receipt["receipt_ref"])

    def test_malformed_typed_transport_fields_are_not_normalized(self) -> None:
        class PretendsLocked:
            def __str__(self) -> str:
                return "Locked"

        transport, journal = self._new_stack()
        transport.return_next(
            "get_container_policy",
            replace(
                self.policy,
                default_immutability_policy_mode=PretendsLocked(),
            ),
        )
        with self.assertRaises(AzureBlobWormError):
            journal.commit(
                self.records,
                self.anchor,
                idempotency_key_sha256=self.idempotency_key,
            )

        for result in (
            AzureBlobPutResult(status_code=201, etag='"etag"', version_id=None),
            AzureBlobPutResult(status_code=200, etag='"etag"', version_id=None),
        ):
            with self.subTest(put_result=result):
                transport, journal = self._new_stack()
                transport.return_next("put_blob_if_absent", result)
                with self.assertRaises(AzureBlobWormError):
                    journal.commit(
                        self.records,
                        self.anchor,
                        idempotency_key_sha256=self.idempotency_key,
                    )
                self.assertEqual(transport.create_effects, 0)

        for field, malformed in (
            ("version_id", 7),
            ("etag", object()),
            ("body", bytearray(b"not-provider-bytes")),
        ):
            with self.subTest(field=field):
                transport, journal = self._new_stack()
                receipt = journal.commit(
                    self.records,
                    self.anchor,
                    idempotency_key_sha256=self.idempotency_key,
                )
                snapshot = transport.blob_snapshot(receipt["receipt_ref"])
                transport.return_next(
                    "get_blob",
                    replace(snapshot, **{field: malformed}),
                )
                with self.assertRaises(AzureBlobWormError):
                    journal.readback(receipt["receipt_ref"])

    def test_create_conflict_and_public_readback_bind_one_version(self) -> None:
        receipt = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        snapshot = self.transport.blob_snapshot(receipt["receipt_ref"])
        retry = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        readback = self.journal.readback(receipt["receipt_ref"])

        self.assertEqual(retry, receipt)
        self.assertEqual(readback["receipt_ref"], receipt["receipt_ref"])
        self.assertEqual(
            [entry["version_id"] for entry in self.transport.get_history[:2]],
            [snapshot.version_id, snapshot.version_id],
        )
        self.assertEqual(
            self.transport.get_history[-1]["version_id"],
            snapshot.version_id,
        )
        self.assertNotIn(
            "version_id_binding", self.transport.get_history[-1]
        )
        replacement = "0" if receipt["receipt_ref"][-1] != "0" else "1"
        tampered_receipt = receipt["receipt_ref"][:-1] + replacement
        with self.assertRaises(AzureBlobWormError):
            self.journal.readback(tampered_receipt)

    def test_412_response_cannot_self_assert_a_version(self) -> None:
        self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        self.transport.return_next(
            "put_blob_if_absent",
            AzureBlobPutResult(
                status_code=412,
                etag=None,
                version_id="version-v1-" + "f" * 64,
            ),
        )
        with self.assertRaises(AzureBlobWormError):
            self.journal.commit(
                self.records,
                self.anchor,
                idempotency_key_sha256=self.idempotency_key,
            )

    def test_provider_tenant_readback_drift_fails_before_put(self) -> None:
        transport, journal = self._new_stack()
        transport.replace_policy_for_test(
            replace(
                self.policy,
                provider_context_binding_sha256="f" * 64,
            )
        )
        with self.assertRaises(AzureBlobWormError):
            journal.commit(
                self.records,
                self.anchor,
                idempotency_key_sha256=self.idempotency_key,
            )
        self.assertEqual(transport.put_calls, 0)

    def test_concurrent_distinct_valid_payloads_really_race_same_blob(self) -> None:
        transport, journal = self._new_stack()
        transport.block_next_puts(2)
        alternate_anchor = {
            **self.anchor,
            "anchor_ref": "anchor-v1-" + "e" * 64,
            "signature_ref": "signature-v1-" + "f" * 64,
        }

        def commit(anchor: dict[str, Any]) -> object:
            try:
                return journal.commit(
                    self.records,
                    anchor,
                    idempotency_key_sha256=self.idempotency_key,
                )
            except AzureBlobWormError as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(commit, (self.anchor, alternate_anchor)))

        self.assertEqual(transport.put_calls, 2)
        self.assertEqual(transport.create_effects, 1)
        self.assertEqual(sum(isinstance(item, dict) for item in results), 1)
        self.assertEqual(
            sum(isinstance(item, AzureBlobWormError) for item in results),
            1,
        )

    def test_future_event_time_and_retention_overflow_are_pre_put_safe(self) -> None:
        future_records = self._normal_chain("2099-01-01T00:00:00Z")
        future_anchor = self._anchor(future_records)
        future_key = worm_commit_idempotency_key(
            future_records[-1].event_sha256
        )
        receipt = self.journal.commit(
            future_records,
            future_anchor,
            idempotency_key_sha256=future_key,
        )
        retry = self.journal.commit(
            future_records,
            future_anchor,
            idempotency_key_sha256=future_key,
        )
        snapshot = self.transport.blob_snapshot(receipt["receipt_ref"])
        created_at = datetime.strptime(
            snapshot.created_at, "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        retention_until = datetime.strptime(
            snapshot.retention_until, "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        self.assertEqual(retry, receipt)
        self.assertEqual(
            retention_until,
            created_at + timedelta(days=3653),
        )
        self.assertEqual(self.transport.create_effects, 1)

        overflow_records = self._normal_chain(
            "2099-01-01T00:00:00Z", retention_years=10**20
        )
        overflow_anchor = self._anchor(overflow_records)
        overflow_key = worm_commit_idempotency_key(
            overflow_records[-1].event_sha256
        )
        overflow_transport, overflow_journal = self._new_stack()
        with self.assertRaises(AzureBlobWormError):
            overflow_journal.commit(
                overflow_records,
                overflow_anchor,
                idempotency_key_sha256=overflow_key,
            )
        self.assertEqual(overflow_transport.put_calls, 0)
        self.assertEqual(overflow_transport.create_effects, 0)
        retry_receipt = overflow_journal.commit(
            future_records,
            future_anchor,
            idempotency_key_sha256=future_key,
        )
        self.assertEqual(
            overflow_journal.commit(
                future_records,
                future_anchor,
                idempotency_key_sha256=future_key,
            ),
            retry_receipt,
        )
        self.assertEqual(overflow_transport.create_effects, 1)

    def test_malformed_event_time_is_pre_put_safe(self) -> None:
        event = dict(self.records[0].event)
        event["occurred_at"] = "2026-07-28 09:00:00"
        malformed_record = EvidenceRecord(
            event=event,
            event_sha256=hashlib.sha256(canonical_json_bytes(event)).hexdigest(),
        )
        malformed_records = (malformed_record,)
        malformed_anchor = self._anchor(malformed_records)
        malformed_key = worm_commit_idempotency_key(
            malformed_record.event_sha256
        )
        transport, journal = self._new_stack()

        with self.assertRaises(AzureBlobWormError):
            journal.commit(
                malformed_records,
                malformed_anchor,
                idempotency_key_sha256=malformed_key,
            )

        self.assertEqual(transport.put_calls, 0)
        self.assertEqual(transport.create_effects, 0)

    def test_fresh_provider_context_binds_tenant_subscription_and_resource(self) -> None:
        receipt = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        self.assertGreaterEqual(self.transport.provider_context_calls, 2)
        raw_evidence = self.transport.blob_snapshot(
            receipt["receipt_ref"]
        ).body.decode("ascii")
        for plaintext in (
            PROVIDER_TENANT_ID,
            PROVIDER_SUBSCRIPTION_ID,
            PROVIDER_RESOURCE_ID,
        ):
            self.assertNotIn(plaintext, raw_evidence)

        for field, replacement in (
            ("tenant_id", "66666666-6666-4666-8666-666666666666"),
            (
                "subscription_resource_id",
                "/subscriptions/77777777-7777-4777-8777-777777777777",
            ),
            (
                "resource_id",
                PROVIDER_RESOURCE_ID.replace(
                    "stnacwormoffline001", "stnacwormoffline002"
                ),
            ),
        ):
            with self.subTest(field=field):
                transport, journal = self._new_stack()
                transport.replace_provider_context_for_test(
                    replace(PROVIDER_CONTEXT, **{field: replacement})
                )
                with self.assertRaises(AzureBlobWormError):
                    journal.commit(
                        self.records,
                        self.anchor,
                        idempotency_key_sha256=self.idempotency_key,
                    )
                self.assertEqual(transport.put_calls, 0)

        self.transport.replace_provider_context_for_test(
            replace(
                PROVIDER_CONTEXT,
                tenant_id="88888888-8888-4888-8888-888888888888",
            )
        )
        with self.assertRaises(AzureBlobWormError):
            self.journal.readback(receipt["receipt_ref"])

    def test_201_and_412_resolve_only_raw_exact_version_ids(self) -> None:
        receipt = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        snapshot = self.transport.blob_snapshot(receipt["receipt_ref"])
        retry = self.journal.commit(
            self.records,
            self.anchor,
            idempotency_key_sha256=self.idempotency_key,
        )
        readback = self.journal.readback(receipt["receipt_ref"])
        self.assertEqual(retry, receipt)
        self.assertEqual(readback["receipt_ref"], receipt["receipt_ref"])
        self.assertEqual(
            {item["version_id"] for item in self.transport.get_history},
            {snapshot.version_id},
        )
        self.assertTrue(
            all(item["version_id"] for item in self.transport.get_history)
        )
        self.assertGreaterEqual(self.transport.list_versions_calls, 2)

    def test_412_version_discovery_rejects_none_ambiguous_and_foreign(self) -> None:
        for mode in ("none", "ambiguous", "foreign"):
            with self.subTest(mode=mode):
                transport, journal = self._new_stack()
                receipt = journal.commit(
                    self.records,
                    self.anchor,
                    idempotency_key_sha256=self.idempotency_key,
                )
                if mode == "none":
                    transport.return_next("list_blob_versions", ())
                elif mode == "ambiguous":
                    transport.clone_blob_version_for_test(
                        receipt["receipt_ref"],
                        version_id="version-v1-" + "d" * 64,
                    )
                else:
                    transport.replace_all_versions_with_foreign_for_test(
                        receipt["receipt_ref"],
                        version_id="version-v1-" + "e" * 64,
                    )
                with self.assertRaises(AzureBlobWormError):
                    journal.commit(
                        self.records,
                        self.anchor,
                        idempotency_key_sha256=self.idempotency_key,
                    )
                self.assertEqual(transport.create_effects, 1)
    def test_irreversible_lock_plan_rejects_target_etag_and_hash_drift(
        self,
    ) -> None:
        pre = AzureBlobImmutabilityPolicySnapshot(
            target_resource_id_sha256="1" * 64,
            provider_context_binding_sha256=(
                PROVIDER_CONTEXT_BINDING_SHA256
            ),
            policy_resource_id_sha256="2" * 64,
            policy_state="Unlocked",
            retention_days=3653,
            etag='"policy-etag-v1"',
        )
        plan = prepare_irreversible_lock_plan(
            pre,
            operator_ref="operator-v1-" + "3" * 64,
            approver_ref="approver-v1-" + "4" * 64,
        )
        with self.assertRaises(AzureBlobWormError):
            prepare_irreversible_lock_plan(
                pre,
                operator_ref="operator-v1-" + "7" * 64,
                approver_ref="approver-v1-" + "7" * 64,
            )
        post = replace(pre, policy_state="Locked", etag='"policy-etag-v2"')
        evidence = verify_irreversible_lock_evidence(plan, pre, post)
        self.assertEqual(evidence["result"], "LOCKED_READBACK_VERIFIED")

        cases = (
            (plan, pre, replace(post, target_resource_id_sha256="5" * 64)),
            (plan, replace(pre, etag='"stale-etag"'), post),
            ({**plan, "prepared_request_sha256": "6" * 64}, pre, post),
        )
        for candidate, candidate_pre, candidate_post in cases:
            with self.subTest(candidate=candidate):
                with self.assertRaises(AzureBlobWormError):
                    verify_irreversible_lock_evidence(
                        candidate,
                        candidate_pre,
                        candidate_post,
                    )
if __name__ == "__main__":
    unittest.main()
