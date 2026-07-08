from __future__ import annotations

import fnmatch
import json
import py_compile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "agent-context" / "index.json"
VERIFICATION_CONTRACT = REPO_ROOT / "workflows" / "verification-contracts" / "codex-agent-context.verification.json"
CODEX_CONFIG = REPO_ROOT / ".codex" / "config.toml"
CODEOWNERS = REPO_ROOT / "CODEOWNERS"
REQUIRED_LAYERS = {"always_on", "scoped", "on_demand", "runtime"}
REQUIRED_ARTIFACT_CATEGORIES = {"maps", "history", "guardrails", "command_rules", "memory_hooks"}
REQUIRED_VERIFICATION_FIELDS = {
    "schema_version",
    "contract_id",
    "applies_when",
    "required_context",
    "checks",
    "invariants",
    "thresholds",
    "required_evidence",
    "pass_condition",
    "failure_behavior",
}
REQUIRED_CONTEXT_FIELDS = {"always_on", "scoped", "on_demand", "runtime"}
PROHIBITED_MARKERS = {
    "client" + "_secret",
    "BEGIN " + "PRIVATE KEY",
    "BEGIN " + "CERTIFICATE",
    "gh" + "p_",
    "gh" + "o_",
    "real_mandate_data_sample",
}


def validate_index(path: Path = INDEX_PATH) -> list[str]:
    errors: list[str] = []
    payload = _read_json(path, errors)
    if payload is None:
        return errors
    if payload.get("schema_version") != "nac.agent-context-index/v0.1":
        errors.append("agent-context/index.json: schema_version muss nac.agent-context-index/v0.1 sein")
    guardrails = payload.get("guardrails")
    if not isinstance(guardrails, dict):
        errors.append("agent-context/index.json: guardrails muss ein Objekt sein")
    else:
        expected = {
            "root_agents_md_is_router": True,
            "real_mandate_data_allowed": False,
            "secrets_allowed": False,
            "runtime_logs_loaded_only_for_current_task": True,
            "external_memory_is_source_of_shared_truth": True,
        }
        for key, value in expected.items():
            if guardrails.get(key) is not value:
                errors.append(f"agent-context/index.json: guardrails.{key} muss {value!r} sein")

    layers = payload.get("layers")
    if not isinstance(layers, list):
        return errors + ["agent-context/index.json: layers muss eine Liste sein"]
    layer_ids = {str(item.get("id")) for item in layers if isinstance(item, dict)}
    for missing in sorted(REQUIRED_LAYERS - layer_ids):
        errors.append(f"agent-context/index.json: layer fehlt: {missing}")
    categories: set[str] = set()
    for layer in layers:
        if not isinstance(layer, dict):
            errors.append("agent-context/index.json: layer muss Objekt sein")
            continue
        categories.update(_category_ids(layer.get("categories")))
        for rel_path in _paths(layer):
            if layer.get("id") == "runtime":
                continue
            errors.extend(_validate_path_pattern(rel_path, f"agent-context/index.json:{layer.get('id')}"))
    for missing in sorted(REQUIRED_ARTIFACT_CATEGORIES - categories):
        errors.append(f"agent-context/index.json: on_demand category fehlt: {missing}")
    for rel_path in _string_list(payload.get("verification_contracts")):
        errors.extend(_validate_path_pattern(rel_path, "agent-context/index.json:verification_contracts"))
    return errors


def validate_verification_contract(path: Path = VERIFICATION_CONTRACT) -> list[str]:
    errors: list[str] = []
    payload = _read_json(path, errors)
    if payload is None:
        return errors
    missing_fields = REQUIRED_VERIFICATION_FIELDS - set(payload)
    for field in sorted(missing_fields):
        errors.append(f"{path.relative_to(REPO_ROOT)}: Pflichtfeld fehlt: {field}")
    if payload.get("schema_version") != "nac.verification-contract/v0.1":
        errors.append(f"{path.relative_to(REPO_ROOT)}: schema_version muss nac.verification-contract/v0.1 sein")
    applies_when = payload.get("applies_when")
    if not isinstance(applies_when, dict) or not _string_list(applies_when.get("paths")):
        errors.append(f"{path.relative_to(REPO_ROOT)}: applies_when.paths muss gesetzt sein")
    else:
        for pattern in _string_list(applies_when.get("paths")):
            if not _path_or_glob_matches(pattern):
                errors.append(f"{path.relative_to(REPO_ROOT)}: applies_when.paths matcht nichts: {pattern}")

    required_context = payload.get("required_context")
    if not isinstance(required_context, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)}: required_context muss Objekt sein")
    else:
        for field in sorted(REQUIRED_CONTEXT_FIELDS):
            if not _string_list(required_context.get(field)):
                errors.append(f"{path.relative_to(REPO_ROOT)}: required_context.{field} muss nicht leer sein")

    for field in ("checks", "invariants", "required_evidence"):
        if not _string_list(payload.get(field)):
            errors.append(f"{path.relative_to(REPO_ROOT)}: {field} muss nicht leer sein")
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)}: thresholds muss Objekt sein")
    else:
        expected_thresholds = {
            "max_agent_threads": 6,
            "max_agent_depth": 1,
            "max_agent_runtime_seconds": 1800,
        }
        for key, value in expected_thresholds.items():
            if thresholds.get(key) != value:
                errors.append(f"{path.relative_to(REPO_ROOT)}: thresholds.{key} muss {value} sein")
    pass_condition = payload.get("pass_condition")
    if not isinstance(pass_condition, dict) or pass_condition.get("all_checks_pass") is not True:
        errors.append(f"{path.relative_to(REPO_ROOT)}: pass_condition.all_checks_pass muss true sein")
    failure_behavior = payload.get("failure_behavior")
    if not isinstance(failure_behavior, dict) or failure_behavior.get("quality_gate_failure") != "block_completion":
        errors.append(f"{path.relative_to(REPO_ROOT)}: failure_behavior.quality_gate_failure muss block_completion sein")
    return errors


