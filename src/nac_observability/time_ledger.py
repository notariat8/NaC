from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "nac.codex-time-ledger/v0.1"
SUMMARY_SCHEMA_VERSION = "nac.codex-time-ledger-summary/v0.1"

CATEGORY_CHOICES = (
    "llm_backend",
    "local_cpu",
    "local_io",
    "remote_io",
    "remote_cpu",
    "approval_wait",
    "user_wait",
    "editing",
    "review",
    "validation",
    "other",
)

OUTCOME_CHOICES = ("completed", "failed", "interrupted")


def parse_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def build_entry(
    *,
    session_id: str,
    task: str,
    phase: str,
    category: str,
    started_at: datetime,
    ended_at: datetime,
    actor: str = "codex",
    outcome: str = "completed",
    command: str = "",
    notes: str = "",
    exit_code: int | None = None,
) -> dict[str, Any]:
    if category not in CATEGORY_CHOICES:
        raise ValueError(f"Unknown time-ledger category: {category}")
    if outcome not in OUTCOME_CHOICES:
        raise ValueError(f"Unknown time-ledger outcome: {outcome}")
    if ended_at < started_at:
        raise ValueError("ended_at must not be earlier than started_at")

    duration_ms = int((ended_at - started_at).total_seconds() * 1000)
    entry: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id,
        "task": task,
        "phase": phase,
        "category": category,
        "actor": actor,
        "started_at": format_timestamp(started_at),
        "ended_at": format_timestamp(ended_at),
        "duration_ms": duration_ms,
        "outcome": outcome,
    }
    if command:
        entry["command"] = command
    if notes:
        entry["notes"] = notes
    if exit_code is not None:
        entry["exit_code"] = exit_code
    return entry


def append_entry(path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True, sort_keys=True))
        handle.write("\n")
    return entry


def load_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if entry.get("schema_version") != SCHEMA_VERSION:
                raise ValueError(f"Unsupported time-ledger schema at {path}:{line_number}")
            entries.append(entry)
    return entries


def summarize_entries(
    entries: list[dict[str, Any]],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    selected = [
        entry
        for entry in entries
        if session_id is None or entry.get("session_id") == session_id
    ]
    total_duration_ms = sum(int(entry.get("duration_ms", 0)) for entry in selected)

    by_category = _group_duration(selected, "category", total_duration_ms)
    by_phase = _group_duration(selected, "phase", total_duration_ms)
    sessions = sorted({str(entry.get("session_id", "")) for entry in selected if entry.get("session_id")})

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "entries": len(selected),
        "sessions": sessions,
        "total_duration_ms": total_duration_ms,
        "total_duration_seconds": round(total_duration_ms / 1000, 3),
        "by_category": by_category,
        "by_phase": by_phase,
    }


def _group_duration(
    entries: list[dict[str, Any]],
    key: str,
    total_duration_ms: int,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"entries": 0, "duration_ms": 0})
    for entry in entries:
        group = str(entry.get(key, "unknown") or "unknown")
        grouped[group]["entries"] += 1
        grouped[group]["duration_ms"] += int(entry.get("duration_ms", 0))

    return {
        group: {
            "entries": values["entries"],
            "duration_ms": values["duration_ms"],
            "duration_seconds": round(values["duration_ms"] / 1000, 3),
            "share": round(values["duration_ms"] / total_duration_ms, 4)
            if total_duration_ms
            else 0.0,
        }
        for group, values in sorted(grouped.items())
    }


def format_summary_text(summary: dict[str, Any]) -> str:
    lines = [
        "NaC Codex Time Ledger",
        f"- Entries: {summary['entries']}",
        f"- Total: {summary['total_duration_seconds']} s",
    ]
    if summary["sessions"]:
        lines.append(f"- Sessions: {', '.join(summary['sessions'])}")
    lines.append("")
    lines.append("By category")
    for category, values in summary["by_category"].items():
        percent = values["share"] * 100
        lines.append(
            f"- {category}: {values['duration_seconds']} s "
            f"({percent:.1f}%, {values['entries']} entries)"
        )
    lines.append("")
    lines.append("By phase")
    for phase, values in summary["by_phase"].items():
        percent = values["share"] * 100
        lines.append(
            f"- {phase}: {values['duration_seconds']} s "
            f"({percent:.1f}%, {values['entries']} entries)"
        )
    return "\n".join(lines)


def run_timed_command(
    *,
    log_path: Path,
    session_id: str,
    task: str,
    phase: str,
    category: str,
    command: list[str],
    cwd: Path,
    actor: str = "codex",
    notes: str = "",
) -> tuple[int, dict[str, Any]]:
    if not command:
        raise ValueError("time-ledger run needs a child command")
    if command[0] == "--":
        command = command[1:]
    if not command:
        raise ValueError("time-ledger run needs a child command")

    started_at = datetime.now(tz=UTC)
    result = subprocess.run(command, cwd=cwd, check=False)
    ended_at = datetime.now(tz=UTC)
    outcome = "completed" if result.returncode == 0 else "failed"
    entry = build_entry(
        session_id=session_id,
        task=task,
        phase=phase,
        category=category,
        started_at=started_at,
        ended_at=ended_at,
        actor=actor,
        outcome=outcome,
        command=" ".join(command),
        notes=notes,
        exit_code=result.returncode,
    )
    append_entry(log_path, entry)
    return result.returncode, entry
