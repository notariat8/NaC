from __future__ import annotations

import json
import unittest
from datetime import datetime
from pathlib import Path

from nac_bff.workbench_projection import (
    WorkbenchProjectionError,
    build_workbench_projection,
    serialize_workbench_projection,
    validate_workbench_projection,
    workbench_projection_content_sha256,
)


class WorkbenchProjectionTests(unittest.TestCase):
    def test_builds_explicit_server_authored_projection(self) -> None:
        payload = _projection()

        self.assertEqual(payload["schemaVersion"], "nac.workbench.snapshot/v1")
        self.assertEqual(payload["producer"]["id"], "nac-bff")
        self.assertEqual(payload["decisions"][0]["id"], "decision:001")
        self.assertEqual(payload["capabilities"][0]["decision"], "deny")
        self.assertEqual(payload["redaction"]["status"], "verified")
        self.assertEqual(
            validate_workbench_projection(
                payload,
                observed_at=_observed_at(),
            ),
            payload,
        )

    def test_wire_validator_rejects_missing_nested_and_unknown_fields(self) -> None:
        missing = _projection()
        del missing["tasks"]
        with self.assertRaisesRegex(WorkbenchProjectionError, "fields"):
            validate_workbench_projection(missing, observed_at=_observed_at())
        unknown = _projection()
        unknown["matter"]["internal"] = "must-not-pass"
        with self.assertRaisesRegex(WorkbenchProjectionError, "fields"):
            validate_workbench_projection(unknown, observed_at=_observed_at())

    def test_rejects_deny_snapshot_and_unbounded_deputy(self) -> None:
        with self.assertRaisesRegex(WorkbenchProjectionError, "deny"):
            _projection(access_override={"mode": "deny"})
        with self.assertRaisesRegex(WorkbenchProjectionError, "reason"):
            _projection(access_override={"mode": "deputy", "reason": ""})

    def test_rejects_invented_capability_and_authoritative_bpmn(self) -> None:
        with self.assertRaisesRegex(WorkbenchProjectionError, "deny-only"):
            _projection(capability_override={"decision": "allow"})
        with self.assertRaisesRegex(WorkbenchProjectionError, "not authoritative"):
            _projection(model_evidence_override={"authority": "authoritative"})

    def test_rejects_broken_references_and_stale_leases(self) -> None:
        with self.assertRaisesRegex(WorkbenchProjectionError, "current step"):
            _projection(matter_override={"currentStepId": "missing"})
        with self.assertRaisesRegex(WorkbenchProjectionError, "lease"):
            _projection(expires_at="2026-08-01T09:06:00Z")

    def test_rejects_unknown_fields_before_projection(self) -> None:
        with self.assertRaisesRegex(WorkbenchProjectionError, "fields"):
            _projection(matter_override={"internalClientName": "must-not-leak"})
        with self.assertRaisesRegex(WorkbenchProjectionError, "fields"):
            _projection(access_override={"operatorEmail": "must-not-leak@example.invalid"})

    def test_rejects_future_access_issue_time(self) -> None:
        with self.assertRaisesRegex(WorkbenchProjectionError, "future"):
            _projection(access_override={"issuedAt": "2026-08-01T09:02:00Z"})

    def test_rejects_access_bound_to_another_actor_scope(self) -> None:
        for access_override in (
            {"subjectId": "actor:synthetic:other"},
            {"role": "clerk"},
            {"workspaceId": "notary_team_02"},
            {"matterId": "NAC-SYN-MATTER-OTHER"},
            {"purpose": "view_other_matter"},
        ):
            with self.subTest(access_override=access_override):
                with self.assertRaisesRegex(WorkbenchProjectionError, "access scope binding mismatch"):
                    _projection(access_override=access_override)

    def test_shared_wire_conformance_rejects_duplicate_identifiers_and_milliseconds(self) -> None:
        fixture = _conformance_fixture()
        rejected = fixture["rejected"]
        duplicate_agent = {
            "id": rejected["duplicate_agent_id"],
            "label": "Duplikat",
            "status": "idle",
            "detail": "Muss abgelehnt werden.",
        }
        with self.assertRaisesRegex(WorkbenchProjectionError, "agents values are not unique"):
            _projection(agents_override=[_agent(), duplicate_agent])
        duplicate_step = {
            **_task(),
            "id": "task:002",
            "stepId": rejected["duplicate_step_id"],
        }
        with self.assertRaisesRegex(WorkbenchProjectionError, "task step values are not unique"):
            _projection(tasks_override=[_task(), duplicate_step])
        with self.assertRaisesRegex(WorkbenchProjectionError, "timestamp is not canonical"):
            _projection(generated_at=rejected["timestamp_with_milliseconds"])

    def test_requires_content_bound_redaction_attestation_and_opaque_references(self) -> None:
        token_identifier = "".join(
            _conformance_fixture()["rejected"]["token_shaped_identifier_parts"]
        )
        with self.assertRaisesRegex(WorkbenchProjectionError, "content binding"):
            _projection(redaction_override={"contentSha256": "f" * 64})
        with self.assertRaisesRegex(WorkbenchProjectionError, "prohibited sensitive text"):
            _projection(matter_override={"title": "Kontakt test@example.invalid"})
        with self.assertRaisesRegex(WorkbenchProjectionError, "prohibited sensitive text"):
            _projection(access_override={"mode": "deputy", "reason": "Token https://example.invalid"})
        with self.assertRaisesRegex(WorkbenchProjectionError, "sourceRef is invalid"):
            _projection(model_evidence_override={"sourceRef": "https://example.invalid/x?access_token=secret"})
        with self.assertRaisesRegex(WorkbenchProjectionError, "sourceRef is invalid"):
            _projection(model_evidence_override={"sourceRef": token_identifier})
        with self.assertRaisesRegex(WorkbenchProjectionError, "businessCaseTypeId is invalid"):
            _projection(matter_override={"businessCaseTypeId": token_identifier})

    def test_text_limit_uses_shared_utf16_code_units(self) -> None:
        maximum = _conformance_fixture()["limits"]["maximum_text_utf16_code_units"]
        accepted = "\U0001F600" * (maximum // 2)
        rejected = accepted + "\U0001F600"

        self.assertEqual(_projection(matter_override={"title": accepted})["matter"]["title"], accepted)
        with self.assertRaisesRegex(WorkbenchProjectionError, "matter.title is invalid"):
            _projection(matter_override={"title": rejected})

    def test_exact_compact_wire_serialization_matches_browser_budget(self) -> None:
        payload = _projection()
        wire = serialize_workbench_projection(payload)

        self.assertEqual(json.loads(wire), payload)
        self.assertNotIn(": ", wire)
        self.assertLessEqual(
            len(wire.encode("utf-8")),
            _conformance_fixture()["limits"]["maximum_snapshot_bytes"],
        )

    def test_rejects_projection_that_exceeds_shared_wire_budget(self) -> None:
        maximum = _conformance_fixture()["limits"]["maximum_snapshot_bytes"]
        self.assertEqual(maximum, 128 * 1024)
        long_text = "\U0001F600" * 128
        agents = [
            {"id": f"agent:{index}", "label": long_text, "status": "idle", "detail": long_text}
            for index in range(64)
        ]
        tasks = [
            {
                "id": f"task:{index}",
                "title": long_text,
                "status": long_text,
                "dueAt": None,
                "stepId": f"Step:{index}",
                "requiresApproval": True,
            }
            for index in range(64)
        ]
        with self.assertRaisesRegex(WorkbenchProjectionError, "wire size"):
            _projection(
                matter_override={"currentStepId": "Step:0"},
                tasks_override=tasks,
                agents_override=agents,
                attention_override=[
                    {
                        "id": f"attention:{index}",
                        "title": long_text,
                        "reason": long_text,
                        "severity": "warning",
                        "dueAt": None,
                        "taskId": f"task:{index}",
                    }
                    for index in range(64)
                ],
            )


def _projection(
    *,
    generated_at: str | None = None,
    expires_at: str = "2026-08-01T09:04:00Z",
    access_override: dict | None = None,
    matter_override: dict | None = None,
    capability_override: dict | None = None,
    model_evidence_override: dict | None = None,
    tasks_override: list[dict] | None = None,
    agents_override: list[dict] | None = None,
    attention_override: list[dict] | None = None,
    redaction_override: dict | None = None,
) -> dict:
    accepted = _conformance_fixture()["accepted"]
    binding = accepted["access_binding"]
    access = {
        "mode": "assigned",
        "decisionId": "access:001",
        "decisionVersion": "policy-v1",
        "subjectId": binding["subject_id"],
        "role": binding["role"],
        "workspaceId": binding["workspace_id"],
        "matterId": binding["matter_id"],
        "purpose": binding["purpose"],
        "issuedAt": "2026-08-01T09:00:00Z",
        "expiresAt": "2026-08-01T09:04:00Z",
        "reason": None,
    }
    access.update(access_override or {})
    matter = {
        "id": "NAC-SYN-MATTER-001",
        "businessCaseTypeId": "immobilienkaufvertrag",
        "title": "Synthetischer Immobilienkaufvertrag",
        "status": "Entwurf",
        "deadline": "2026-08-31T16:00:00Z",
        "currentStepId": "Task_EntwurfAbstimmen",
        "modelReference": {
            "kind": "bpmn",
            "modelKey": "Process_immobilienkaufvertrag",
            "sha256": "0" * 64,
        },
    }
    matter.update(matter_override or {})
    capability = {
        "id": "matter.decision.review",
        "mode": "approve",
        "decision": "deny",
        "reason": "Foundation is read-only.",
    }
    capability.update(capability_override or {})
    model_evidence = {
        "id": "evidence:model:001",
        "title": "BPMN model",
        "kind": "model_reference",
        "authority": "non_authoritative",
        "sourceSystem": "nac-git",
        "sourceRef": "Process_immobilienkaufvertrag",
        "sha256": "0" * 64,
    }
    model_evidence.update(model_evidence_override or {})
    return build_workbench_projection(
        generated_at=generated_at or accepted["generated_at"],
        expires_at=expires_at,
        producer_version="1.0.0",
        workspace_id=binding["workspace_id"],
        matter_id=binding["matter_id"],
        purpose=binding["purpose"],
        actor_id=binding["subject_id"],
        actor_role=binding["role"],
        access=access,
        matter=matter,
        tasks=tasks_override or [_task()],
        attention=attention_override or [{
            "id": "attention:001",
            "title": "Entwurf prüfen",
            "reason": "Notarielle Prüfung erforderlich",
            "severity": "warning",
            "dueAt": None,
            "taskId": "task:001",
        }],
        decisions=[{
            "id": "decision:001",
            "title": "Entwurf notariell prüfen",
            "status": "pending",
            "riskClass": "R4",
            "dueAt": None,
            "evidenceIds": ["evidence:audit:001"],
            "capabilityId": "matter.decision.review",
        }],
        evidence=[model_evidence, {
            "id": "evidence:audit:001",
            "title": "Redigierter Prüfauftrag",
            "kind": "audit",
            "authority": "authoritative",
            "sourceSystem": "nac-bff",
            "sourceRef": "audit:synthetic:001",
            "sha256": None,
        }],
        capabilities=[capability],
        agents=agents_override or [_agent()],
        redaction_verifier=lambda payload: _redaction_attestation(payload, redaction_override),
        observed_at=accepted["observed_at"],
    )


def _redaction_attestation(payload: dict, override: dict | None = None) -> dict:
    accepted = _conformance_fixture()["accepted"]
    attestation = {
        "status": "verified",
        "policyId": "nac-redaction",
        "policyVersion": "v1",
        "classifierId": "synthetic-redaction-verifier",
        "classifierVersion": "v1",
        "verifiedAt": accepted["redaction_verified_at"],
        "contentSha256": workbench_projection_content_sha256(payload),
    }
    attestation.update(override or {})
    return attestation


def _task() -> dict:
    return {
        "id": "task:001",
        "title": "Entwurf prüfen",
        "status": "Offen",
        "dueAt": None,
        "stepId": "Task_EntwurfAbstimmen",
        "requiresApproval": True,
    }


def _agent() -> dict:
    return {
        "id": "personal-assistance",
        "label": "Persönliche Assistenz",
        "status": "idle",
        "detail": "Keine Agentenaktion angefordert.",
    }


def _conformance_fixture() -> dict:
    path = Path(__file__).resolve().parents[1] / "workflows" / "fixtures" / "generic-workbench-conformance.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _observed_at() -> datetime:
    return datetime.fromisoformat(
        _conformance_fixture()["accepted"]["observed_at"].replace("Z", "+00:00")
    )


if __name__ == "__main__":
    unittest.main()
