from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_agent_ops.batch_run_envelope import (
    SCHEMA_VERSION,
    load_batch_run_envelope,
    validate_batch_run_envelope,
)


FIXTURE = REPO_ROOT / "tests" / "fixtures" / "agent-ops" / "codex-5h-batch-run-envelope.valid.json"
MODULE = REPO_ROOT / "src" / "nac_agent_ops" / "batch_run_envelope.py"
CLI = REPO_ROOT / "src" / "nac_cli" / "cli.py"
QUALITY_GATE = REPO_ROOT / "scripts" / "quality_gate.py"
AGENT_CONTEXT = REPO_ROOT / "agent-context" / "index.json"
CONTRACT = REPO_ROOT / "workflows" / "verification-contracts" / "codex-5h-batch-run-envelope.verification.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "operations" / "codex-5h-batch-run-envelope.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "operations" / "codex-5h-batch-run-envelope.md"
OPS_DE = REPO_ROOT / "docs" / "de" / "operations" / "README.md"
OPS_EN = REPO_ROOT / "docs" / "en" / "operations" / "README.md"
AGENT_CONTEXT_DE = REPO_ROOT / "docs" / "de" / "agent-context" / "README.md"
AGENT_CONTEXT_EN = REPO_ROOT / "docs" / "en" / "agent-context" / "README.md"
CONTRACT_README = REPO_ROOT / "workflows" / "verification-contracts" / "README.md"

PROHIBITED_MARKERS = {
    "client" + "_secret",
    "BEGIN " + "PRIVATE KEY",
    "BEGIN " + "CERTIFICATE",
    "gh" + "p_",
    "gh" + "o_",
    "real_mandate_data_sample",
    "password=",
}

REQUIRED_CONTEXT_CATEGORY_PATHS = {
    "docs/de/operations/codex-5h-batch-run-envelope.md",
    "docs/en/operations/codex-5h-batch-run-envelope.md",
    "src/nac_agent_ops/batch_run_envelope.py",
    "scripts/validate_codex_5h_batch_run_envelope.py",
    "tests/test_codex_5h_batch_run_envelope.py",
    "tests/fixtures/agent-ops/codex-5h-batch-run-envelope.valid.json",
    "workflows/verification-contracts/codex-5h-batch-run-envelope.verification.json",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: Codex 5h batch run envelope is routed, validated and quality-gated.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_fixture())
    errors.extend(_validate_contract())
    errors.extend(_validate_context_index())
    errors.extend(_validate_cli_and_quality_gate())
    errors.extend(_validate_docs())
    return errors


def _validate_fixture() -> list[str]:
    errors = _file_exists(FIXTURE)
    if errors:
        return errors
    payload = load_batch_run_envelope(FIXTURE)
    errors.extend(validate_batch_run_envelope(payload))
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("fixture schema_version does not match module schema")
    if payload.get("time_budget_hours") != 5:
        errors.append("fixture must model a 5h batch")
    lanes = payload.get("lanes")
    if not isinstance(lanes, list) or len(lanes) < 2:
        errors.append("fixture must include at least two parallel lanes")
    if _contains_prohibited_marker(FIXTURE.read_text(encoding="utf-8")):
        errors.append("fixture contains prohibited persistent context marker")
    return errors


def _validate_contract() -> list[str]:
    errors = _file_exists(CONTRACT)
    if errors:
        return errors
    payload = _read_json(CONTRACT, errors)
    if payload is None:
        return errors
    if payload.get("schema_version") != "nac.verification-contract/v0.1":
        errors.append("codex-5h-batch-run-envelope contract has wrong schema_version")
    if payload.get("contract_id") != "verification.codex_5h_batch_run_envelope":
        errors.append("codex-5h-batch-run-envelope contract has wrong contract_id")
    required_checks = {
        "python3 scripts/validate_codex_5h_batch_run_envelope.py",
        "python3 scripts/nac.py agent-batch validate --format json",
        "python3 scripts/nac.py contracts verify",
    }
    checks = set(_strings(payload.get("checks")))
    for check in sorted(required_checks - checks):
        errors.append(f"verification contract missing check {check}")
    pass_condition = payload.get("pass_condition")
    if not isinstance(pass_condition, dict) or pass_condition.get("all_checks_pass") is not True:
        errors.append("verification contract pass_condition.all_checks_pass must be true")
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict):
        errors.append("verification contract thresholds must be an object")
    else:
        if thresholds.get("max_time_budget_hours") != 5:
            errors.append("thresholds.max_time_budget_hours must be 5")
        if thresholds.get("minimum_parallel_lanes") != 2:
            errors.append("thresholds.minimum_parallel_lanes must be 2")
    return errors


