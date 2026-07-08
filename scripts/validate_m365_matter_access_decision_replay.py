#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.matter_access_decision_replay import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_DECISION_REPLAY_OUTPUT,
    DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
    replay_matter_access_decisions_from_path,
)


REQUIRED_DECISION_CODES = {
    "ALLOW_LEAD_NOTARY",
    "ALLOW_ASSIGNED_CLERK",
    "ALLOW_ACTIVE_DEPUTY_GRANT",
    "BLOCK_WORKSPACE_SCOPE",
    "BLOCK_CASE_SCOPE",
    "BLOCK_DEPUTY_GRANT_EXPIRED",
    "BLOCK_DEPUTY_GRANT_MISSING_REASON",
    "BLOCK_DEPUTY_GRANT_MISSING_APPROVER",
    "BLOCK_DEPUTY_GRANT_MISSING_AUDIT_CORRELATION",
    "BLOCK_BLANKET_VISIBILITY",
}
REQUIRED_DOC_MARKERS = {
    REPO_ROOT / "docs" / "de" / "cli.md": [
        "matter-access-decision-replay",
        "matter-access-decision-replay.redacted.json",
    ],
    REPO_ROOT / "docs" / "en" / "cli.md": [
        "matter-access-decision-replay",
        "matter-access-decision-replay.redacted.json",
    ],
    REPO_ROOT / "docs" / "de" / "architecture" / "m365-matter-access-delegation.md": [
        "matter-access-decision-replay",
        "matter-access-decision-replay.redacted.json",
    ],
    REPO_ROOT / "docs" / "en" / "architecture" / "m365-matter-access-delegation.md": [
        "matter-access-decision-replay",
        "matter-access-decision-replay.redacted.json",
    ],
    REPO_ROOT / "docs" / "de" / "quality-gate.md": ["m365_matter_access_decision_replay"],
    REPO_ROOT / "docs" / "en" / "quality-gate.md": ["m365_matter_access_decision_replay"],
    REPO_ROOT / "workflows" / "contracts" / "README.md": ["matter-access-decision-replay"],
}
REQUIRED_CODE_MARKERS = {
    REPO_ROOT / "src" / "nac_cli" / "cli.py": [
        "matter-access-decision-replay",
        "--matter-access-decision-snapshot",
        "--matter-access-decision-replay-output",
    ],
    REPO_ROOT / "scripts" / "provision_teams_sharepoint_graph.py": [
        "matter-access-decision-replay",
        "run_matter_access_decision_replay",
    ],
    REPO_ROOT / "scripts" / "quality_gate.py": ["m365_matter_access_decision_replay"],
}
PROHIBITED_EVIDENCE_MARKERS = {
    "synthetic-",
    "NAC-SYN-MATTER",
    "NAC-SYN-GRANT",
    "NAC-SYN-AUDIT",
    "BEGIN PRIVATE KEY",
    "client_secret",
    "password=",
    "ghp_",
    "/sites/",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: M365 matter access decision replay is offline, redacted and CLI-wired.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    if not DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT.is_file():
        errors.append("matter-access-decision-replay fixture is missing")
        return errors

    try:
        payload = replay_matter_access_decisions_from_path(
            snapshot_path=DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
            reference_time="2026-07-08T12:00:00Z",
            correlation_id="validator-replay",
        )
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        return [str(exc)]

    _validate_payload(payload, errors)
    _validate_redaction(payload, errors)
    _validate_markers(REQUIRED_CODE_MARKERS, errors)
    _validate_markers(REQUIRED_DOC_MARKERS, errors)
    return errors


def _validate_payload(payload: dict[str, Any], errors: list[str]) -> None:
    if payload.get("status") != "PASSED":
        errors.append("matter-access-decision-replay fixture replay must pass")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if summary.get("request_count") != 10:
        errors.append("matter-access-decision-replay must evaluate ten synthetic requests")
    if summary.get("allowed_count") != 3:
        errors.append("matter-access-decision-replay must allow three positive cases")
    if summary.get("blocked_count") != 7:
        errors.append("matter-access-decision-replay must block seven negative cases")
    code_counts = summary.get("decision_code_counts") if isinstance(summary.get("decision_code_counts"), dict) else {}
    missing_codes = sorted(REQUIRED_DECISION_CODES - set(code_counts))
    if missing_codes:
        errors.append("matter-access-decision-replay missing decision codes: " + ", ".join(missing_codes))
    for code in REQUIRED_DECISION_CODES:
        if code_counts.get(code) != 1:
            errors.append(f"matter-access-decision-replay decision code {code} must occur exactly once")
    for flag in (
        "executes_graph_requests",
        "executes_graph_writes",
        "tenant_mutation_allowed",
        "team_membership_mutation_allowed",
        "sharepoint_item_permission_mutation_allowed",
        "reads_sharepoint_file_content",
        "stores_tokens_or_secrets",
        "stores_matter_payloads",
        "raw_graph_path_stored",
        "raw_graph_response_stored",
    ):
        if summary.get(flag) is not False:
            errors.append(f"matter-access-decision-replay summary.{flag} must be false")
    if str(DEFAULT_MATTER_ACCESS_DECISION_REPLAY_OUTPUT).endswith(".redacted.json") is not True:
        errors.append("matter-access-decision-replay default output must be a redacted JSON artifact")


def _validate_redaction(payload: dict[str, Any], errors: list[str]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    for marker in sorted(PROHIBITED_EVIDENCE_MARKERS):
        if marker in serialized:
            errors.append(f"matter-access-decision-replay evidence leaks marker {marker!r}")
    privacy = payload.get("privacy") if isinstance(payload.get("privacy"), dict) else {}
    for flag in (
        "storesRawSharePointItems",
        "storesCredentials",
        "storesTokensOrSecrets",
        "storesMatterData",
        "storesMatterPayloads",
        "storesRawGraphPath",
        "storesRawGraphResponse",
        "readsSharePointFileContent",
        "executesGraphRequests",
        "executesGraphWrites",
        "tenantWritesExecuted",
    ):
        if privacy.get(flag) is not False:
            errors.append(f"matter-access-decision-replay privacy.{flag} must be false")
    if privacy.get("metadataOnly") is not True:
        errors.append("matter-access-decision-replay privacy.metadataOnly must be true")


def _validate_markers(markers_by_path: dict[Path, list[str]], errors: list[str]) -> None:
    for path, markers in markers_by_path.items():
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(str(exc))
            continue
        for marker in markers:
            if marker not in content:
                errors.append(f"{path.relative_to(REPO_ROOT)} missing marker {marker!r}")


if __name__ == "__main__":
    raise SystemExit(main())
