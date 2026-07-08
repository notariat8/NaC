from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = REPO_ROOT / "policies" / "codex-command-rules-policy.json"
QUALITY_GATE = REPO_ROOT / "scripts" / "quality_gate.py"
NAC_CLI = REPO_ROOT / "src" / "nac_cli" / "cli.py"
TEST_FILE = REPO_ROOT / "tests" / "test_codex_command_rules_adoption.py"

PROFILE_MARKERS = {
    "GREEN",
    "YELLOW",
    "RED",
    "policies/codex-command-rules-policy.json",
    ".codex/rules/default.rules",
}
DOC_MARKERS = {
    "GREEN",
    "YELLOW",
    "RED",
    "codex-command-rules-policy.json",
    ".codex/rules/default.rules",
}
PROHIBITED_MARKERS = {
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
    print("OK: Codex command rules adoption smoke covers batch docs, owner-gate runbooks and agent profiles.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    policy = _read_json(POLICY, errors)
    if not policy:
        return errors
    adoption = policy.get("adoption_smoke")
    if not isinstance(adoption, dict):
        return errors + ["codex-command-rules-policy.json missing adoption_smoke"]

    required_docs = _strings(adoption.get("required_docs"))
    required_profiles = _strings(adoption.get("required_agent_profiles"))
    required_markers = set(_strings(adoption.get("required_markers")))
    if not required_docs:
        errors.append("adoption_smoke.required_docs must not be empty")
    if not required_profiles:
        errors.append("adoption_smoke.required_agent_profiles must not be empty")
    if not DOC_MARKERS <= required_markers:
        errors.append("adoption_smoke.required_markers must include GREEN/YELLOW/RED and policy/rules paths")

    for rel_path in required_docs:
        errors.extend(_validate_doc(rel_path))
    for rel_path in required_profiles:
        errors.extend(_validate_profile(rel_path))

    for rel_path in (
        "docs/de/operations/README.md",
        "docs/en/operations/README.md",
    ):
        text = _read_text(rel_path, errors)
        if text and "codex-command-rules-operating-model.md" not in text:
            errors.append(f"{rel_path} must index codex-command-rules-operating-model.md")

    quality_text = QUALITY_GATE.read_text(encoding="utf-8")
    if "validate_codex_command_rules_adoption.py" not in quality_text:
        errors.append("quality_gate.py must run validate_codex_command_rules_adoption.py")
    cli_text = NAC_CLI.read_text(encoding="utf-8")
    if "validate_codex_command_rules_adoption.py" not in cli_text:
        errors.append("nac contracts validate/verify must run validate_codex_command_rules_adoption.py")
    test_text = TEST_FILE.read_text(encoding="utf-8") if TEST_FILE.is_file() else ""
    if "test_adoption_policy_lists_batch_docs_and_agent_profiles" not in test_text:
        errors.append("tests must cover command-rules adoption policy")
    return errors


def _validate_doc(rel_path: str) -> list[str]:
    errors: list[str] = []
    text = _read_text(rel_path, errors)
    if not text:
        return errors
    for marker in DOC_MARKERS:
        if marker not in text:
            errors.append(f"{rel_path} missing marker {marker}")
    if "owner" not in text.lower():
        errors.append(f"{rel_path} must mention owner-gated boundary")
    return errors


def _validate_profile(rel_path: str) -> list[str]:
    errors: list[str] = []
    text = _read_text(rel_path, errors)
    if not text:
        return errors
    for marker in PROFILE_MARKERS:
        if marker not in text:
            errors.append(f"{rel_path} missing marker {marker}")
    if "sandbox_mode = \"read-only\"" not in text:
        errors.append(f"{rel_path} must stay read-only")
    if "destructive/secret/credential/deploy/productive-apply" not in text:
        errors.append(f"{rel_path} must preserve RED command boundary language")
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if not text:
        errors.append(f"missing JSON file {path.relative_to(REPO_ROOT)}")
        return None
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker {marker}")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} must be a JSON object")
        return None
    return payload


def _read_text(rel_path: str, errors: list[str]) -> str:
    path = REPO_ROOT / rel_path
    if not path.is_file():
        errors.append(f"missing required adoption file {rel_path}")
        return ""
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{rel_path} contains prohibited marker {marker}")
    return text


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
