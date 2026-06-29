from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


PLUGIN_NAME = "nac-bnotk-xnp"
SCHEMA_VERSION = "nac.xnp.workflow-gate/v1"
READER_PROMPT_SCHEMA_VERSION = "nac.xnp.reader-prompt/v1"
READER_PROMPT_SCRIPT = Path(__file__).with_name("reader_prompt.py")
POLICY_FALSE_KEYS = (
    "pin_captured",
    "card_data_captured",
    "xnp_api_key_captured",
    "xnp_login_performed",
    "external_network_calls",
    "productive_xnp_write",
)


def load_reader_prompt_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("nac_xnp_reader_prompt", READER_PROMPT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load XNP reader prompt script: {READER_PROMPT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_evidence(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("XNP reader-prompt evidence must be a JSON object.")
    return payload


def validate_reader_prompt_evidence(evidence: dict[str, Any]) -> None:
    if evidence.get("schema_version") != READER_PROMPT_SCHEMA_VERSION:
        raise ValueError("Unsupported XNP reader-prompt evidence schema.")
    if evidence.get("plugin") != PLUGIN_NAME:
        raise ValueError("XNP reader-prompt evidence belongs to the wrong plugin.")


def build_reader_prompt_evidence(args: argparse.Namespace) -> dict[str, Any]:
    reader_prompt = load_reader_prompt_module()
    reader_args = argparse.Namespace(
        prompt=args.prompt,
        intent=args.intent,
        manual_card_present=args.manual_card_present,
        manual_rfid_off=args.manual_rfid_off,
        probe_morris_api=args.probe_morris_api,
    )
    return reader_prompt.build_evidence(reader_args)


def build_workflow_gate(evidence: dict[str, Any], usecase_slug: str) -> dict[str, Any]:
    validate_reader_prompt_evidence(evidence)
    policy = evidence.get("policy") if isinstance(evidence.get("policy"), dict) else {}
    source_status = str(evidence.get("overall_status", "blocked"))
    policy_compliant = all(policy.get(key) is False for key in POLICY_FALSE_KEYS) and policy.get("localhost_only") is True
    status = _gate_status(source_status, policy_compliant)
    source_prompt_id = str(evidence.get("prompt_id", ""))
    next_required_action = str(evidence.get("next_required_action", "")).strip()

    if not policy_compliant:
        next_required_action = "Reject the reader-prompt evidence before any workflow handoff."

    return {
        "schema_version": SCHEMA_VERSION,
        "plugin": PLUGIN_NAME,
        "workflow_gate": {
            "id": "xnp.reader_prompt_gate",
            "workflow_id": f"{usecase_slug}:xnp-reader-prompt-gate",
            "usecase_slug": usecase_slug,
            "status": status,
            "source_schema_version": READER_PROMPT_SCHEMA_VERSION,
            "source_prompt_id": source_prompt_id,
            "source_status": source_status,
            "source_policy_compliant": policy_compliant,
            "opens_next_step": "local_reader_function_check" if status == "ready_for_operator_review" else "",
        },
        "evidence_summary": {
            "reader_prompt_seen": bool(source_prompt_id),
            "card_gate_status": _card_gate_status(evidence),
            "xnp_local_interface_status": _xnp_local_interface_status(evidence),
            "checks": _checks_summary(evidence),
        },
        "decision": {
            "workflow_can_prepare_next_step": status == "ready_for_operator_review",
            "requires_human_review": True,
            "requires_local_workstation": True,
            "productive_xnp_action_allowed": False,
            "next_required_action": next_required_action,
        },
        "guardrails": {
            "real_mandate_data_in_git": False,
            "pin_captured": False,
            "card_data_captured": False,
            "xnp_api_key_captured": False,
            "xnp_login_performed": False,
            "external_network_calls": False,
            "localhost_only": True,
            "productive_xnp_write": False,
        },
        "actions": [
            {"name": "review_xnp_reader_prompt_evidence"},
            {"name": "confirm_local_workstation_context"},
            {"name": "bind_gate_to_workflow_version"},
            {"name": "create_pull_request"},
        ],
    }


def _gate_status(source_status: str, policy_compliant: bool) -> str:
    if not policy_compliant:
        return "blocked"
    if source_status == "prompted":
        return "ready_for_operator_review"
    if source_status == "manual_review":
        return "manual_review"
    return "blocked"


def _card_gate_status(evidence: dict[str, Any]) -> str:
    card_gate = evidence.get("card_gate_evidence")
    if isinstance(card_gate, dict):
        return str(card_gate.get("overall_status", "unknown"))
    return "unknown"


def _xnp_local_interface_status(evidence: dict[str, Any]) -> str:
    xnp_interface = evidence.get("xnp_local_interface")
    if isinstance(xnp_interface, dict):
        return str(xnp_interface.get("status", "unknown"))
    return "unknown"


def _checks_summary(evidence: dict[str, Any]) -> list[dict[str, str]]:
    checks = evidence.get("checks")
    if not isinstance(checks, list):
        return []
    summary: list[dict[str, str]] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        summary.append(
            {
                "id": str(check.get("id", "")),
                "status": str(check.get("status", "")),
                "severity": str(check.get("severity", "")),
            }
        )
    return summary


def write_output(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a workflow gate from XNP reader-prompt evidence."
    )
    parser.add_argument("--evidence", type=Path, help="Existing XNP reader-prompt evidence JSON.")
    parser.add_argument("--usecase", default="online-gmbh-gruendung", help="Usecase slug for the gate binding.")
    parser.add_argument("--prompt", help="Optional local operator prompt when evidence is generated inline.")
    parser.add_argument(
        "--intent",
        default="reader_function_check",
        choices=["reader_function_check", "xnp_login_preflight", "online_hra_preflight"],
    )
    parser.add_argument("--manual-card-present", default="unknown", choices=["yes", "no", "unknown"])
    parser.add_argument("--manual-rfid-off", default="unknown", choices=["yes", "no", "unknown"])
    parser.add_argument("--probe-morris-api", action="store_true")
    parser.add_argument("--output", type=Path, help="Optional JSON gate output path.")
    parser.add_argument("--json", action="store_true", help="Print full JSON gate to stdout.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero unless the gate can prepare the next step.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        evidence = read_evidence(args.evidence) if args.evidence else build_reader_prompt_evidence(args)
        payload = build_workflow_gate(evidence, args.usecase)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.output:
        write_output(args.output, payload)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        gate = payload["workflow_gate"]
        print(f"{PLUGIN_NAME}: {gate['status']}")
        print(payload["decision"]["next_required_action"])

    if args.strict and payload["workflow_gate"]["status"] != "ready_for_operator_review":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
