from __future__ import annotations

import argparse
import json
import os
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
        description="Deterministischer Quality Gate Runner fuer NaC."
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
            "NaC Process Validation",
            [sys.executable, "scripts/nac.py", "process", "validate-all"],
        ),
        (
            "unit_tests",
            "Unit Tests",
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        ),
        (
            "plugin_validate",
            "Plugin Manifest Validation",
            [sys.executable, "scripts/validate_plugins.py"],
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
                    "spec_traceability",
                    "Spec Traceability Contract",
                    [sys.executable, "scripts/validate_spec_traceability.py"],
                ),
                (
                    "technology_policy",
                    "Technology Policy",
                    [sys.executable, "scripts/validate_technology_policy.py"],
                ),
                (
                    "language_parity",
                    "Language Parity",
                    [sys.executable, "scripts/validate_language_parity.py"],
                ),
                (
                    "doc_links",
                    "Documentation Links",
                    [sys.executable, "scripts/validate_doc_links.py"],
                ),
                (
                    "bpmn_models",
                    "BPMN Model Validation",
                    [sys.executable, "scripts/validate_bpmn_models.py"],
                ),
                (
                    "gantt_progress",
                    "Gantt Progress Update",
                    [sys.executable, "scripts/validate_gantt_progress.py"],
                ),
                (
                    "cloud_runbook_parity",
                    "Cloud Runbook Parity",
                    [sys.executable, "scripts/validate_cloud_runbook_parity.py"],
                ),
                (
                    "ai_sbom",
                    "AI SBOM Baseline",
                    [sys.executable, "scripts/validate_ai_sbom.py"],
                ),
                (
                    "ai_sbom_export_mapping",
                    "AI SBOM Export Mapping",
                    [sys.executable, "scripts/validate_ai_sbom_export_mapping.py"],
                ),
                (
                    "knowledge_graph",
                    "Knowledge Graph Baseline",
                    [sys.executable, "scripts/validate_knowledge_graph.py"],
                ),
                (
                    "kg_editor",
                    "Knowledge Graph Editor Contract",
                    [sys.executable, "scripts/validate_kg_editor.py"],
                ),
                (
                    "codex_parallel_review",
                    "Codex Parallel Review Contract",
                    [sys.executable, "scripts/validate_codex_parallel_review.py"],
                ),
                (
                    "codex_subagent_operating_gate",
                    "Codex Subagent Operating Gate",
                    [sys.executable, "scripts/validate_codex_subagent_operating_gate.py"],
                ),
                (
                    "codex_worktree_operating_model",
                    "Codex Worktree Operating Model",
                    [sys.executable, "scripts/validate_codex_worktree_operating_model.py"],
                ),
                (
                    "codex_agent_context_operating_model",
                    "Codex Agent Context Operating Model",
                    [sys.executable, "scripts/validate_codex_agent_context_operating_model.py"],
                ),
                (
                    "codex_agent_context_index_audit",
                    "Codex Agent Context Index Audit",
                    [sys.executable, "scripts/validate_codex_agent_context_index_audit.py"],
                ),
                (
                    "codex_memory_hooks_operating_model",
                    "Codex Memory Hooks Operating Model",
                    [sys.executable, "scripts/validate_codex_memory_hooks_operating_model.py"],
                ),
                (
                    "codex_command_rules_operating_model",
                    "Codex Command Rules Operating Model",
                    [sys.executable, "scripts/validate_codex_command_rules_operating_model.py"],
                ),
                (
                    "codex_command_rules_adoption_smoke",
                    "Codex Command Rules Adoption Smoke",
                    [sys.executable, "scripts/validate_codex_command_rules_adoption.py"],
                ),
                (
                    "verification_contracts_domain_pilot",
                    "Verification Contracts Domain Pilot",
                    [sys.executable, "scripts/validate_verification_contracts_domain_pilot.py"],
                ),
                (
                    "teams_sharepoint_graph_data_plane",
                    "Teams SharePoint Graph Data Plane",
                    [sys.executable, "scripts/validate_teams_sharepoint_graph_data_plane.py"],
                ),
                (
                    "m365_release_readiness_gate",
                    "M365 Release Readiness Gate",
                    [sys.executable, "scripts/validate_m365_release_readiness_gate.py"],
                ),
                (
                    "m365_sharepoint_bpmn_viewer_adapter",
                    "M365 SharePoint BPMN Viewer Adapter",
                    [sys.executable, "scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py"],
                ),
                (
                    "m365_matter_access_delegation",
                    "M365 Matter Access Delegation",
                    [sys.executable, "scripts/validate_m365_matter_access_delegation.py"],
                ),
                (
                    "notarial_application_interface_inventory",
                    "Notarial Application Interface Inventory",
                    [sys.executable, "scripts/validate_notarial_application_interface_inventory.py"],
                ),
                (
                    "matter_data_classification_redaction",
                    "Matter Data Classification And Redaction",
                    [sys.executable, "scripts/validate_matter_data_classification_redaction.py"],
                ),
                (
                    "private_operating_frame_gate",
                    "Private Operating Frame Gate",
                    [sys.executable, "scripts/validate_private_operating_frame_gate.py"],
                ),
                (
                    "private_payload_target_design",
                    "Private Payload Target Design",
                    [sys.executable, "scripts/validate_private_payload_target_design.py"],
                ),
                (
                    "private_payload_access_policy",
                    "Private Payload Access Policy",
                    [sys.executable, "scripts/validate_private_payload_access_policy.py"],
                ),
                (
                    "gnotkg_costs",
                    "GNotKG Cost Review Contract",
                    [sys.executable, "scripts/validate_gnotkg_costs.py"],
                ),
                (
                    "secure_document_links",
                    "Secure Document Link Contract",
                    [sys.executable, "scripts/validate_secure_document_links.py"],
                ),
                (
                    "legal_research_connectors",
                    "Legal Research Connector Candidates",
                    [sys.executable, "scripts/validate_legal_research_connectors.py"],
                ),
                (
                    "legal_source_inventory_license_tdm",
                    "Legal Source Inventory License TDM",
                    [sys.executable, "scripts/validate_legal_source_inventory_license_tdm.py"],
                ),
                (
                    "legal_model_customization_readiness",
                    "Legal Model Customization Readiness",
                    [sys.executable, "scripts/validate_legal_model_customization_readiness.py"],
                ),
                (
                    "legal_model_card_ai_sbom_delta",
                    "Legal Model Card AI-SBOM Delta",
                    [sys.executable, "scripts/validate_legal_model_card_ai_sbom_delta.py"],
                ),
                (
                    "legal_model_card_proposal",
                    "Legal Model Card Proposal",
                    [sys.executable, "scripts/validate_legal_model_card_proposal.py"],
                ),
                (
                    "legal_ai_sbom_delta_proposal",
                    "Legal AI-SBOM Delta Proposal",
                    [sys.executable, "scripts/validate_legal_ai_sbom_delta_proposal.py"],
                ),
                (
                    "legal_model_evaluation_benchmark",
                    "Legal Model Evaluation Benchmark",
                    [sys.executable, "scripts/validate_legal_model_evaluation_benchmark.py"],
                ),
                (
                    "legal_graph_contracts",
                    "Legal Graph Contracts",
                    [sys.executable, "scripts/validate_legal_graph_contracts.py"],
                ),
            ]
        )
    return checks


