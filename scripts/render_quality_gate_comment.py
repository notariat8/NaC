from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SRC_ROOT_TEXT = str(SRC_ROOT)
while SRC_ROOT_TEXT in sys.path:
    sys.path.remove(SRC_ROOT_TEXT)
sys.path.insert(0, SRC_ROOT_TEXT)

from notary_kg.catalog import all_case_summaries, load_catalogs


M365_MATTER_ACCESS_POLICY_CONTRACT_ID = "verification.m365_matter_access_delegation"
M365_MATTER_ACCESS_POLICY_NEGATIVE_CASE_IDS = (
    "missing_reason",
    "expired_delegation",
    "workspace_scope_violation",
    "missing_cleanup",
    "audit_readback_missing",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rendert einen kompakten PR-Kommentar fuer den NaC Developer CI Status.")
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
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository-Root fuer KG-Readiness-Auswertung.",
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


def _build_kg_readiness(repo_root: Path) -> dict:
    try:
        catalogs = load_catalogs(repo_root)
        cases = all_case_summaries(catalogs)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "FAILED",
            "error": f"KG readiness konnte nicht geladen werden: {type(exc).__name__}",
            "totals": {
                "catalogs": 0,
                "cases": 0,
                "p0_cases": 0,
                "open_required_information": 0,
                "cases_ready_for_development": 0,
                "value_fields": 0,
            },
            "active_development_candidates": [],
        }

    value_fields = sum(len(case.non_empty_values) for case in cases)
    open_required_information = sum(case.open_required_information for case in cases)
    ready_cases = sum(1 for case in cases if case.ready_for_development)
    status = "READY" if cases and value_fields == 0 else "NEEDS_REVIEW"
    p0_cases = [case for case in cases if case.priority == "P0"]

    return {
        "status": status,
        "totals": {
            "catalogs": len(catalogs),
            "cases": len(cases),
            "p0_cases": len(p0_cases),
            "open_required_information": open_required_information,
            "cases_ready_for_development": ready_cases,
            "value_fields": value_fields,
        },
        "active_development_candidates": [
            {
                "slug": case.slug,
                "open_required_information": case.open_required_information,
                "plugins": list(case.plugin_dependencies),
            }
            for case in p0_cases[:8]
        ],
    }


def _build_markdown(payload: dict, kg_readiness: dict | None = None) -> str:
    marker = "<!-- nac-quality-gate-comment -->"
    status = payload.get("overall_status", "UNKNOWN")
    profile = payload.get("profile", "unknown")
    timestamp = payload.get("timestamp_utc", "unknown")
    checks = payload.get("checks", [])
    kg_readiness = kg_readiness or _build_kg_readiness(REPO_ROOT)
    m365_readiness = _build_m365_release_readiness_summary(payload)
    passed_checks = sum(1 for check in checks if check.get("passed") is True)

    lines: list[str] = [marker, "## NaC Developer CI", ""]
    lines.append(f"- Build Status: **{status}**")
    lines.append(f"- Profil: `{profile}`")
    lines.append(f"- Zeit: `{timestamp}`")
    lines.append(f"- Checks: `{passed_checks}/{len(checks)}` bestanden")
    lines.append("")

    if payload.get("error"):
        lines.append(f"- Fehler: `{payload['error']}`")
        lines.append("")
        lines.extend(_m365_release_readiness_markdown(m365_readiness))
        lines.append("")
        lines.extend(_kg_readiness_markdown(kg_readiness))
        lines.append("")
        lines.append("Artefakte: `out/quality/status.json`, `out/quality/report.md`, `out/quality/comment.md`")
        return "\n".join(lines).rstrip() + "\n"

    lines.append("### Build Checks")
    lines.append("")
    lines.append("| Check | Status | Dauer |")
    lines.append("| --- | --- | --- |")
    for check in checks:
        title = check.get("title", check.get("id", "unknown"))
        passed = bool(check.get("passed", False))
        duration_ms = int(check.get("duration_ms", 0))
        lines.append(f"| `{title}` | {_status_icon(passed)} | `{duration_ms} ms` |")

    lines.append("")
    lines.extend(_m365_release_readiness_markdown(m365_readiness))
    lines.append("")
    lines.extend(_kg_readiness_markdown(kg_readiness))
    lines.append("")
    lines.append("Artefakte: `out/quality/status.json`, `out/quality/report.md`, `out/quality/comment.md`")
    return "\n".join(lines).rstrip() + "\n"