def validate_docs_and_hooks() -> list[str]:
    errors: list[str] = []
    required_docs = [
        "docs/AGENTS.md",
        "workflows/contracts/AGENTS.md",
        "docs/de/agent-context/README.md",
        "docs/en/agent-context/README.md",
        "docs/de/operations/codex-memory-hooks-operating-model.md",
        "docs/en/operations/codex-memory-hooks-operating-model.md",
        "docs/de/operations/codex-command-rules-operating-model.md",
        "docs/en/operations/codex-command-rules-operating-model.md",
        ".codex/hooks/README.md",
        ".codex/hooks/pre_tool_use_policy.example.py",
        ".codex/rules/README.md",
        ".codex/rules/default.rules",
    ]
    for rel_path in required_docs:
        path = REPO_ROOT / rel_path
        if not path.is_file():
            errors.append(f"Pflichtdatei fehlt: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in PROHIBITED_MARKERS:
            if marker.lower() in text.lower():
                errors.append(f"{rel_path} enthaelt unzulaessigen Marker: {marker}")

    for rel_path in (
        "docs/de/agent-context/README.md",
        "docs/en/agent-context/README.md",
        "docs/de/operations/codex-memory-hooks-operating-model.md",
        "docs/en/operations/codex-memory-hooks-operating-model.md",
        "docs/de/operations/codex-command-rules-operating-model.md",
        "docs/en/operations/codex-command-rules-operating-model.md",
    ):
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        for marker in ("agent-context/index.json", "Verification", "Runtime"):
            if marker not in text:
                errors.append(f"{rel_path} fehlt Marker: {marker}")

    hook_example = REPO_ROOT / ".codex" / "hooks" / "pre_tool_use_policy.example.py"
    try:
        py_compile.compile(str(hook_example), doraise=True)
    except py_compile.PyCompileError as exc:
        errors.append(f"Hook-Beispiel kompiliert nicht: {exc}")

    config_text = CODEX_CONFIG.read_text(encoding="utf-8") if CODEX_CONFIG.is_file() else ""
    if "[[hooks." in config_text or "[hooks." in config_text:
        errors.append(".codex/config.toml darf in diesem Slice keine Live-Hooks aktivieren")
    return errors


def validate_codeowners(path: Path = CODEOWNERS) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return ["CODEOWNERS fehlt"]
    text = path.read_text(encoding="utf-8")
    for pattern in (
        ".codex/agents/*",
        ".codex/hooks/*",
        ".codex/rules/*",
        "agent-context/*",
        "workflows/contracts/*",
        "workflows/verification-contracts/*",
        "scripts/validate_codex_*.py",
    ):
        if pattern not in text:
            errors.append(f"CODEOWNERS fehlt Pattern: {pattern}")
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"JSON-Datei fehlt: {path.relative_to(REPO_ROOT)}")
        return None
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} enthaelt unzulaessigen Marker: {marker}")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)} ist kein gueltiges JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} muss ein JSON-Objekt sein")
        return None
    return payload


def _paths(layer: dict[str, Any]) -> list[str]:
    paths = _string_list(layer.get("paths"))
    for category in layer.get("categories", []):
        if isinstance(category, dict):
            paths.extend(_string_list(category.get("paths")))
    return paths


def _category_ids(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item.get("id")) for item in value if isinstance(item, dict)}


def _validate_path_pattern(pattern: str, source: str) -> list[str]:
    if _path_or_glob_matches(pattern):
        return []
    return [f"{source}: Pfad oder Glob matcht nichts: {pattern}"]


def _path_or_glob_matches(pattern: str) -> bool:
    if any(char in pattern for char in "*?[]"):
        return any(fnmatch.fnmatch(path.as_posix(), pattern) for path in _repo_files())
    return (REPO_ROOT / pattern).exists()


def _repo_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if ".git" in path.parts or "out" in path.parts:
            continue
        if path.is_file():
            files.append(path.relative_to(REPO_ROOT))
    return files


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main() -> int:
    errors: list[str] = []
    errors.extend(validate_index())
    errors.extend(validate_verification_contract())
    errors.extend(validate_docs_and_hooks())
    errors.extend(validate_codeowners())

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: Codex Agent Context Operating Model hat Progressive Disclosure, Artifacts, Hooks und Verification Contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
