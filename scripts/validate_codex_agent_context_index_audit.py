from __future__ import annotations

import json
from pathlib import Path
from typing import Any


if __package__:
    from scripts.scoped_repo_glob import path_or_glob_matches as _path_or_glob_matches
else:
    from scoped_repo_glob import path_or_glob_matches as _path_or_glob_matches


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "agent-context" / "index.json"
QUALITY_GATE = REPO_ROOT / "scripts" / "quality_gate.py"
NAC_CLI = REPO_ROOT / "src" / "nac_cli" / "cli.py"
TEST_FILE = REPO_ROOT / "tests" / "test_codex_agent_context_index_audit.py"
AUDIT_CONTRACT = (
    "workflows/verification-contracts/codex-agent-context-index-audit.verification.json"
)

GATES: dict[str, dict[str, object]] = {
    "worktree_operating_model": {
        "quality_gate_id": "codex_worktree_operating_model",
        "verification_contract": "workflows/verification-contracts/codex-worktree-operating-model.verification.json",
        "validators": ["scripts/validate_codex_worktree_operating_model.py"],
        "tests": ["tests/test_codex_worktree_operating_model.py"],
        "required_paths": [
            "docs/de/operations/codex-worktree-operating-model.md",
            "docs/en/operations/codex-worktree-operating-model.md",
            "src/nac_git/worktree_hygiene.py",
        ],
    },
    "subagent_operating_gate": {
        "quality_gate_id": "codex_subagent_operating_gate",
        "verification_contract": "workflows/verification-contracts/codex-subagent-operating-gate.verification.json",
        "validators": ["scripts/validate_codex_subagent_operating_gate.py"],
        "tests": ["tests/test_codex_subagent_operating_gate.py"],
        "required_paths": [
            "agent-context/subagent-registry.json",
            "docs/de/operations/codex-subagent-operating-gate.md",
            "docs/en/operations/codex-subagent-operating-gate.md",
        ],
    },
    "memory_hooks": {
        "quality_gate_id": "codex_memory_hooks_operating_model",
        "verification_contract": "workflows/verification-contracts/codex-memory-hooks.verification.json",
        "validators": ["scripts/validate_codex_memory_hooks_operating_model.py"],
        "tests": ["tests/test_codex_memory_hooks_operating_model.py"],
        "required_paths": [
            ".codex/hooks/README.md",
            ".codex/hooks/pre_tool_use_policy.example.py",
            "docs/de/operations/codex-memory-hooks-operating-model.md",
            "docs/en/operations/codex-memory-hooks-operating-model.md",
        ],
    },
    "command_rules": {
        "quality_gate_id": "codex_command_rules_operating_model",
        "secondary_quality_gate_id": "codex_command_rules_adoption_smoke",
        "verification_contract": "workflows/verification-contracts/codex-command-rules.verification.json",
        "validators": [
            "scripts/validate_codex_command_rules_operating_model.py",
            "scripts/validate_codex_command_rules_adoption.py",
        ],
        "tests": [
            "tests/test_codex_command_rules_operating_model.py",
            "tests/test_codex_command_rules_adoption.py",
        ],
        "required_paths": [
            "policies/codex-command-rules-policy.json",
            ".codex/rules/README.md",
            ".codex/rules/default.rules",
            "docs/de/operations/codex-command-rules-operating-model.md",
            "docs/en/operations/codex-command-rules-operating-model.md",
        ],
    },
    "codex_5h_batch_run_envelope": {
        "quality_gate_id": "codex_5h_batch_run_envelope",
        "verification_contract": "workflows/verification-contracts/codex-5h-batch-run-envelope.verification.json",
        "validators": ["scripts/validate_codex_5h_batch_run_envelope.py"],
        "tests": ["tests/test_codex_5h_batch_run_envelope.py"],
        "required_paths": [
            "docs/de/operations/codex-5h-batch-run-envelope.md",
            "docs/en/operations/codex-5h-batch-run-envelope.md",
            "src/nac_agent_ops/batch_run_envelope.py",
            "tests/fixtures/agent-ops/codex-5h-batch-run-envelope.valid.json",
        ],
    },
}