def _validate_context_index() -> list[str]:
    errors = _file_exists(AGENT_CONTEXT)
    if errors:
        return errors
    payload = _read_json(AGENT_CONTEXT, errors)
    if payload is None:
        return errors
    categories = {
        str(category.get("id")): set(_strings(category.get("paths")))
        for layer in payload.get("layers", [])
        if isinstance(layer, dict)
        for category in layer.get("categories", [])
        if isinstance(category, dict)
    }
    paths = categories.get("codex_5h_batch_run_envelope")
    if paths is None:
        errors.append("agent-context/index.json missing codex_5h_batch_run_envelope category")
        return errors
    for path in sorted(REQUIRED_CONTEXT_CATEGORY_PATHS - paths):
        errors.append(f"agent-context/index.json missing codex_5h_batch_run_envelope path {path}")
    for path in sorted(paths):
        if not (REPO_ROOT / path).exists():
            errors.append(f"agent-context/index.json path does not exist: {path}")
    contracts = set(_strings(payload.get("verification_contracts")))
    contract_path = "workflows/verification-contracts/codex-5h-batch-run-envelope.verification.json"
    if contract_path not in contracts:
        errors.append(f"agent-context/index.json verification_contracts missing {contract_path}")
    return errors


def _validate_cli_and_quality_gate() -> list[str]:
    errors: list[str] = []
    for path in (CLI, QUALITY_GATE):
        errors.extend(_file_exists(path))
    if errors:
        return errors
    cli_text = CLI.read_text(encoding="utf-8")
    quality_text = QUALITY_GATE.read_text(encoding="utf-8")
    for marker in (
        "agent-batch",
        "command_agent_batch",
        "load_batch_run_envelope",
        "validate_codex_5h_batch_run_envelope.py",
    ):
        if marker not in cli_text:
            errors.append(f"src/nac_cli/cli.py missing marker {marker}")
    for marker in (
        "codex_5h_batch_run_envelope",
        "validate_codex_5h_batch_run_envelope.py",
    ):
        if marker not in quality_text:
            errors.append(f"scripts/quality_gate.py missing marker {marker}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_docs = (DOC_DE, DOC_EN, OPS_DE, OPS_EN, AGENT_CONTEXT_DE, AGENT_CONTEXT_EN, CONTRACT_README)
    for path in required_docs:
        errors.extend(_file_exists(path))
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if _contains_prohibited_marker(text):
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker")
    for path in (DOC_DE, DOC_EN):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in (
            "agent-context/index.json",
            "worktree",
            "subagent",
            "owner",
            "Verification",
            "no live",
        ):
            if marker.lower() not in text.lower():
                errors.append(f"{path.relative_to(REPO_ROOT)} missing marker {marker}")
    for path in (OPS_DE, OPS_EN, AGENT_CONTEXT_DE, AGENT_CONTEXT_EN, CONTRACT_README):
        if path.is_file() and "codex-5h-batch-run-envelope" not in path.read_text(encoding="utf-8"):
            errors.append(f"{path.relative_to(REPO_ROOT)} must link codex-5h-batch-run-envelope")
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"JSON file missing: {path.relative_to(REPO_ROOT)}")
        return None
    text = path.read_text(encoding="utf-8")
    if _contains_prohibited_marker(text):
        errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)} is not valid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} must be a JSON object")
        return None
    return payload


def _file_exists(path: Path) -> list[str]:
    if path.is_file():
        return []
    return [f"Required file missing: {path.relative_to(REPO_ROOT)}"]


def _contains_prohibited_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in PROHIBITED_MARKERS)


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


if __name__ == "__main__":
    raise SystemExit(main())
