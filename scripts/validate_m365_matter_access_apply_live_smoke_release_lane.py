from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    "de_doc": REPO_ROOT / "docs/de/operations/m365-matter-access-apply-live-smoke-release-lane.md",
    "en_doc": REPO_ROOT / "docs/en/operations/m365-matter-access-apply-live-smoke-release-lane.md",
    "de_ops_index": REPO_ROOT / "docs/de/operations/README.md",
    "en_ops_index": REPO_ROOT / "docs/en/operations/README.md",
    "de_batch": REPO_ROOT / "docs/de/operations/m365-mcp-batch-approval.md",
    "en_batch": REPO_ROOT / "docs/en/operations/m365-mcp-batch-approval.md",
    "de_cli": REPO_ROOT / "docs/de/cli.md",
    "en_cli": REPO_ROOT / "docs/en/cli.md",
    "de_quality": REPO_ROOT / "docs/de/quality-gate.md",
    "en_quality": REPO_ROOT / "docs/en/quality-gate.md",
    "verification_contract": REPO_ROOT
    / "workflows/verification-contracts/m365-matter-access-apply-live-smoke-release-lane.verification.json",
    "verification_readme": REPO_ROOT / "workflows/verification-contracts/README.md",
    "agent_context_index": REPO_ROOT / "agent-context/index.json",
    "decision_index": REPO_ROOT / "agent-context/decision-index.json",
    "invariant_index": REPO_ROOT / "agent-context/invariant-index.json",
    "apply_smoke": REPO_ROOT / "src/nac_m365_graph/matter_access_apply_smoke.py",
    "release_gate_evidence": REPO_ROOT / "src/nac_m365_graph/release_gate_evidence.py",
    "cli": REPO_ROOT / "src/nac_cli/cli.py",
    "quality_gate": REPO_ROOT / "scripts/quality_gate.py",
    "matter_access_tests": REPO_ROOT / "tests/test_m365_matter_access_delegation.py",
    "evidence_tests": REPO_ROOT / "tests/test_m365_release_gate_evidence.py",
}

CONTRACT_ID = "verification.m365_matter_access_apply_live_smoke_release_lane"
CHECK_ID = "m365_matter_access_apply_live_smoke_release_lane"
DOC_NAME = "m365-matter-access-apply-live-smoke-release-lane.md"
APPROVAL_TEXT = (
    "Freigabe: Matter-Access Apply Live-Smoke im Workspace notary_team_01 "
    "owner-approved ausführen"
)

REQUIRED_DE_MARKERS = [
    "kein stillschweigender Default",
    "owner-gated Release Lane",
    "Vertretungsfreigaben",
    "AuditJournalLite",
    "Graph-REST-only",
    "notary_team_01",
    "NAC-SMOKE-GRANT-",
    "NAC-SMOKE-MATTER-",
    "matter-access-apply-smoke",
    "--owner-approved",
    "--release-gate-matter-access-apply-smoke-artifact",
    "NOT_ATTACHED",
    "Readback",
    "Cleanup",
    "redigierte Evidence",
    "stores_tokens_or_secrets=false",
    "raw_graph_response_stored=false",
]

REQUIRED_EN_MARKERS = [
    "not a silent default",
    "owner-gated release lane",
    "Vertretungsfreigaben",
    "AuditJournalLite",
    "Graph REST",
    "notary_team_01",
    "NAC-SMOKE-GRANT-",
    "NAC-SMOKE-MATTER-",
    "matter-access-apply-smoke",
    "--owner-approved",
    "--release-gate-matter-access-apply-smoke-artifact",
    "NOT_ATTACHED",
    "readback",
    "cleanup",
    "redacted evidence",
    "stores_tokens_or_secrets=false",
    "raw_graph_response_stored=false",
]

PROHIBITED_MARKERS = {
    "BEGIN PRIVATE KEY",
    "client_secret",
    "password=",
    "ghp_",
    "real_mandate_data_sample",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: M365 matter-access apply live-smoke release lane is documented, indexed and gated.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_files())
    errors.extend(_validate_docs())
    errors.extend(_validate_code_boundaries())
    errors.extend(_validate_agent_indexes())
    errors.extend(_validate_verification_contract())
    errors.extend(_validate_quality_gate())
    return errors


