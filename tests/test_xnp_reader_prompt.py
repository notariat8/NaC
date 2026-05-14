from __future__ import annotations

import argparse
import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "plugins" / "noc-bnotk-xnp" / "scripts" / "reader_prompt.py"


def load_reader_prompt_module():
    spec = importlib.util.spec_from_file_location("reader_prompt", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reader_prompt = load_reader_prompt_module()


def args(prompt: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(
        prompt=prompt,
        intent="reader_function_check",
        manual_card_present="yes",
        manual_rfid_off="yes",
        probe_morris_api=False,
    )


def cyberjack(status: str) -> dict:
    return {
        "plugin": "noc-cyberjack-rfid",
        "schema_version": "noc.cyberjack.readiness/v1",
        "evidence_id": "CJ-00000000-0000-0000-0000-000000000000",
        "generated_at": "2026-05-14T00:00:00+00:00",
        "overall_status": status,
        "manual_attestations": {},
        "checks": [],
    }


class XnpReaderPromptTests(unittest.TestCase):
    def test_reader_prompt_is_prompted_when_card_gate_ready_and_xnp_reachable(self) -> None:
        evidence = reader_prompt.build_evidence(
            args(),
            cyberjack_evidence=cyberjack("ready"),
            xnp_interface={"status": "reachable", "host": "127.0.0.1", "open_ports": [12774], "api_key_observed": False},
        )

        self.assertEqual(evidence["overall_status"], "prompted")
        self.assertEqual(evidence["reader_prompt"]["route"], "noc-bnotk-xnp -> noc-cyberjack-rfid")
        self.assertFalse(evidence["policy"]["pin_captured"])
        self.assertFalse(evidence["policy"]["xnp_api_key_captured"])
        self.assertFalse(evidence["policy"]["xnp_login_performed"])

    def test_reader_prompt_requires_manual_review_when_xnp_is_not_reachable(self) -> None:
        evidence = reader_prompt.build_evidence(
            args(),
            cyberjack_evidence=cyberjack("ready"),
            xnp_interface={"status": "not_reachable", "host": "127.0.0.1", "port_range": [12774, 12784]},
        )

        self.assertEqual(evidence["overall_status"], "manual_review")

    def test_reader_prompt_blocks_when_card_gate_is_blocked(self) -> None:
        evidence = reader_prompt.build_evidence(
            args(),
            cyberjack_evidence=cyberjack("blocked"),
            xnp_interface={"status": "reachable", "host": "127.0.0.1", "open_ports": [12774], "api_key_observed": False},
        )

        self.assertEqual(evidence["overall_status"], "blocked")

    def test_prompt_text_with_secret_marker_is_rejected(self) -> None:
        evidence = reader_prompt.build_evidence(
            args("Bitte PIN 123456 testen"),
            cyberjack_evidence=cyberjack("ready"),
            xnp_interface={"status": "reachable", "host": "127.0.0.1", "open_ports": [12774], "api_key_observed": False},
        )

        self.assertEqual(evidence["overall_status"], "blocked")
        self.assertNotIn("123456", evidence["reader_prompt"]["text"])


if __name__ == "__main__":
    unittest.main()
