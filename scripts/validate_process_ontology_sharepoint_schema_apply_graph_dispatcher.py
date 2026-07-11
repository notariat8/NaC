#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import urllib.parse
from pathlib import Path
from unittest.mock import patch

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
from notary_kg import process_ontology_schema_apply_graph_dispatcher as graph_dispatcher_module  # noqa: E402
from notary_kg.process_ontology_schema_apply_graph_dispatcher import (  # noqa: E402
    SCHEMA_VERSION,
    run_process_ontology_sharepoint_schema_apply_graph_dispatcher,
    validate_process_ontology_sharepoint_schema_apply_graph_dispatcher,
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
    def __init__(
        self,
        *,
        choice_patch_error_codes: tuple[str, ...] = (),
        wrong_existing_list_shape: bool = False,
        ambiguous_list_match: bool = False,
        choice_shape_drift: bool = False,
    ) -> None:
        self.posts: list[tuple[str, dict]] = []
        self.patches: list[tuple[str, dict]] = []
        self.get_counts: dict[str, int] = {}
        self.objects: dict[tuple[str, str, str], dict] = {}
        self.choice_columns = {"Vorgangstyp", "CurrentPhase", "ProcessPhase", "RoleTemplate"}
        self.choice_patch_error_codes = choice_patch_error_codes
        self.wrong_existing_list_shape = wrong_existing_list_shape
        self.ambiguous_list_match = ambiguous_list_match
        self.choice_shape_drift = choice_shape_drift
        self.choice_state: dict[str, dict] = {}
        self.column_names: dict[str, str] = {}

    def get(self, path: str) -> dict:
        self.get_counts[path] = self.get_counts.get(path, 0) + 1
        if "$filter=displayName" in path:
            if self.ambiguous_list_match:
                name = self._quoted_filter_value(path)
                return {"value": [{"id": "duplicate-list-a", "displayName": name}, {"id": "duplicate-list-b", "displayName": name}]}
            if self.wrong_existing_list_shape:
                return {
                    "value": [
                        {
                            "id": "wrong-shape-list",
                            "displayName": self._quoted_filter_value(path),
                            "list": {"template": "documentLibrary"},
                            "columns": [],
                            "description": "validator-sensitive-wrong-shape-must-not-survive",
                        }
                    ]
                }
            return self._filter_response(path, "displayName")
        if "$filter=name" in path:
            name = self._quoted_filter_value(path)
            existing = self._filter_response(path, "name")
            if (
                existing["value"]
                and name in self.choice_columns
                and self.choice_patch_error_codes
                and self.get_counts[path] > 2
            ):
                column_id = str(existing["value"][0]["id"])
                self.choice_state[column_id] = {
                    "choices": [],
                    "allowTextEntry": False,
                    "displayAs": "dropDownMenu",
                }
                existing["value"][0]["choice"] = dict(self.choice_state[column_id])
            return existing
        if "/columns/" in path:
            column_id = path.split("/columns/", 1)[1].split("?", 1)[0]
            if column_id in self.choice_state:
                response = {
                    "id": column_id,
                    "name": self.column_names.get(
                        column_id,
                        column_id.removeprefix("fake-choice-column-"),
                    ),
                    "readOnly": False,
                    "sealed": False,
                    "indexed": True,
                    "choice": dict(self.choice_state[column_id]),
                }
                if self.choice_shape_drift:
                    response["readOnly"] = True
                return response
        return {"value": [{"id": "fake-existing"}]}

    def post(self, path: str, payload: dict) -> dict:
        self.posts.append((path, payload))
        object_id = f"fake-post-{len(self.posts)}"
        for key in ("displayName", "name"):
            if payload.get(key):
                self.objects[(path, key, str(payload[key]))] = {"id": object_id, **payload}
        if isinstance(payload.get("choice"), dict):
            self.choice_state[object_id] = dict(payload["choice"])
        if isinstance(payload.get("name"), str):
            self.column_names[object_id] = payload["name"]
        return {"id": object_id}

    def patch(self, path: str, payload: dict) -> dict:
        if isinstance(payload.get("choice"), dict) and self.choice_patch_error_codes:
            raise GraphHttpError(400, _nested_graph_error_body(self.choice_patch_error_codes, path))
        self.patches.append((path, payload))
        object_id = path.split("/columns/", 1)[1].split("?", 1)[0]
        if isinstance(payload.get("choice"), dict):
            self.choice_state[object_id] = dict(payload["choice"])
        return {"id": object_id}

    def _filter_response(self, path: str, key: str) -> dict:
        base = path.split("?", 1)[0]
        value = self._quoted_filter_value(path)
        item = self.objects.get((base, key, value))
        return {"value": [dict(item)] if item else []}

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


_REAL_APPLY_PLAN_BUILDER = (
    graph_dispatcher_module.build_process_ontology_sharepoint_schema_apply_plan
)
_REAL_LIVE_RUNNER_BUILDER = (
    graph_dispatcher_module.build_process_ontology_sharepoint_schema_apply_live_runner
)


def _nonblocked_apply_plan(*args: object, **kwargs: object) -> dict:
    payload = _REAL_APPLY_PLAN_BUILDER(*args, **kwargs)
    patched = dict(payload)
    patched["summary"] = dict(payload["summary"])
    patched["summary"]["live_execution_approval_state"] = "VALIDATOR_PATCHED_READY"
    return patched


def _ready_live_runner(*args: object, **kwargs: object) -> dict:
    payload = _REAL_LIVE_RUNNER_BUILDER(*args, **kwargs)
    patched = dict(payload)
    patched["status"] = "READY_FOR_GRAPH_REST_DISPATCH"
    return patched


def _run_patched_graph_dispatcher(client: FakeGraphDispatcherClient, **kwargs: object) -> dict:
    with (
        patch.object(
            graph_dispatcher_module,
            "build_process_ontology_sharepoint_schema_apply_plan",
            side_effect=_nonblocked_apply_plan,
        ),
        patch.object(
            graph_dispatcher_module,
            "build_process_ontology_sharepoint_schema_apply_live_runner",
            side_effect=_ready_live_runner,
        ),
    ):
        return run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
            client,
            REPO_ROOT,
            **kwargs,
        )


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

        blocker_client = FakeGraphDispatcherClient()
        blocker_json = temp_root / "s2-blocker.redacted.json"
        blocker_md = temp_root / "s2-blocker.redacted.md"
        try:
            run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                blocker_client,
                REPO_ROOT,
                live_readiness_gate=gate_json,
                workspace_id="notary_team_01",
                correlation_id="nac-schema-apply-s2-block-validator",
                owner_approval_reference="owner-approval-s2-block-validator",
                reason="Validate public S2 pre-dispatch block",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                evidence_json_output=blocker_json,
                evidence_markdown_output=blocker_md,
            )
        except ValueError as exc:
            if "blocked pending S6/S7 approval" not in str(exc):
                errors.append("dispatcher returned an unexpected S2 blocker")
        else:
            errors.append("dispatcher must reject the S2 plan before Graph dispatch")
        if blocker_client.get_counts or blocker_client.posts or blocker_client.patches:
            errors.append("S2 dispatcher blocker must make zero fake Graph client calls")
        if blocker_json.exists() or blocker_md.exists():
            errors.append("S2 dispatcher blocker must stop before dispatch evidence execution")

        payload = _run_patched_graph_dispatcher(
            FakeGraphDispatcherClient(),
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
        approved_step_count = build_process_ontology_sharepoint_schema_apply_binding(
            REPO_ROOT,
            ["notary_team_01"],
        )["selected_apply_unit_count"]
        if payload.get("summary", {}).get("dispatched_step_count") != approved_step_count:
            errors.append("graph dispatcher must cover every approved notary_team_01 apply step")
        if payload.get("summary", {}).get("mutation_request_count", 0) < 1:
            errors.append("graph dispatcher must execute at least one mutation")

        wrong_shape_client = FakeGraphDispatcherClient(wrong_existing_list_shape=True)
        wrong_shape_payload = _run_patched_graph_dispatcher(
            wrong_shape_client,
            live_readiness_gate=gate_json,
            workspace_id="notary_team_01",
            correlation_id="nac-schema-apply-wrong-shape-validator",
            owner_approval_reference="owner-approval-wrong-shape-validator",
            reason="Validate fail-closed existing list shape",
            owner_approved=True,
            execute_live_schema_apply=True,
            write_redacted_evidence=True,
            evidence_json_output=temp_root / "wrong-shape.redacted.json",
            evidence_markdown_output=temp_root / "wrong-shape.redacted.md",
        )
        wrong_shape_step = wrong_shape_payload.get("dispatch_steps", [{}])[-1]
        if wrong_shape_payload.get("status") != "FAILED":
            errors.append("wrong existing list shape must fail closed")
        if wrong_shape_step.get("error", {}).get("code") != "existing_object_shape_mismatch":
            errors.append("wrong existing list shape must use the closed mismatch code")
        if wrong_shape_step.get("mutationAttempted") is not False:
            errors.append("wrong existing list shape must fail before mutation")
        if wrong_shape_client.posts or wrong_shape_client.patches:
            errors.append("wrong existing list shape must not execute Graph writes")
        if "validator-sensitive-wrong-shape-must-not-survive" in json.dumps(
            wrong_shape_payload, ensure_ascii=False, sort_keys=True
        ):
            errors.append("wrong existing list shape retained raw sensitive detail")

        ambiguous_client = FakeGraphDispatcherClient(ambiguous_list_match=True)
        ambiguous_payload = _run_patched_graph_dispatcher(
            ambiguous_client,
            live_readiness_gate=gate_json,
            workspace_id="notary_team_01",
            correlation_id="nac-schema-apply-ambiguous-validator",
            owner_approval_reference="owner-approval-ambiguous-validator",
            reason="Validate ambiguous named Graph match rejection",
            owner_approved=True,
            execute_live_schema_apply=True,
            write_redacted_evidence=True,
            evidence_json_output=temp_root / "ambiguous.redacted.json",
            evidence_markdown_output=temp_root / "ambiguous.redacted.md",
        )
        ambiguous_step = ambiguous_payload.get("dispatch_steps", [{}])[-1]
        if ambiguous_step.get("error", {}).get("code") != "ambiguous_graph_match":
            errors.append("ambiguous named Graph matches must fail closed")
        if ambiguous_client.posts or ambiguous_client.patches:
            errors.append("ambiguous named Graph matches must fail before mutation")

        choice_drift_client = FakeGraphDispatcherClient(choice_shape_drift=True)
        choice_drift_payload = _run_patched_graph_dispatcher(
            choice_drift_client,
            live_readiness_gate=gate_json,
            workspace_id="notary_team_01",
            correlation_id="nac-schema-apply-choice-shape-validator",
            owner_approval_reference="owner-approval-choice-shape-validator",
            reason="Validate existing Choice shape drift rejection",
            owner_approved=True,
            execute_live_schema_apply=True,
            write_redacted_evidence=True,
            evidence_json_output=temp_root / "choice-shape.redacted.json",
            evidence_markdown_output=temp_root / "choice-shape.redacted.md",
        )
        choice_drift_step = choice_drift_payload.get("dispatch_steps", [{}])[-1]
        if choice_drift_step.get("error", {}).get("code") != "existing_object_shape_mismatch":
            errors.append("existing Choice shape drift must fail closed")
        if choice_drift_client.patches:
            errors.append("existing Choice shape drift must fail before Choice mutation")

        diagnostic_cases = (
            (("invalidRequest",), "invalidRequest"),
            (("outerSensitiveUnknown", "badArgument"), "badArgument"),
            (("badArgument", "invalidRequest"), "invalidRequest"),
        )
        for index, (graph_error_codes, expected_code) in enumerate(diagnostic_cases):
            failure_json = temp_root / f"choice-patch-{index}.redacted.json"
            failure_md = temp_root / f"choice-patch-{index}.redacted.md"
            failure_payload = _run_patched_graph_dispatcher(
                FakeGraphDispatcherClient(choice_patch_error_codes=graph_error_codes),
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

        artifact_payload = _run_patched_graph_dispatcher(
            FakeGraphDispatcherClient(),
            evidence_json_output=dispatch_json,
            evidence_markdown_output=dispatch_md,
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
