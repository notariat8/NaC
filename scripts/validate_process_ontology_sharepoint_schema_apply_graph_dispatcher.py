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
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict]] = []
        self.patches: list[tuple[str, dict]] = []
        self.get_counts: dict[str, int] = {}
        self.choice_columns = {"Vorgangstyp", "CurrentPhase", "ProcessPhase", "RoleTemplate"}

    def get(self, path: str) -> dict:
        self.get_counts[path] = self.get_counts.get(path, 0) + 1
        if "$filter=displayName" in path:
            return self._filter_response(path, "displayName", created=bool(self.posts))
        if "$filter=name" in path:
            name = self._quoted_filter_value(path)
            if name in self.choice_columns:
                return {"value": [{"id": f"fake-choice-column-{name}", "name": name, "choice": {"choices": []}}]}
            return self._filter_response(path, "name", created=bool(self.posts))
        if "/columns/fake-choice-column" in path or "/columns/fake-choice-" in path:
            if self.patches:
                return {"id": "fake-choice-column", "choice": {"choices": self.patches[-1][1]["choice"]["choices"]}}
            return {"id": "fake-choice-column", "choice": {"choices": []}}
        return {"value": [{"id": "fake-existing"}]}

    def post(self, path: str, payload: dict) -> dict:
        self.posts.append((path, payload))
        return {"id": f"fake-post-{len(self.posts)}"}

    def patch(self, path: str, payload: dict) -> dict:
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
        validation = validate_process_ontology_sharepoint_schema_apply_graph_dispatcher(payload)
        errors.extend(validation.errors)
        if payload.get("schema_version") != SCHEMA_VERSION:
            errors.append("unexpected graph dispatcher schema version")
        if payload.get("status") != "PASSED":
            errors.append("graph dispatcher fake-client run must pass")
        if payload.get("summary", {}).get("dispatched_step_count") != 34:
            errors.append("graph dispatcher must cover all 34 notary_team_01 apply steps")
        if payload.get("summary", {}).get("mutation_request_count", 0) < 1:
            errors.append("graph dispatcher must execute at least one mutation")

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