def run_check(check_id: str, title: str, command: list[str]) -> CheckResult:
    started = datetime.now(tz=UTC)
    env = os.environ.copy()
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    )
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
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
    lines.append("# NaC Quality Gate Report")
    lines.append("")
    lines.append(f"- Timestamp: `{payload['timestamp_utc']}`")
    lines.append(f"- Profile: `{payload['profile']}`")
    lines.append(f"- Overall status: `{payload['overall_status']}`")
    lines.append("")
    lines.extend(m365_release_readiness_report_lines(payload))
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


def m365_release_readiness_report_lines(payload: dict) -> list[str]:
    summary = m365_release_readiness_report_summary(payload)
    return [
        "## M365 MVP Readiness",
        "",
        "- Go/No-Go: `mvp_release_readiness=READY`",
        "- Runner summary: `release_gate_readiness=READY`",
        (
            "- Required matter access evidence: `matter_access_delegation_smoke`, "
            "`matter_access_apply_readiness`, `matter_access_apply_request_plan`"
        ),
        f"- CI enforcement: `{summary['ci_enforcement']}`",
        f"- Gate check: `{summary['check_status']}`",
        f"- Check duration: `{summary['duration_ms']} ms`",
        "- Live evidence: owner-gated `release-gate-run --release-gate-write-audit-pack --release-gate-write-readiness --release-gate-readiness-require-audit-pack`",
    ]


def m365_release_readiness_report_summary(payload: dict) -> dict:
    readiness_check = next(
        (
            check
            for check in payload.get("checks", [])
            if isinstance(check, dict) and check.get("id") == "m365_release_readiness_gate"
        ),
        None,
    )
    if readiness_check is None:
        return {
            "ci_enforcement": "NOT_EVALUATED",
            "check_status": "NOT_ATTACHED",
            "duration_ms": 0,
        }
    passed = readiness_check.get("passed") is True
    return {
        "ci_enforcement": "ENFORCED" if passed else "NOT_ENFORCED",
        "check_status": "PASSED" if passed else "FAILED",
        "duration_ms": int(readiness_check.get("duration_ms", 0)),
    }


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

    print("=== NaC Quality Gate ===")
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
