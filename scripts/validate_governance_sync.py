from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

POLICY_FILES = {
    "policies/process-policy.yaml",
    "policies/role-model-policy.yaml",
    "policies/github-identity-registry.json",
    "policies/access-control-policy.yaml",
    "policies/revisionssicherheit-eventstream-policy.yaml",
    "policies/tenant-ownership-policy.yaml",
    "policies/provider-open-services-policy.yaml",
}

MIRROR_FILES = {
    "AGENTS.md",
    ".github/copilot-instructions.md",
}

MIRROR_PREFIXES = (".cursor/rules/",)

MANDATORY_ACCESS_POLICY_KEYS = (
    "source_of_truth:",
    "repository_model:",
    "organization_project:",
    "guest_access_rules:",
    "change_control:",
)


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def changed_files() -> list[str]:
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        run_git(["fetch", "--no-tags", "origin", base_ref])
        diff = run_git(["diff", "--name-only", f"origin/{base_ref}...HEAD"])
    else:
        diff = run_git(["diff", "--name-only", "HEAD"])

    if diff.returncode != 0:
        print("ERROR: Konnte geaenderte Dateien nicht bestimmen.")
        print(diff.stderr.strip())
        return []
    return [line.strip() for line in diff.stdout.splitlines() if line.strip()]


def is_policy_file(path: str) -> bool:
    return path in POLICY_FILES


def is_mirror_file(path: str) -> bool:
    return path in MIRROR_FILES or any(path.startswith(prefix) for prefix in MIRROR_PREFIXES)


def validate_access_policy_file() -> list[str]:
    errors: list[str] = []
    policy_path = REPO_ROOT / "policies" / "access-control-policy.yaml"
    if not policy_path.exists():
        errors.append("Pflichtdatei fehlt: policies/access-control-policy.yaml")
        return errors

    text = policy_path.read_text(encoding="utf-8")
    for key in MANDATORY_ACCESS_POLICY_KEYS:
        if key not in text:
            errors.append(f"Pflichtabschnitt fehlt in access-control-policy: {key}")
    return errors


def main() -> int:
    files = changed_files()
    if not files:
        print("INFO: Keine geaenderten Dateien erkannt oder nur nicht relevante Aenderungen.")
        return 0

    policy_changed = any(is_policy_file(path) for path in files)
    mirror_changed = any(is_mirror_file(path) for path in files)

    errors = validate_access_policy_file()

    if mirror_changed and not policy_changed:
        errors.append(
            "Aenderung an AI-Regelflaechen ohne Policy-Aenderung erkannt. "
            "Bitte zuerst Policies unter policies/ aendern und Spiegel synchronisieren."
        )

    if policy_changed and not mirror_changed:
        errors.append(
            "Policy-Aenderung ohne Spiegel-Aktualisierung erkannt. "
            "Bitte AGENTS.md, .github/copilot-instructions.md und relevante .cursor/rules/ synchronisieren."
        )

    if errors:
        print("STATUS: FAILED")
        for entry in errors:
            print(f"ERROR: {entry}")
        return 1

    print("STATUS: PASSED")
    print("OK: Governance-Sync-Regeln eingehalten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
