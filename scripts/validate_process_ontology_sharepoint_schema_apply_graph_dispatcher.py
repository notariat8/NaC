#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
src_text = str(SRC)
if src_text in sys.path:
    sys.path.remove(src_text)
sys.path.insert(0, src_text)

from nac_m365_graph.graph_client import GraphHttpError  # noqa: E402
from notary_kg.process_ontology_schema_apply_binding import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_binding,
)
from notary_kg.process_ontology_schema_apply_graph_dispatcher import (  # noqa: E402
    SCHEMA_VERSION,
    run_process_ontology_sharepoint_schema_apply_graph_dispatcher,
    validate_process_ontology_sharepoint_schema_apply_graph_dispatcher,
    write_process_ontology_sharepoint_schema_apply_graph_dispatcher_artifact,
)
from notary_kg.process_ontology_schema_apply_runner_dry_run import (  # noqa: E402
    write_process_ontology_sharepoint_schema_apply_live_readiness_gate,
    write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact,
)


SENSITIVE_GRAPH_MARKERS = (
    "validator-sensitive-message-must-not-survive",
    "validator-sensitive-nested-message-must-not-survive",
    "validator-sensitive-request-id-must-not-survive",
    "validator-sensitive-choice-must-not-survive",
)
FORBIDDEN_MARKERS = (
    "client_secret",
    "private_key",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "authorization",
    "bearer ",
    "funktion8.sharepoint.com",
    "\"headers\"",
)


class FakeGraphDispatcherClient:
    def __init__(self, *, choice_patch_error_codes: tuple[str, ...] = ()) -> None:
        self.posts: list[tuple[str, dict]] = []
        self.patches: list[tuple[str, dict]] = []
        self.get_counts: dict[str, int] = {}
        self.choice_columns = {"Vorgangstyp", "CurrentPhase", "ProcessPhase", "RoleTemplate"}
        self.choice_patch_error_codes = choice_patch_error_codes

    def get(self, path: str) -> dict:
        self.get_counts[path] = self.get_counts.get(path, 0) + 1
        if "$filter=displayName" in path:
            return self._filter_response(path, "displayName", created=bool(self.posts))
        if "$filter=name" in path:
            name = self._quoted_filter_value(path)
            if name in self.choice_columns:
                return {
                    "value": [
                        {
                            "id": f"fake-choice-column-{name}",
                            "name": name,
                            "readOnly": False,
                            "sealed": False,
                            "indexed": True,
                            "choice": {"choices": []},
                        }
                    ]
                }
            return self._filter_response(path, "name", created=bool(self.posts))
        if "/columns/fake-choice-column" in path or "/columns/fake-choice-" in path:
            if self.patches:
                return {
                    "id": "fake-choice-column",
                    "readOnly": False,
                    "sealed": False,
                    "indexed": True,
                    "choice": {"choices": self.patches[-1][1]["choice"]["choices"]},
                }
            return {
                "id": "fake-choice-column",
                "readOnly": False,
                "sealed": False,
                "indexed": True,
                "choice": {"choices": []},
            }
        return {"value": [{"id": "fake-existing"}]}

    def post(self, path: str, payload: dict) -> dict:
        self.posts.append((path, payload))
        return {"id": f"fake-post-{len(self.posts)}"}

    def patch(self, path: str, payload: dict) -> dict:
        if isinstance(payload.get("choice"), dict) and self.choice_patch_error_codes:
            raise GraphHttpError(400, _nested_graph_error_body(self.choice_patch_error_codes, path))
        self.patches.append((path, payload))
        return {"id": f"fake-patch-{len(self.patches)}"}

    def _filter_response(self, path: str, key: str, *, created: bool) -> dict:
        if self.get_counts[path] == 1 and not created:
            return {"value": []}
        return {"value": [{"id": f"fake-{key}-id", key: self._quoted_filter_value(path)}]}

    def _quoted_filter_value(self, path: str) -> str:
        marker = "%27"
        if marker in path:
            parts = path.split(marker)
            if len(parts) >= 3:
                return urllib.parse.unquote(parts[1])
        if "'" in path:
            parts = path.split("'")
            if len(parts) >= 3:
                return urllib.parse.unquote(parts[1])
        return "fake"


def _nested_graph_error_body(codes: tuple[str, ...], path: str) -> str:
    error: dict = {
        "code": codes[0],
        "message": SENSITIVE_GRAPH_MARKERS[0],
        "details": [{"target": path, "value": SENSITIVE_GRAPH_MARKERS[3]}],
    }
    current = error
    for code in codes[1:]:
        nested = {"code": code, "message": SENSITIVE_GRAPH_MARKERS[1]}
        current["innerError"] = nested
        current = nested
    current["innerError"] = {"request-id": SENSITIVE_GRAPH_MARKERS[2]}
    return json.dumps({"error": error})