def _build_m365_release_readiness_summary(payload: dict) -> dict:
    checks = payload.get("checks", [])
    readiness_check = next(
        (
            check
            for check in checks
            if isinstance(check, dict) and check.get("id") == "m365_release_readiness_gate"
        ),
        None,
    )
    if readiness_check is None:
        return {
            "ci_enforcement": "NOT_EVALUATED",
            "check_status": "NOT_ATTACHED",
            "check_title": "M365 Release Readiness Gate",
            "duration_ms": 0,
        }
    passed = readiness_check.get("passed") is True
    return {
        "ci_enforcement": "ENFORCED" if passed else "NOT_ENFORCED",
        "check_status": "PASSED" if passed else "FAILED",
        "check_title": readiness_check.get("title", "M365 Release Readiness Gate"),
        "duration_ms": int(readiness_check.get("duration_ms", 0)),
    }


def _m365_release_readiness_markdown(readiness: dict) -> list[str]:
    lines = [
        "### M365 MVP Readiness",
        "",
        "- Go/No-Go: `mvp_release_readiness=READY`",
        "- Runner summary: `release_gate_readiness=READY`",
        (
            "- Required matter access evidence: `matter_access_delegation_smoke`, "
            "`matter_access_apply_readiness`, `matter_access_apply_request_plan`, "
            "`matter_access_apply_policy_smoke`"
        ),
        f"- CI enforcement: **{readiness.get('ci_enforcement', 'UNKNOWN')}**",
        f"- Gate check: `{readiness.get('check_status', 'UNKNOWN')}`",
        f"- Check duration: `{readiness.get('duration_ms', 0)} ms`",
        "- Live evidence: owner-gated `release-gate-run --release-gate-write-audit-pack --release-gate-write-readiness --release-gate-readiness-require-audit-pack`",
    ]
    lines.extend(_m365_matter_access_policy_review_markdown())
    return lines


def _m365_matter_access_policy_review_markdown() -> list[str]:
    case_list = "`, `".join(M365_MATTER_ACCESS_POLICY_NEGATIVE_CASE_IDS)
    return [
        (
            f"- Matter-access verification contract: `{M365_MATTER_ACCESS_POLICY_CONTRACT_ID}` "
            "is required in PR/release review"
        ),
        (
            "- Apply-policy enforcement: `matter_access_apply_policy_smoke` must show "
            "`5/5` negative cases detected"
        ),
        f"- Required negative cases: `{case_list}`",
        "- Required boundary: fail-closed before Graph writes; no tenant writes; exact grant/audit readback and cleanup evidence required",
    ]


def _kg_readiness_markdown(kg_readiness: dict) -> list[str]:
    totals = kg_readiness.get("totals", {})
    lines = ["### KG Readiness", ""]
    lines.append(f"- Status: **{kg_readiness.get('status', 'UNKNOWN')}**")
    if kg_readiness.get("error"):
        lines.append(f"- Fehler: `{kg_readiness['error']}`")
        return lines

    lines.append(f"- Kataloge: `{totals.get('catalogs', 0)}`")
    lines.append(f"- Usecases: `{totals.get('cases', 0)}`")
    lines.append(f"- P0-Usecases: `{totals.get('p0_cases', 0)}`")
    lines.append(f"- Entwicklungsbereit: `{totals.get('cases_ready_for_development', 0)}/{totals.get('cases', 0)}`")
    lines.append(f"- Offene Pflichtinformationen: `{totals.get('open_required_information', 0)}`")
    lines.append(f"- Blockierte `value`-Felder: `{totals.get('value_fields', 0)}`")
    lines.append("")

    candidates = kg_readiness.get("active_development_candidates", [])
    if not candidates:
        lines.append("Keine aktiven KG-Kandidaten gefunden.")
        return lines

    lines.append("| KG-Kandidat | Offene Informationen | Plugins |")
    lines.append("| --- | --- | --- |")
    for candidate in candidates:
        plugins = ", ".join(candidate.get("plugins", [])) or "-"
        lines.append(
            f"| `{candidate.get('slug', 'unknown')}` | "
            f"`{candidate.get('open_required_information', 0)}` | `{plugins}` |"
        )
    return lines


def main() -> int:
    args = parse_args()
    payload = _load_status(args.input)
    rendered = _build_markdown(payload, _build_kg_readiness(args.repo_root.resolve()))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"COMMENT_WRITTEN: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
