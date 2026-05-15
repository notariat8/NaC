from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

STANDARD_LANGUAGES = ("de", "en")
CLOUDS = ("aws", "azure", "gcp", "oci")

RUNBOOKS_BY_LANGUAGE = {
    language: {
        f"docs/{language}/eventstream/runbook-{cloud}.md"
        for cloud in CLOUDS
    }
    for language in STANDARD_LANGUAGES
}

RUNBOOKS = set().union(*RUNBOOKS_BY_LANGUAGE.values())

PARITY_RELEVANT = RUNBOOKS | {
    f"docs/{language}/eventstream/implementation-templates.md"
    for language in STANDARD_LANGUAGES
} | {
    f"docs/{language}/eventstream/revisionssicherheit.md"
    for language in STANDARD_LANGUAGES
} | {
    "policies/revisionssicherheit-eventstream-policy.yaml",
    "policies/language-policy.yaml",
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

    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    if untracked.returncode != 0:
        print("ERROR: Konnte ungetrackte Dateien nicht bestimmen.")
        print(untracked.stderr.strip())
        return []

    files = {
        line.strip()
        for output in (diff.stdout, untracked.stdout)
        for line in output.splitlines()
        if line.strip()
    }
    return sorted(files)


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

    for language, expected_runbooks in RUNBOOKS_BY_LANGUAGE.items():
        changed_language_runbooks = changed_runbooks & expected_runbooks
        if changed_language_runbooks and changed_language_runbooks != expected_runbooks:
            print("STATUS: FAILED")
            print("ERROR: Cloud-Runbook-Paritaet verletzt.")
            print(
                "ERROR: Bei Aenderung eines Cloud-Runbooks muessen pro Sprache alle 4 Runbooks synchron geprueft und aktualisiert werden."
            )
            print(f"ERROR: Sprache: {language}")
            print("ERROR: Erwartete Dateien:")
            for path in sorted(expected_runbooks):
                print(f"  - {path}")
            print("ERROR: Geaenderte Runbooks:")
            for path in sorted(changed_language_runbooks):
                print(f"  - {path}")
            return 1

    languages_with_changes = {
        language
        for language, expected_runbooks in RUNBOOKS_BY_LANGUAGE.items()
        if changed_runbooks & expected_runbooks
    }
    if languages_with_changes and languages_with_changes != set(STANDARD_LANGUAGES):
        print("STATUS: FAILED")
        print("ERROR: Cloud-Runbook-Paritaet verletzt.")
        print("ERROR: Cloud-Runbook-Aenderungen muessen in de und en gepflegt werden.")
        print(f"ERROR: Geaenderte Sprachen: {sorted(languages_with_changes)}")
        return 1

    print("STATUS: PASSED")
    print("OK: Alle Cloud-Runbooks wurden pro Standardsprachen synchron aktualisiert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
