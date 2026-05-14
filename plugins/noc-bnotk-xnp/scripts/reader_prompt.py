from __future__ import annotations

import argparse
import importlib.util
import json
import socket
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any


PLUGIN_NAME = "noc-bnotk-xnp"
SCHEMA_VERSION = "noc.xnp.reader-prompt/v1"
REPO_ROOT = Path(__file__).resolve().parents[3]
CYBERJACK_SCRIPT = REPO_ROOT / "plugins" / "noc-cyberjack-rfid" / "scripts" / "check_readiness.py"
XNP_PORTS = range(12774, 12785)
DEFAULT_READER_PROMPT = (
    "Bitte pruefen Sie lokal am XNP-Arbeitsplatz, ob der cyberJack Kartenleser "
    "auf die Kartenpruefung reagiert. Keine PIN, Kartendaten oder XNP-API-Keys "
    "in Codex eingeben."
)
FORBIDDEN_PROMPT_TERMS = [
    "api key",
    "api-key",
    "api_key",
    "apikey",
    "pin",
    "passwort",
    "password",
    "token",
    "secret",
    "private key",
]


def utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def check_result(
    check_id: str,
    title: str,
    status: str,
    severity: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": status,
        "severity": severity,
        "message": message,
        "details": details or {},
    }


def load_cyberjack_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("noc_cyberjack_readiness", CYBERJACK_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load cyberJack readiness script: {CYBERJACK_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sanitize_prompt(value: str | None) -> tuple[str, bool]:
    if value is None or not value.strip():
        return DEFAULT_READER_PROMPT, False

    prompt = value.strip()
    lowered = prompt.lower()
    if any(term in lowered for term in FORBIDDEN_PROMPT_TERMS):
        return DEFAULT_READER_PROMPT, True
    return prompt[:500], False


def probe_xnp_local_interface() -> dict[str, Any]:
    open_ports: list[int] = []
    for port in XNP_PORTS:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                open_ports.append(port)
        except OSError:
            continue

    if open_ports:
        return {
            "status": "reachable",
            "host": "127.0.0.1",
            "open_ports": open_ports,
            "api_key_observed": False,
        }
    return {
        "status": "not_reachable",
        "host": "127.0.0.1",
        "port_range": [min(XNP_PORTS), max(XNP_PORTS)],
        "api_key_observed": False,
    }


def build_cyberjack_evidence(args: argparse.Namespace) -> dict[str, Any]:
    cyberjack = load_cyberjack_module()
    cyberjack_args = argparse.Namespace(
        manual_card_present=args.manual_card_present,
        manual_rfid_off=args.manual_rfid_off,
        probe_morris_api=getattr(args, "probe_morris_api", False),
    )
    return cyberjack.build_evidence(cyberjack_args)


def summarize_cyberjack_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    checks = []
    for check in evidence.get("checks", []):
        if not isinstance(check, dict):
            continue
        checks.append(
            {
                "id": check.get("id"),
                "status": check.get("status"),
                "severity": check.get("severity"),
                "message": check.get("message"),
            }
        )
    return {
        "plugin": evidence.get("plugin"),
        "schema_version": evidence.get("schema_version"),
        "evidence_id": evidence.get("evidence_id"),
        "generated_at": evidence.get("generated_at"),
        "overall_status": evidence.get("overall_status"),
        "manual_attestations": evidence.get("manual_attestations", {}),
        "checks": checks,
    }


def evaluate_status(
    prompt_rejected: bool,
    cyberjack_status: str,
    xnp_interface_status: str,
) -> str:
    if prompt_rejected or cyberjack_status == "blocked":
        return "blocked"
    if cyberjack_status != "ready" or xnp_interface_status != "reachable":
        return "manual_review"
    return "prompted"


def next_required_action(status: str) -> str:
    if status == "blocked":
        return "Resolve the blocker before any XNP login or reader-function test."
    if status == "manual_review":
        return "Complete local XNP, card-gate and reader review before treating the reader prompt as successful."
    return "Proceed with the local XNP reader-function check; human approval is still required for any PIN or login step."


def build_evidence(
    args: argparse.Namespace,
    cyberjack_evidence: dict[str, Any] | None = None,
    xnp_interface: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prompt, prompt_rejected = sanitize_prompt(args.prompt)
    card_gate = cyberjack_evidence if cyberjack_evidence is not None else build_cyberjack_evidence(args)
    xnp_local = xnp_interface if xnp_interface is not None else probe_xnp_local_interface()
    cyberjack_status = str(card_gate.get("overall_status") or "manual_review")
    xnp_status = str(xnp_local.get("status") or "not_reachable")
    status = evaluate_status(prompt_rejected, cyberjack_status, xnp_status)

    checks = [
        check_result(
            "prompt_policy",
            "Reader prompt policy",
            "failed" if prompt_rejected else "passed",
            "blocker" if prompt_rejected else "info",
            (
                "Prompt text looked like it may contain a secret and was replaced with the default safe prompt."
                if prompt_rejected
                else "Reader prompt is safe for evidence metadata."
            ),
            {"prompt_rejected": prompt_rejected},
        ),
        check_result(
            "cyberjack_card_gate",
            "CyberJack Card SAK Gate",
            "passed" if cyberjack_status == "ready" else "manual_review" if cyberjack_status == "manual_review" else "failed",
            "info" if cyberjack_status == "ready" else "manual" if cyberjack_status == "manual_review" else "blocker",
            f"Referenced cyberJack readiness status is {cyberjack_status}.",
            {"evidence_id": card_gate.get("evidence_id")},
        ),
        check_result(
            "xnp_local_interface",
            "XNP localhost interface",
            "passed" if xnp_status == "reachable" else "manual_review",
            "info" if xnp_status == "reachable" else "manual",
            (
                "XNP localhost interface is reachable without reading or using an API key."
                if xnp_status == "reachable"
                else "XNP localhost interface is not reachable in the expected port range."
            ),
            xnp_local,
        ),
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "plugin": PLUGIN_NAME,
        "prompt_id": f"XNP-RP-{uuid.uuid4()}",
        "generated_at": utc_now(),
        "overall_status": status,
        "mode": "local_dry_run",
        "intent": args.intent,
        "reader_prompt": {
            "target": "local_cyberjack_reader",
            "route": "noc-bnotk-xnp -> noc-cyberjack-rfid",
            "text": prompt,
            "operator_actions": [
                "Use the local workstation where XNP and the card reader are installed.",
                "Use only the approved local cyberJack reader and BNotK chip/signature card.",
                "Confirm locally whether the reader display, LED or XNP/card path reacts.",
                "Do not enter PINs, card values, certificates, passwords or XNP API keys into Codex.",
            ],
            "dry_run_only": True,
        },
        "xnp_local_interface": xnp_local,
        "card_gate_evidence": summarize_cyberjack_evidence(card_gate),
        "policy": {
            "pin_captured": False,
            "card_data_captured": False,
            "xnp_api_key_captured": False,
            "xnp_login_performed": False,
            "external_network_calls": False,
            "localhost_only": True,
            "productive_xnp_write": False,
        },
        "checks": checks,
        "next_required_action": next_required_action(status),
    }


def write_output(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a local XNP reader prompt and card-gate evidence preview."
    )
    parser.add_argument(
        "--prompt",
        help="Optional local operator prompt for the reader-function check. Do not include secrets.",
    )
    parser.add_argument(
        "--intent",
        default="reader_function_check",
        choices=["reader_function_check", "xnp_login_preflight", "online_hra_preflight"],
        help="Reader prompt intent.",
    )
    parser.add_argument(
        "--manual-card-present",
        default="unknown",
        choices=["yes", "no", "unknown"],
        help="Manual attestation passed to the cyberJack card gate.",
    )
    parser.add_argument(
        "--manual-rfid-off",
        default="unknown",
        choices=["yes", "no", "unknown"],
        help="Manual attestation that RFID is disabled or not used for the BNotK chip-card workflow.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON evidence output path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON evidence to stdout.",
    )
    parser.add_argument(
        "--probe-morris-api",
        action="store_true",
        help="Ask the cyberJack card gate to actively test the local morris localhost API and PC/SC listreaders path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code unless the reader prompt is fully ready.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    evidence = build_evidence(args)

    if args.output:
        write_output(args.output, evidence)

    if args.json:
        print(json.dumps(evidence, indent=2, ensure_ascii=True))
    else:
        print(f"{PLUGIN_NAME}: {evidence['overall_status']}")
        print(evidence["next_required_action"])

    if args.strict and evidence["overall_status"] != "prompted":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
