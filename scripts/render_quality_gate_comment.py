from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rendert einen kompakten PR-Kommentar fuer den OaC8 Quality Gate.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("out/quality/status.json"),
        help="Pfad zur JSON-Statusdatei des Quality Gates.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("out/quality/comment.md"),
        help="Pfad zur generierten Markdown-Kommentardatei.",
    )
    return parser.parse_args()


def _status_icon(passed: bool) -> str:
    return "✅" if passed else "❌"


def _load_status(path: Path) -> dict:
    if not path.exists():
        return {
            "overall_status": "FAILED",
            "profile": "unknown",
            "timestamp_utc": "unknown",
            "checks": [],
            "error": f"Statusdatei fehlt: {path}",
        }
    return json.loads(path.read_text(encoding="utf-8"))


def _build_markdown(payload: dict) -> str:
    marker = "<!-- oac8-quality-gate-comment -->"
    status = payload.get("overall_status", "UNKNOWN")
    profile = payload.get("profile", "unknown")
    timestamp = payload.get("timestamp_utc", "unknown")
    checks = payload.get("checks", [])

    lines: list[str] = [marker, "## OaC8 Quality Gate", ""]
    lines.append(f"- Status: **{status}**")
    lines.append(f"- Profil: `{profile}`")
    lines.append(f"- Zeit: `{timestamp}`")
    lines.append("")

    if payload.get("error"):
        lines.append(f"- Fehler: `{payload['error']}`")
        lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    lines.append("| Check | Status | Dauer |")
    lines.append("| --- | --- | --- |")
    for check in checks:
        title = check.get("title", check.get("id", "unknown"))
        passed = bool(check.get("passed", False))
        duration_ms = int(check.get("duration_ms", 0))
        lines.append(f"| `{title}` | {_status_icon(passed)} | `{duration_ms} ms` |")

    lines.append("")
    lines.append("Artefakte: `out/quality/status.json`, `out/quality/report.md`")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    payload = _load_status(args.input)
    rendered = _build_markdown(payload)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"COMMENT_WRITTEN: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
