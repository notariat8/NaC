from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GLOBAL_GANTT = "roadmap/GANTT.md"
AREA_GANTTS = {
    "plugins": "plugins/GANTT.md",
    "workflows": "workflows/GANTT.md",
    "usecases": "usecases/GANTT.md",
}
IGNORED_PREFIXES = (
    "out/",
    ".git/",
)
MERMAID_GANTT_RESERVED_TASK_STARTS = (
    "gantt",
    "section",
    "dateformat",
    "axisformat",
    "tickinterval",
    "excludes",
    "includes",
    "todaymarker",
    "title",
    "acc_title",
    "acc_descr",
)


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def is_zero_sha(value: str) -> bool:
    return bool(value) and set(value) == {"0"}


def event_before_sha() -> str:
    before = os.environ.get("GITHUB_EVENT_BEFORE", "")
    if before:
        return before

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return ""

    try:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(payload.get("before", ""))


def diff_names(args: list[str]) -> set[str]:
    result = run_git(args)
    if result.returncode != 0:
        print("ERROR: Konnte Git-Diff fuer Gantt-Pruefung nicht bestimmen.")
        print(result.stderr.strip())
        return set()
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def changed_files() -> set[str]:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    base_ref = os.environ.get("GITHUB_BASE_REF", "")

    if event_name == "push":
        before = event_before_sha()
        if before and not is_zero_sha(before):
            return diff_names(["diff", "--name-only", f"{before}...HEAD"])
        return diff_names(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"])

    if base_ref:
        run_git(["fetch", "--no-tags", "origin", base_ref])
        return diff_names(["diff", "--name-only", f"origin/{base_ref}...HEAD"])

    files = diff_names(["diff", "--name-only", "HEAD"])
    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    if untracked.returncode != 0:
        print("ERROR: Konnte ungetrackte Dateien fuer Gantt-Pruefung nicht bestimmen.")
        print(untracked.stderr.strip())
        return files

    files.update(
        line.strip().replace("\\", "/")
        for line in untracked.stdout.splitlines()
        if line.strip()
    )
    return files


def relevant(files: set[str]) -> set[str]:
    return {
        path
        for path in files
        if not any(path.startswith(prefix) for prefix in IGNORED_PREFIXES)
    }


def validate_required_files() -> list[str]:
    errors: list[str] = []
    required = [GLOBAL_GANTT, *AREA_GANTTS.values()]
    for rel_path in required:
        if not (REPO_ROOT / rel_path).exists():
            errors.append(f"Pflicht-Gantt fehlt: {rel_path}")
    return errors


def validate_changed_files(files: set[str]) -> list[str]:
    errors: list[str] = []
    if not files:
        return errors

    if GLOBAL_GANTT not in files:
        errors.append(
            f"Jeder Push oder Change-Set muss {GLOBAL_GANTT} aktualisieren."
        )

    for area, gantt_path in AREA_GANTTS.items():
        prefix = f"{area}/"
        area_changed = any(
            path.startswith(prefix) and path != gantt_path
            for path in files
        )
        if area_changed and gantt_path not in files:
            errors.append(
                f"Aenderungen unter {area}/ muessen {gantt_path} aktualisieren."
            )
    return errors


def validate_mermaid_render_safety() -> list[str]:
    errors: list[str] = []
    for rel_path in [GLOBAL_GANTT, *AREA_GANTTS.values()]:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue

        in_mermaid = False
        in_gantt = False
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if line.startswith("```mermaid"):
                in_mermaid = True
                in_gantt = False
                continue
            if in_mermaid and line.startswith("```"):
                in_mermaid = False
                in_gantt = False
                continue
            if not in_mermaid:
                continue
            if line == "gantt":
                in_gantt = True
                continue
            if line.startswith("section "):
                continue
            if not in_gantt or ":" not in line:
                continue

            task_label = line.split(":", maxsplit=1)[0].strip().lower()
            if task_label.startswith(MERMAID_GANTT_RESERVED_TASK_STARTS):
                errors.append(
                    f"{rel_path}:{line_number}: Mermaid-Gantt-Task beginnt mit reserviertem Keyword: {task_label}"
                )
    return errors


def main() -> int:
    errors = validate_required_files()
    files = relevant(changed_files())
    errors.extend(validate_changed_files(files))
    errors.extend(validate_mermaid_render_safety())

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: Gantt-Pflege fuer globalen und thematischen Fortschritt ist eingehalten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
