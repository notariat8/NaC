from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(slots=True)
class CheckResult:
    id: str
    title: str
    command: list[str]
    return_code: int
    passed: bool
    duration_ms: int
    output: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministischer Quality Gate Runner fuer OaC8."
    )
    parser.add_argument(
        "--profile",
        choices=["minimal", "standard", "strict"],
        default="standard",
        help="Pruefprofil fuer den Lauf.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("out/quality/status.json"),
        help="Pfad fuer maschinenlesbares Ergebnis.",
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("out/quality/report.md"),
        help="Pfad fuer menschenlesbaren Report.",
    )
    return parser.parse_args()


def build_checks(profile: str) -> list[tuple[str, str, list[str]]]:
    checks: list[tuple[str, str, list[str]]] = [
        (
            "process_validate",
            "Process Validation",
            [sys.executable, "-m", "business_os", "validate-all", "--repo-root", "."],
        ),
        (
            "unit_tests",
            "Unit Tests",
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        ),
    ]

    if profile in {"standard", "strict"}:
        checks.append(
            (
                "privacy_lint",
                "Privacy Lint",
                [sys.executable, "scripts/privacy_lint.py"],
            )
        )

    if profile == "strict":
        checks.extend(
            [
                (
                    "governance_sync",
                    "Governance Policy Sync",
                    [sys.executable, "scripts/validate_governance_sync.py"],
                ),
                (
                    "cloud_runbook_parity",
                    "Cloud Runbook Parity",
                    [sys.executable, "scripts/validate_cloud_runbook_parity.py"],
                ),
            ]
        )
    return checks


def run_check(check_id: str, title: str, command: list[str]) -> CheckResult:
    started = datetime.now(tz=UTC)
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    finished = datetime.now(tz=UTC)
    output = "\n".join(
        part.strip() for part in [result.stdout, result.stderr] if part and part.strip()
    ).strip()
    duration_ms = int((finished - started).total_seconds() * 1000)
    return CheckResult(
        id=check_id,
        title=title,
        command=command,
        return_code=result.returncode,
        passed=result.returncode == 0,
        duration_ms=duration_ms,
        output=output,
    )


def write_json(path: Path, payload: dict) -> None:
    absolute = path if path.is_absolute() else REPO_ROOT / path
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def write_markdown(path: Path, payload: dict) -> None:
    absolute = path if path.is_absolute() else REPO_ROOT / path
    absolute.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# OaC8 Quality Gate Report")
    lines.append("")
    lines.append(f"- Timestamp: `{payload['timestamp_utc']}`")
    lines.append(f"- Profile: `{payload['profile']}`")
    lines.append(f"- Overall status: `{payload['overall_status']}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")

    for check in payload["checks"]:
        status = "PASSED" if check["passed"] else "FAILED"
        lines.append(f"### {check['title']} ({check['id']})")
        lines.append("")
        lines.append(f"- Status: `{status}`")
        lines.append(f"- Return code: `{check['return_code']}`")
        lines.append(f"- Duration: `{check['duration_ms']} ms`")
        lines.append(f"- Command: `{ ' '.join(check['command']) }`")
        if check["output"]:
            lines.append("")
            lines.append("```text")
            lines.append(check["output"])
            lines.append("```")
        lines.append("")

    absolute.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    checks_to_run = build_checks(args.profile)
    results = [run_check(check_id, title, command) for check_id, title, command in checks_to_run]
    passed = all(item.passed for item in results)

    status_payload = {
        "timestamp_utc": datetime.now(tz=UTC).isoformat(),
        "profile": args.profile,
        "overall_status": "PASSED" if passed else "FAILED",
        "checks": [asdict(item) for item in results],
    }

    write_json(args.json_output, status_payload)
    write_markdown(args.md_output, status_payload)

    print("=== OaC8 Quality Gate ===")
    print(f"PROFILE: {args.profile}")
    print(f"STATUS: {status_payload['overall_status']}")
    for item in results:
        state = "OK" if item.passed else "ERROR"
        print(f"{state}: {item.id} ({item.duration_ms} ms)")
    print(f"JSON: {args.json_output}")
    print(f"REPORT: {args.md_output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