def _validate_files() -> list[str]:
    errors: list[str] = []
    for label, path in REQUIRED_FILES.items():
        if not path.is_file():
            errors.append(f"required file missing ({label}): {path.relative_to(REPO_ROOT)}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    _require_markers(REQUIRED_FILES["de_doc"], REQUIRED_DE_MARKERS, errors)
    _require_markers(REQUIRED_FILES["en_doc"], REQUIRED_EN_MARKERS, errors)

    for key in ("de_doc", "en_doc"):
        path = REQUIRED_FILES[key]
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if APPROVAL_TEXT not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} missing prepared owner approval text")
            if "matter-access-apply-policy-smoke" not in text or "mvp_release_readiness=READY" not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} must require policy smoke and MVP readiness before live smoke")
            _reject_prohibited_text(path, errors)

    for key in ("de_ops_index", "en_ops_index", "de_batch", "en_batch", "de_cli", "en_cli"):
        path = REQUIRED_FILES[key]
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if DOC_NAME not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} must link or reference {DOC_NAME}")

    for key in ("de_batch", "en_batch", "de_cli", "en_cli", "de_quality", "en_quality"):
        path = REQUIRED_FILES[key]
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for marker in ("--release-gate-matter-access-apply-smoke-artifact", "matter-access-apply-smoke"):
                if marker not in text:
                    errors.append(f"{path.relative_to(REPO_ROOT)} missing marker: {marker}")

    return errors


def _validate_code_boundaries() -> list[str]:
    errors: list[str] = []
    apply_path = REQUIRED_FILES["apply_smoke"]
    evidence_path = REQUIRED_FILES["release_gate_evidence"]
    cli_path = REQUIRED_FILES["cli"]
    test_path = REQUIRED_FILES["matter_access_tests"]
    evidence_test_path = REQUIRED_FILES["evidence_tests"]

    if apply_path.is_file():
        text = apply_path.read_text(encoding="utf-8")
        for marker in (
            "SMOKE_GRANT_ID_PREFIX = \"NAC-SMOKE-GRANT-\"",
            "SMOKE_CASE_ID_PREFIX = \"NAC-SMOKE-MATTER-\"",
            "write_tools\": [\"grant_request\", \"audit_append\"]",
            "write_lists\": [\"Vertretungsfreigaben\", \"AuditJournalLite\"]",
            "executed_graph_writes\": True",
            "sharepoint_item_writes_executed\": True",
            "tenant_mutation_allowed\": False",
            "team_membership_mutation_allowed\": False",
            "sharepoint_item_permission_mutation_allowed\": False",
            "raw_graph_path_stored\": False",
            "raw_graph_response_stored\": False",
            "raw_write_payload_stored\": False",
            "storesTokensOrSecrets\": False",
            "storesMatterPayloads\": False",
            "readsSharePointFileContent\": False",
        ):
            if marker not in text:
                errors.append(f"{apply_path.relative_to(REPO_ROOT)} missing boundary marker: {marker}")

    if evidence_path.is_file():
        text = evidence_path.read_text(encoding="utf-8")
        for marker in (
            "_matter_access_apply_smoke_step",
            "matter_access_apply_smoke",
            "label=\"matter-access-apply-smoke --owner-approved\"",
            "required=False",
            "if artifact is None:",
            "matter_access_apply_smoke_artifact",
        ):
            if marker not in text:
                errors.append(f"{evidence_path.relative_to(REPO_ROOT)} missing optional attach boundary marker: {marker}")

    if cli_path.is_file():
        text = cli_path.read_text(encoding="utf-8")
        for marker in ("matter-access-apply-smoke", "--owner-approved", "DEFAULT_MATTER_ACCESS_APPLY_SMOKE_OUTPUT"):
            if marker not in text:
                errors.append(f"{cli_path.relative_to(REPO_ROOT)} missing CLI live-smoke marker: {marker}")

    if test_path.is_file():
        text = test_path.read_text(encoding="utf-8")
        for marker in (
            "test_matter_access_apply_smoke_writes_reads_cleans_and_redacts",
            "test_matter_access_apply_smoke_rejects_non_synthetic_ids_before_graph_calls",
            "test_matter_access_apply_smoke_blocks_missing_cleanup_before_graph_calls",
        ):
            if marker not in text:
                errors.append(f"{test_path.relative_to(REPO_ROOT)} missing live-smoke safety test: {marker}")

    if evidence_test_path.is_file():
        text = evidence_test_path.read_text(encoding="utf-8")
        for marker in (
            "test_attaches_optional_matter_access_apply_smoke_artifact",
            "test_does_not_auto_attach_matter_access_apply_smoke_default_artifact",
        ):
            if marker not in text:
                errors.append(f"{evidence_test_path.relative_to(REPO_ROOT)} missing evidence attachment test: {marker}")

    return errors