def _choice_failure_errors(
    payload: dict,
    expected_code: str,
    expected_binding_sha256: str,
) -> list[str]:
    errors = list(
        validate_process_ontology_sharepoint_schema_apply_graph_dispatcher(
            payload,
            expected_binding_sha256=expected_binding_sha256,
        ).errors
    )
    failed_step = payload.get("dispatch_steps", [{}])[-1]
    diagnostic = failed_step.get("error", {}).get("diagnostic", {})
    expected = {
        "status": (payload.get("status"), "FAILED"),
        "mutation outcome": (failed_step.get("mutationOutcome"), "POSSIBLE"),
        "Graph code": (diagnostic.get("graphError", {}).get("code"), expected_code),
        "Graph class": (
            diagnostic.get("graphError", {}).get("class"),
            "REQUEST_VALIDATION",
        ),
        "retry disposition": (
            diagnostic.get("retryDisposition"),
            "DO_NOT_RETRY_UNCHANGED",
        ),
        "expected HTTP status": (diagnostic.get("expectedHttpStatus"), 200),
        "endpoint": (diagnostic.get("endpoint"), "COLUMN_DEFINITION_UPDATE"),
        "facet": (diagnostic.get("facet"), "CHOICE"),
    }
    errors.extend(
        f"unexpected Choice PATCH diagnostic {name}: {actual!r}"
        for name, (actual, wanted) in expected.items()
        if actual != wanted
    )
    if any(
        isinstance(value, int) and not isinstance(value, bool) and not 0 <= value <= 1000
        for value in diagnostic.get("counts", {}).values()
    ):
        errors.append("Choice PATCH diagnostic counts must remain bounded")
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    errors.extend(
        f"Choice PATCH diagnostic retained forbidden marker: {marker}"
        for marker in SENSITIVE_GRAPH_MARKERS
        if marker in serialized
    )
    return errors


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        artifact_root = temp_root / "artifacts"
        artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
        artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
        gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
        gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
        dispatch_json = temp_root / "process-ontology-schema-apply-graph-dispatcher.redacted.json"
        dispatch_md = temp_root / "process-ontology-schema-apply-graph-dispatcher.redacted.md"
        write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
            REPO_ROOT,
            artifact_json,
            artifact_md,
        )
        write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
            REPO_ROOT,
            artifact_root,
            gate_json,
            gate_md,
            workspace_ids=["notary_team_01"],
        )
        expected_binding_sha256 = build_process_ontology_sharepoint_schema_apply_binding(
            REPO_ROOT,
            ["notary_team_01"],
        )["binding_sha256"]
        payload = run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
            FakeGraphDispatcherClient(),
            REPO_ROOT,
            live_readiness_gate=gate_json,
            workspace_id="notary_team_01",
            correlation_id="nac-schema-apply-graph-dispatcher-validator",
            owner_approval_reference="owner-approval-graph-dispatcher-validator",
            reason="Validate bound Graph dispatcher",
            owner_approved=True,
            execute_live_schema_apply=True,
            write_redacted_evidence=True,
            evidence_json_output=dispatch_json,
            evidence_markdown_output=dispatch_md,
        )
        validation = validate_process_ontology_sharepoint_schema_apply_graph_dispatcher(
            payload,
            expected_binding_sha256=expected_binding_sha256,
        )
        errors.extend(validation.errors)
        if payload.get("schema_version") != SCHEMA_VERSION:
            errors.append("unexpected graph dispatcher schema version")
        if payload.get("status") != "PASSED":
            errors.append("graph dispatcher fake-client run must pass")
        if payload.get("summary", {}).get("dispatched_step_count") != 34:
            errors.append("graph dispatcher must cover all 34 notary_team_01 apply steps")
        if payload.get("summary", {}).get("mutation_request_count", 0) < 1:
            errors.append("graph dispatcher must execute at least one mutation")

        diagnostic_cases = (
            (("invalidRequest",), "invalidRequest"),
            (("outerSensitiveUnknown", "badArgument"), "badArgument"),
            (("badArgument", "invalidRequest"), "invalidRequest"),
        )
        for index, (graph_error_codes, expected_code) in enumerate(diagnostic_cases):
            failure_json = temp_root / f"choice-patch-{index}.redacted.json"
            failure_md = temp_root / f"choice-patch-{index}.redacted.md"
            failure_payload = run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                FakeGraphDispatcherClient(choice_patch_error_codes=graph_error_codes),
                REPO_ROOT,
                live_readiness_gate=gate_json,
                workspace_id="notary_team_01",
                correlation_id="nac-schema-apply-choice-diagnostic-validator",
                owner_approval_reference="owner-approval-choice-diagnostic-validator",
                reason="Validate closed Choice PATCH diagnostics",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                evidence_json_output=failure_json,
                evidence_markdown_output=failure_md,
            )
            errors.extend(
                _choice_failure_errors(
                    failure_payload,
                    expected_code,
                    expected_binding_sha256,
                )
            )

        artifact_payload = write_process_ontology_sharepoint_schema_apply_graph_dispatcher_artifact(
            FakeGraphDispatcherClient(),
            REPO_ROOT,
            dispatch_json,
            dispatch_md,
            live_readiness_gate=gate_json,
            workspace_id="notary_team_01",
            correlation_id="nac-schema-apply-graph-dispatcher-artifact-validator",
            owner_approval_reference="owner-approval-graph-dispatcher-artifact-validator",
            reason="Validate partial Graph dispatcher artifact",
            owner_approved=True,
            execute_live_schema_apply=True,
            write_redacted_evidence=True,
            max_steps=2,
        )
        if artifact_payload.get("status") != "PARTIAL":
            errors.append("limited graph dispatcher artifact run must be partial")
        if not dispatch_json.is_file():
            errors.append("JSON graph dispatcher artifact was not written")
        if not dispatch_md.is_file():
            errors.append("Markdown graph dispatcher artifact was not written")
        combined = dispatch_json.read_text(encoding="utf-8") + "\n" + dispatch_md.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker.lower() in combined.lower():
                errors.append(f"graph dispatcher artifact must not contain marker: {marker}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("process ontology SharePoint schema apply Graph dispatcher validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