PROHIBITED_MARKERS = {
    "client" + "_secret",
    "BEGIN " + "PRIVATE KEY",
    "BEGIN " + "CERTIFICATE",
    "gh" + "p_",
    "gh" + "o_",
    "real_mandate_data_sample",
    "password=",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print(
        "OK: Agent-context index audit cross-links worktree, subagent, "
        "memory/hooks, command-rules and 5h-batch gates for nac contracts verify."
    )
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    index = _read_json(INDEX_PATH, errors)
    if index is not None:
        errors.extend(_validate_index(index))
    errors.extend(_validate_verification_contracts())
    errors.extend(_validate_quality_gate())
    errors.extend(_validate_contracts_verify())
    errors.extend(_validate_docs())
    return errors


def _validate_index(index: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    categories = _category_paths(index)
    verification_contracts = set(_string_list(index.get("verification_contracts")))
    if AUDIT_CONTRACT not in verification_contracts:
        errors.append(f"agent-context/index.json: verification_contracts fehlt {AUDIT_CONTRACT}")

    for gate_id, gate in GATES.items():
        paths = categories.get(gate_id)
        if paths is None:
            errors.append(f"agent-context/index.json: on_demand category fehlt: {gate_id}")
            continue
        required_paths = set(_string_list(gate.get("required_paths")))
        validators = set(_string_list(gate.get("validators")))
        tests = set(_string_list(gate.get("tests")))
        verification_contract = str(gate["verification_contract"])
        expected = required_paths | validators | tests | {verification_contract}
        for missing in sorted(expected - paths):
            errors.append(f"agent-context/index.json:{gate_id} fehlt Pfad {missing}")
        for path in sorted(paths):
            errors.extend(_validate_existing_path(path, f"agent-context/index.json:{gate_id}"))
        if verification_contract not in verification_contracts:
            errors.append(f"agent-context/index.json: verification_contracts fehlt {verification_contract}")
    return errors


def _validate_verification_contracts() -> list[str]:
    errors: list[str] = []
    for contract in [AUDIT_CONTRACT, *[str(gate["verification_contract"]) for gate in GATES.values()]]:
        path = REPO_ROOT / contract
        payload = _read_json(path, errors)
        if payload is None:
            continue
        if payload.get("schema_version") != "nac.verification-contract/v0.1":
            errors.append(f"{contract}: schema_version muss nac.verification-contract/v0.1 sein")
        if not _string_list(payload.get("checks")):
            errors.append(f"{contract}: checks muss nicht leer sein")
        if not _string_list(payload.get("required_evidence")):
            errors.append(f"{contract}: required_evidence muss nicht leer sein")
        applies_when = payload.get("applies_when")
        patterns = _string_list(applies_when.get("paths")) if isinstance(applies_when, dict) else []
        if not patterns:
            errors.append(f"{contract}: applies_when.paths muss nicht leer sein")
        for pattern in patterns:
            if not _path_or_glob_matches(pattern):
                errors.append(f"{contract}: applies_when.paths matcht nichts: {pattern}")
    return errors


def _validate_quality_gate() -> list[str]:
    if not QUALITY_GATE.is_file():
        return ["scripts/quality_gate.py fehlt"]
    text = QUALITY_GATE.read_text(encoding="utf-8")
    errors: list[str] = []
    if "codex_agent_context_index_audit" not in text:
        errors.append("scripts/quality_gate.py enthaelt codex_agent_context_index_audit nicht")
    if "validate_codex_agent_context_index_audit.py" not in text:
        errors.append("scripts/quality_gate.py bindet validate_codex_agent_context_index_audit.py nicht ein")
    for gate_id, gate in GATES.items():
        quality_ids = [str(gate["quality_gate_id"])]
        if gate.get("secondary_quality_gate_id"):
            quality_ids.append(str(gate["secondary_quality_gate_id"]))
        for quality_id in quality_ids:
            if quality_id not in text:
                errors.append(f"scripts/quality_gate.py fehlt Quality-Gate-ID {quality_id} fuer {gate_id}")
    return errors


def _validate_contracts_verify() -> list[str]:
    if not NAC_CLI.is_file():
        return ["src/nac_cli/cli.py fehlt"]
    text = NAC_CLI.read_text(encoding="utf-8")
    errors: list[str] = []
    if "Codex Agent Context Index Audit" not in text:
        errors.append("nac contracts validate muss Codex Agent Context Index Audit ausgeben")
    required_validators = {"scripts/validate_codex_agent_context_index_audit.py"}
    for gate in GATES.values():
        required_validators.update(_string_list(gate.get("validators")))
    for validator in sorted(required_validators):
        if validator not in text and Path(validator).name not in text:
            errors.append(f"nac contracts verify muss {validator} ausfuehren")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    for rel_path in (
        "docs/de/agent-context/README.md",
        "docs/en/agent-context/README.md",
        "workflows/verification-contracts/README.md",
        "docs/de/quality-gate.md",
        "docs/en/quality-gate.md",
    ):
        path = REPO_ROOT / rel_path
        if not path.is_file():
            errors.append(f"Pflichtdokument fehlt: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in PROHIBITED_MARKERS:
            if marker.lower() in text.lower():
                errors.append(f"{rel_path} enthaelt unzulaessigen Marker: {marker}")
    for rel_path in ("docs/de/quality-gate.md", "docs/en/quality-gate.md"):
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        if "codex_agent_context_index_audit" not in text:
            errors.append(f"{rel_path} enthaelt codex_agent_context_index_audit nicht")
    return errors


def _category_paths(index: dict[str, Any]) -> dict[str, set[str]]:
    return {
        str(category.get("id")): set(_string_list(category.get("paths")))
        for layer in index.get("layers", [])
        if isinstance(layer, dict)
        for category in layer.get("categories", [])
        if isinstance(category, dict)
    }


def _validate_existing_path(path: str, label: str) -> list[str]:
    if _path_or_glob_matches(path):
        return []
    return [f"{label}: Pfad existiert nicht oder Glob matcht nichts: {path}"]


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"JSON-Datei fehlt: {path.relative_to(REPO_ROOT)}")
        return None
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} enthaelt unzulaessigen Marker: {marker}")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} muss JSON-Objekt sein")
        return None
    return payload


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


if __name__ == "__main__":
    raise SystemExit(main())