def _validate_agent_indexes() -> list[str]:
    errors: list[str] = []
    for key in ("agent_context_index", "decision_index", "invariant_index"):
        path = REQUIRED_FILES[key]
        payload = _read_json(path, errors)
        if not payload:
            continue
        text = json.dumps(payload, ensure_ascii=False)
        for marker in (
            DOC_NAME,
            "matter_access_apply_smoke",
            "m365_matter_access_apply_live_smoke_release_lane",
            "m365-matter-access-apply-live-smoke-release-lane.verification.json",
        ):
            if marker not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} missing agent-context marker: {marker}")
    return errors


def _validate_verification_contract() -> list[str]:
    errors: list[str] = []
    contract_path = REQUIRED_FILES["verification_contract"]
    payload = _read_json(contract_path, errors)
    if payload:
        if payload.get("contract_id") != CONTRACT_ID:
            errors.append(f"{contract_path.relative_to(REPO_ROOT)} has wrong contract_id")
        contract_text = json.dumps(payload, ensure_ascii=False)
        for marker in (
            DOC_NAME,
            "matter-access-apply-smoke",
            "--release-gate-matter-access-apply-smoke-artifact",
            "not a default one-shot release-gate step",
            "NAC-SMOKE-GRANT-",
            "NAC-SMOKE-MATTER-",
            "max_default_auto_attach_count",
            "block_live_smoke",
        ):
            if marker not in contract_text:
                errors.append(f"{contract_path.relative_to(REPO_ROOT)} missing contract marker: {marker}")

    readme_path = REQUIRED_FILES["verification_readme"]
    if readme_path.is_file() and "m365-matter-access-apply-live-smoke-release-lane.verification.json" not in readme_path.read_text(encoding="utf-8"):
        errors.append(f"{readme_path.relative_to(REPO_ROOT)} must list the live-smoke release-lane verification contract")
    return errors


def _validate_quality_gate() -> list[str]:
    errors: list[str] = []
    quality_path = REQUIRED_FILES["quality_gate"]
    if quality_path.is_file():
        text = quality_path.read_text(encoding="utf-8")
        for marker in (
            CHECK_ID,
            "M365 Matter Access Apply Live-Smoke Release Lane",
            "scripts/validate_m365_matter_access_apply_live_smoke_release_lane.py",
        ):
            if marker not in text:
                errors.append(f"{quality_path.relative_to(REPO_ROOT)} missing quality-gate marker: {marker}")

    for key in ("de_quality", "en_quality"):
        path = REQUIRED_FILES[key]
        if path.is_file() and CHECK_ID not in path.read_text(encoding="utf-8"):
            errors.append(f"{path.relative_to(REPO_ROOT)} must document {CHECK_ID}")
    return errors


def _require_markers(path: Path, markers: list[str], errors: list[str]) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} missing marker: {marker}")


def _reject_prohibited_text(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        return
    lowered = path.read_text(encoding="utf-8").lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker: {marker}")


def _read_json(path: Path, errors: list[str]) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)} is not valid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} must contain a JSON object")
        return None
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
