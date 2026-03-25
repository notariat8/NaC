from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

RUNBOOKS = {
    "docs/eventstream-runbook-aws.md",
    "docs/eventstream-runbook-azure.md",
    "docs/eventstream-runbook-gcp.md",
    "docs/eventstream-runbook-oci.md",
}

PARITY_RELEVANT = RUNBOOKS | {
    "docs/eventstream-implementation-templates.md",
    "docs/revisionssicherheit-eventstreaming.md",
    "policies/revisionssicherheit-eventstream-policy.yaml",
}


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


def main() -> int:
    files = set(changed_files())
    if not files:
        print("INFO: Keine geaenderten Dateien erkannt.")
        return 0

    touched_parity_surface = any(path in PARITY_RELEVANT for path in files)
    if not touched_parity_surface:
        print("INFO: Keine parity-relevanten Cloud-Runbook-Aenderungen erkannt.")
        return 0

    changed_runbooks = {path for path in files if path in RUNBOOKS}
    if not changed_runbooks:
        print("STATUS: PASSED")
        print("OK: Parity-relevante Aenderungen ohne Runbook-Differenz erkannt.")
        return 0

    if changed_runbooks != RUNBOOKS:
        print("STATUS: FAILED")
        print("ERROR: Cloud-Runbook-Paritaet verletzt.")
        print("ERROR: Bei Aenderung eines Cloud-Runbooks muessen alle 4 Runbooks synchron geprueft und aktualisiert werden.")
        print("ERROR: Erwartete Dateien:")
        for path in sorted(RUNBOOKS):
            print(f"  - {path}")
        print("ERROR: Geaenderte Runbooks:")
        for path in sorted(changed_runbooks):
            print(f"  - {path}")
        return 1

    print("STATUS: PASSED")
    print("OK: Alle vier Cloud-Runbooks wurden synchron aktualisiert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
