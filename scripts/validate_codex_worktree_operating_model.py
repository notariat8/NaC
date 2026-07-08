from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_git.worktree_hygiene import SCHEMA_VERSION, build_worktree_audit  # noqa: E402


REQUIRED_FILES = {
    "de_doc": REPO_ROOT / "docs/de/operations/codex-worktree-operating-model.md",
    "en_doc": REPO_ROOT / "docs/en/operations/codex-worktree-operating-model.md",
    "de_ops_index": REPO_ROOT / "docs/de/operations/README.md",
    "en_ops_index": REPO_ROOT / "docs/en/operations/README.md",
    "de_cli": REPO_ROOT / "docs/de/cli.md",
    "en_cli": REPO_ROOT / "docs/en/cli.md",
    "de_quality": REPO_ROOT / "docs/de/quality-gate.md",
    "en_quality": REPO_ROOT / "docs/en/quality-gate.md",
    "cli": REPO_ROOT / "src/nac_cli/cli.py",
    "module": REPO_ROOT / "src/nac_git/worktree_hygiene.py",
    "quality_gate": REPO_ROOT / "scripts/quality_gate.py",
}

REQUIRED_DOC_MARKERS = {
    "nac git worktree-audit",
    "git worktree add ../NaC-<slug> -b <branch>",
    "git worktree remove",
    "git branch -d",
    "git push origin --delete",
    "read-only",
    "owner-gated",
    "Subagents",
    "Forks",
}

PROHIBITED_MARKERS = {
    "client" + "_secret",
    "BEGIN " + "PRIVATE KEY",
    "BEGIN " + "CERTIFICATE",
    "gh" + "p_",
    "gh" + "o_",
    "real_mandate_data_sample",
}


def validate_files() -> list[str]:
    errors: list[str] = []
    for label, path in REQUIRED_FILES.items():
        if not path.is_file():
            errors.append(f"Pflichtdatei fehlt ({label}): {path.relative_to(REPO_ROOT)}")
    return errors


def validate_docs() -> list[str]:
    errors: list[str] = []
    for path in (REQUIRED_FILES["de_doc"], REQUIRED_FILES["en_doc"]):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in REQUIRED_DOC_MARKERS:
            if marker not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} fehlt Marker: {marker}")
        if "Mandatsdaten" not in text and "mandate data" not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} muss Mandatsdaten/mandate data ausschliessen")
        for marker in PROHIBITED_MARKERS:
            if marker.lower() in text.lower():
                errors.append(f"{path.relative_to(REPO_ROOT)} enthaelt unzulaessigen Marker: {marker}")

    for path in (REQUIRED_FILES["de_ops_index"], REQUIRED_FILES["en_ops_index"]):
        if path.is_file() and "codex-worktree-operating-model.md" not in path.read_text(encoding="utf-8"):
            errors.append(f"{path.relative_to(REPO_ROOT)} verlinkt das Worktree Operating Model nicht")

    for path in (REQUIRED_FILES["de_cli"], REQUIRED_FILES["en_cli"]):
        if path.is_file() and "nac git worktree-audit" not in path.read_text(encoding="utf-8"):
            errors.append(f"{path.relative_to(REPO_ROOT)} dokumentiert nac git worktree-audit nicht")

    return errors


def validate_code() -> list[str]:
    errors: list[str] = []
    module_path = REQUIRED_FILES["module"]
    cli_path = REQUIRED_FILES["cli"]
    quality_gate_path = REQUIRED_FILES["quality_gate"]

    if module_path.is_file():
        text = module_path.read_text(encoding="utf-8")
        for marker in (
            SCHEMA_VERSION,
            "destructive_actions_executed",
            "github_api_used",
            "network_used",
            "cleanup_candidates",
            "owner_gate_required",
        ):
            if marker not in text:
                errors.append(f"{module_path.relative_to(REPO_ROOT)} fehlt Marker: {marker}")
        for prohibited in ("git worktree remove", "git branch -d ", "git push origin --delete"):
            if prohibited in text:
                errors.append(
                    f"{module_path.relative_to(REPO_ROOT)} darf keine Cleanup-Befehle ausfuehren oder hardcoden: {prohibited}"
                )

    if cli_path.is_file():
        cli_text = cli_path.read_text(encoding="utf-8")
        if "worktree-audit" not in cli_text:
            errors.append("src/nac_cli/cli.py bindet worktree-audit nicht ein")
        if "build_worktree_audit" not in cli_text:
            errors.append("src/nac_cli/cli.py nutzt build_worktree_audit nicht")

    for path in (quality_gate_path, REQUIRED_FILES["de_quality"], REQUIRED_FILES["en_quality"]):
        if path.is_file() and "codex_worktree_operating_model" not in path.read_text(encoding="utf-8"):
            errors.append(f"{path.relative_to(REPO_ROOT)} enthaelt codex_worktree_operating_model nicht")

    return errors


def validate_runtime_contract() -> list[str]:
    errors: list[str] = []
    try:
        payload = build_worktree_audit(REPO_ROOT)
    except Exception as exc:  # pragma: no cover - validation error surface
        return [f"build_worktree_audit(REPO_ROOT) ist fehlgeschlagen: {exc}"]

    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("Worktree-Audit liefert falsche schema_version")
    summary = payload.get("summary", {})
    if summary.get("destructive_actions_executed") is not False:
        errors.append("Worktree-Audit muss destructive_actions_executed=false melden")
    if summary.get("github_api_used") is not False:
        errors.append("Worktree-Audit muss github_api_used=false melden")
    if summary.get("network_used") is not False:
        errors.append("Worktree-Audit muss network_used=false melden")
    if summary.get("stores_secrets") is not False:
        errors.append("Worktree-Audit muss stores_secrets=false melden")
    for candidate in payload.get("cleanup_candidates", []):
        if candidate.get("owner_gate_required") is not True:
            errors.append(f"Cleanup-Kandidat ohne owner_gate_required=true: {candidate}")
        if candidate.get("destructive_action_executed") is not False:
            errors.append(f"Cleanup-Kandidat muss destructive_action_executed=false melden: {candidate}")
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(validate_files())
    errors.extend(validate_docs())
    errors.extend(validate_code())
    errors.extend(validate_runtime_contract())

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: Codex Worktree Operating Model ist dokumentiert, CLI-gebunden, read-only und im Quality Gate verankert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

