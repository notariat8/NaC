from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "plugins" / "nac-bnotk-xnp" / "scripts" / "workflow_gate.py"
CONTRACT_PATH = REPO_ROOT / "plugins" / "nac-bnotk-xnp" / "contracts" / "workflow-gate-evidence.schema.json"


def load_workflow_gate_module():
    spec = importlib.util.spec_from_file_location("xnp_workflow_gate", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workflow_gate = load_workflow_gate_module()


def reader_prompt(status: str = "prompted") -> dict:
    return {
        "schema_version": "nac.xnp.reader-prompt/v1",
        "plugin": "nac-bnotk-xnp",
        "prompt_id": "XNP-RP-00000000-0000-0000-0000-000000000000",
        "generated_at": "2026-06-29T00:00:00+00:00",
        "overall_status": status,
        "mode": "local_dry_run",
        "intent": "reader_function_check",
        "reader_prompt": {
            "target": "local_cyberjack_reader",
            "route": "nac-bnotk-xnp -> nac-cyberjack-rfid",
            "text": "Bitte testen. Kein Secret.",
            "operator_actions": [],
            "dry_run_only": True,
        },
        "xnp_local_interface": {"status": "reachable", "host": "127.0.0.1", "open_ports": [12774]},
        "card_gate_evidence": {"overall_status": "ready", "evidence_id": "CJ-000"},
        "policy": {
            "pin_captured": False,
            "card_data_captured": False,
            "xnp_api_key_captured": False,
            "xnp_login_performed": False,
            "external_network_calls": False,
            "localhost_only": True,
            "productive_xnp_write": False,
        },
        "checks": [
            {"id": "prompt_policy", "title": "Prompt", "status": "passed", "severity": "info", "message": "", "details": {}}
        ],
        "next_required_action": "Proceed with the local XNP reader-function check.",
    }


class XnpWorkflowGateTests(unittest.TestCase):
    def test_prompted_reader_evidence_opens_operator_review_without_copying_prompt_text(self) -> None:
        payload = workflow_gate.build_workflow_gate(reader_prompt(), "online-gmbh-gruendung")
        serialized = json.dumps(payload, sort_keys=True).lower()

        self.assertEqual(payload["schema_version"], "nac.xnp.workflow-gate/v1")
        self.assertEqual(payload["workflow_gate"]["workflow_id"], "online-gmbh-gruendung:xnp-reader-prompt-gate")
        self.assertEqual(payload["workflow_gate"]["status"], "ready_for_operator_review")
        self.assertTrue(payload["decision"]["workflow_can_prepare_next_step"])
        self.assertTrue(payload["decision"]["requires_human_review"])
        self.assertFalse(payload["decision"]["productive_xnp_action_allowed"])
        self.assertEqual(payload["evidence_summary"]["card_gate_status"], "ready")
        self.assertNotIn("bitte testen", serialized)
        self.assertFalse(_contains_key(payload, "value"))

    def test_manual_review_reader_evidence_keeps_gate_in_manual_review(self) -> None:
        payload = workflow_gate.build_workflow_gate(reader_prompt("manual_review"), "online-gmbh-gruendung")

        self.assertEqual(payload["workflow_gate"]["status"], "manual_review")
        self.assertFalse(payload["decision"]["workflow_can_prepare_next_step"])

    def test_policy_violation_blocks_gate(self) -> None:
        evidence = reader_prompt()
        evidence["policy"]["xnp_login_performed"] = True

        payload = workflow_gate.build_workflow_gate(evidence, "online-gmbh-gruendung")

        self.assertEqual(payload["workflow_gate"]["status"], "blocked")
        self.assertFalse(payload["workflow_gate"]["source_policy_compliant"])
        self.assertIn("Reject", payload["decision"]["next_required_action"])

    def test_cli_reads_existing_evidence_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "xnp-reader-prompt.json"
            evidence_path.write_text(json.dumps(reader_prompt()), encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                rc = workflow_gate.main(["--evidence", str(evidence_path), "--json"])

        self.assertEqual(rc, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["schema_version"], "nac.xnp.workflow-gate/v1")

    def test_wrong_schema_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            workflow_gate.build_workflow_gate({"schema_version": "wrong", "plugin": "nac-bnotk-xnp"}, "online-gmbh-gruendung")

    def test_workflow_gate_contract_tracks_payload_schema(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

        self.assertEqual(contract["properties"]["schema_version"]["const"], "nac.xnp.workflow-gate/v1")
        self.assertIn("workflow_gate", contract["required"])
        self.assertIn("guardrails", contract["required"])


if __name__ == "__main__":
    unittest.main()


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False
