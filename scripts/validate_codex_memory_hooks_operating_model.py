from __future__ import annotations

import fnmatch
import json
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "agent-context" / "index.json"
VERIFICATION_PATH = REPO_ROOT / "workflows" / "verification-contracts" / "codex-memory-hooks.verification.json"
CODEX_CONFIG = REPO_ROOT / ".codex" / "config.toml"
HOOK_README = REPO_ROOT / ".codex" / "hooks" / "README.md"
HOOK_EXAMPLE = REPO_ROOT / ".codex" / "hooks" / "pre_tool_use_policy.example.py"
QUALITY_GATE = REPO_ROOT / "scripts" / "quality_gate.py"
NAC_CLI = REPO_ROOT / "src" / "nac_cli" / "cli.py"
TEST_FILE = REPO_ROOT / "tests" / "test_codex_memory_hooks_operating_model.py"

REQUIRED_DOCS = (
    "docs/de/operations/codex-memory-hooks-operating-model.md",
    "docs/en/operations/codex-memory-hooks-operating-model.md",
)
REQUIRED_DOC_MARKERS = {
    "docs/en/operations/codex-memory-hooks-operating-model.md": {
        "memory": {
            "Codex Memory",
            "Repository artifact",
            "GitHub issue/PR",
            "Search index or MCP",
            "do not store",
            "source of truth",
        },
        "hooks": {
            "does not activate hooks",
            "not suitable",
            "owner gates",
            "quality gate",
        },
    },
    "docs/de/operations/codex-memory-hooks-operating-model.md": {
        "memory": {
            "Codex Memory",
            "Repo-Artefakt",
            "GitHub Issue/PR",
            "Suchindex oder MCP",
            "nicht speichern",
            "Quelle",
        },
        "hooks": {
            "aktiviert keine hooks",
            "nicht geeignet",
            "owner-gates",
            "quality gate",
        },
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
PROHIBITED_HOOK_CODE_MARKERS = {
    "import subprocess",
    "import requests",
    "from requests",
    "import urllib",
    "from urllib",
    "import http.client",
    "open(",
    "Path(",
    "os.environ",
    "socket",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: Codex memory/hooks operating model keeps memory source boundaries, opt-in hooks and no live activation.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_docs())
    errors.extend(_validate_hook_files())
    errors.extend(_validate_config())
    errors.extend(_validate_index())
    errors.extend(_validate_verification_contract())
    errors.extend(_validate_quality_gate_and_cli())
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    for rel_path in REQUIRED_DOCS:
        path = REPO_ROOT / rel_path
        if not path.is_file():
            errors.append(f"Pflichtdokument fehlt: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        errors.extend(_check_prohibited_markers(rel_path, text))
        normalized = " ".join(text.split())
        required = REQUIRED_DOC_MARKERS.get(rel_path, {"memory": set(), "hooks": set()})
        for marker in required["memory"]:
            if marker not in normalized:
                errors.append(f"{rel_path} fehlt Memory-Marker: {marker}")
        lowered = normalized.lower()
        for marker in required["hooks"]:
            if marker not in lowered:
                errors.append(f"{rel_path} fehlt Hook-Grenzmarker: {marker}")
        if "workflows/verification-contracts/codex-memory-hooks.verification.json" not in text:
            errors.append(f"{rel_path} muss codex-memory-hooks.verification.json referenzieren")
        if "validate_codex_memory_hooks_operating_model.py" not in text:
            errors.append(f"{rel_path} muss validate_codex_memory_hooks_operating_model.py referenzieren")
    return errors


def _validate_hook_files() -> list[str]:
    errors: list[str] = []
    if not HOOK_README.is_file():
        errors.append(".codex/hooks/README.md fehlt")
    else:
        text = HOOK_README.read_text(encoding="utf-8")
        errors.extend(_check_prohibited_markers(".codex/hooks/README.md", text))
        for marker in ("opt-in", "does not activate", "Out of scope", "quality gate"):
            if marker not in text:
                errors.append(f".codex/hooks/README.md fehlt Marker: {marker}")
        if "validate_codex_memory_hooks_operating_model.py" not in text:
            errors.append(".codex/hooks/README.md muss den Memory-/Hooks-Validator nennen")

    if not HOOK_EXAMPLE.is_file():
        return errors + [".codex/hooks/pre_tool_use_policy.example.py fehlt"]

    hook_text = HOOK_EXAMPLE.read_text(encoding="utf-8")
    errors.extend(_check_prohibited_markers(".codex/hooks/pre_tool_use_policy.example.py", hook_text))
    for marker in PROHIBITED_HOOK_CODE_MARKERS:
        if marker in hook_text:
            errors.append(f".codex/hooks/pre_tool_use_policy.example.py darf {marker} nicht verwenden")
    if "json.dumps" not in hook_text or "sys.stdin.read" not in hook_text:
        errors.append(".codex/hooks/pre_tool_use_policy.example.py muss stdin lesen und JSON ausgeben")
    try:
        py_compile.compile(str(HOOK_EXAMPLE), doraise=True)
    except py_compile.PyCompileError as exc:
        errors.append(f".codex/hooks/pre_tool_use_policy.example.py kompiliert nicht: {exc}")
    errors.extend(_run_hook_smoke())
    return errors


def _run_hook_smoke() -> list[str]:
    payload = {"command": "python3 scripts/quality_gate.py --profile strict"}
    result = subprocess.run(
        [sys.executable, str(HOOK_EXAMPLE)],
        input=json.dumps(payload),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if result.returncode != 0:
        return [f"Hook-Beispiel-Smoke fehlgeschlagen: rc={result.returncode} stderr={result.stderr.strip()}"]
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return [f"Hook-Beispiel-Smoke gibt kein JSON aus: {exc}"]
    if not isinstance(parsed, dict) or parsed.get("status") != "ok":
        return ["Hook-Beispiel-Smoke muss status=ok liefern"]
    hints = parsed.get("hints")
    if not isinstance(hints, list) or not hints:
        return ["Hook-Beispiel-Smoke muss Quality-Gate-Hinweis liefern"]
    return []


def _validate_config() -> list[str]:
    if not CODEX_CONFIG.is_file():
        return [".codex/config.toml fehlt"]
    text = CODEX_CONFIG.read_text(encoding="utf-8")
    if "[[hooks." in text or "[hooks." in text:
        return [".codex/config.toml darf keine Live-Hooks aktivieren"]
    if "pre_tool_use_policy.example.py" in text:
        return [".codex/config.toml darf das Hook-Beispiel nicht live referenzieren"]
    return []


def _validate_index() -> list[str]:
    errors: list[str] = []
    payload = _read_json(INDEX_PATH, errors)
    if payload is None:
        return errors
    categories = {
        category.get("id"): category.get("paths")
        for layer in payload.get("layers", [])
        if isinstance(layer, dict)
        for category in layer.get("categories", [])
        if isinstance(category, dict)
    }
    memory_paths = set(_string_list(categories.get("memory_hooks")))
    required = {
        "docs/de/operations/codex-memory-hooks-operating-model.md",
        "docs/en/operations/codex-memory-hooks-operating-model.md",
        ".codex/hooks/README.md",
        ".codex/hooks/pre_tool_use_policy.example.py",
        "workflows/verification-contracts/codex-memory-hooks.verification.json",
    }
    for missing in sorted(required - memory_paths):
        errors.append(f"agent-context/index.json: memory_hooks fehlt Pfad {missing}")
    contracts = set(_string_list(payload.get("verification_contracts")))
    if "workflows/verification-contracts/codex-memory-hooks.verification.json" not in contracts:
        errors.append("agent-context/index.json: verification_contracts fehlt codex-memory-hooks.verification.json")
    return errors


def _validate_verification_contract() -> list[str]:
    errors: list[str] = []
    payload = _read_json(VERIFICATION_PATH, errors)
    if payload is None:
        return errors
    if payload.get("schema_version") != "nac.verification-contract/v0.1":
        errors.append("codex-memory-hooks.verification.json: schema_version muss nac.verification-contract/v0.1 sein")
    if payload.get("contract_id") != "verification.codex_memory_hooks":
        errors.append("codex-memory-hooks.verification.json: contract_id muss verification.codex_memory_hooks sein")
    applies_when = payload.get("applies_when")
    paths = _string_list(applies_when.get("paths")) if isinstance(applies_when, dict) else []
    for required in (
        ".codex/hooks/**",
        "docs/*/operations/codex-memory-hooks-operating-model.md",
        "scripts/validate_codex_memory_hooks_operating_model.py",
        "tests/test_codex_memory_hooks_operating_model.py",
    ):
        if required not in paths:
            errors.append(f"codex-memory-hooks.verification.json: applies_when.paths fehlt {required}")
    for pattern in paths:
        if not _path_or_glob_matches(pattern):
            errors.append(f"codex-memory-hooks.verification.json: applies_when.paths matcht nichts: {pattern}")
    for field in ("checks", "invariants", "required_evidence"):
        if not _string_list(payload.get(field)):
            errors.append(f"codex-memory-hooks.verification.json: {field} muss nicht leer sein")
    pass_condition = payload.get("pass_condition")
    if not isinstance(pass_condition, dict) or pass_condition.get("no_live_hook_activation") is not True:
        errors.append("codex-memory-hooks.verification.json: pass_condition.no_live_hook_activation muss true sein")
    failure_behavior = payload.get("failure_behavior")
    if not isinstance(failure_behavior, dict) or failure_behavior.get("hook_activation_detected") != "fail_closed":
        errors.append("codex-memory-hooks.verification.json: hook_activation_detected muss fail_closed sein")
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict) or thresholds.get("hook_example_timeout_seconds") != 30:
        errors.append("codex-memory-hooks.verification.json: thresholds.hook_example_timeout_seconds muss 30 sein")
    return errors


def _validate_quality_gate_and_cli() -> list[str]:
    errors: list[str] = []
    for path, label in (
        (QUALITY_GATE, "scripts/quality_gate.py"),
        (NAC_CLI, "src/nac_cli/cli.py"),
        (TEST_FILE, "tests/test_codex_memory_hooks_operating_model.py"),
    ):
        if not path.is_file():
            errors.append(f"Pflichtdatei fehlt: {label}")
            continue
        text = path.read_text(encoding="utf-8")
        if "validate_codex_memory_hooks_operating_model.py" not in text:
            errors.append(f"{label} bindet validate_codex_memory_hooks_operating_model.py nicht ein")
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"JSON-Datei fehlt: {path.relative_to(REPO_ROOT)}")
        return None
    text = path.read_text(encoding="utf-8")
    errors.extend(_check_prohibited_markers(path.relative_to(REPO_ROOT).as_posix(), text))
    payload = json.loads(text)
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} muss JSON-Objekt sein")
        return None
    return payload


def _check_prohibited_markers(label: str, text: str) -> list[str]:
    return [
        f"{label} enthaelt unzulaessigen Marker: {marker}"
        for marker in PROHIBITED_MARKERS
        if marker.lower() in text.lower()
    ]


def _path_or_glob_matches(pattern: str) -> bool:
    if any(char in pattern for char in "*?["):
        return any(fnmatch.fnmatch(path.relative_to(REPO_ROOT).as_posix(), pattern) for path in REPO_ROOT.rglob("*"))
    return (REPO_ROOT / pattern).exists()


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


if __name__ == "__main__":
    raise SystemExit(main())
