from __future__ import annotations

import argparse
import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "plugins" / "noc-cyberjack-rfid" / "scripts" / "check_readiness.py"


def load_readiness_module():
    spec = importlib.util.spec_from_file_location("check_readiness", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


readiness = load_readiness_module()


class CyberJackReadinessTests(unittest.TestCase):
    def test_hash_identifier_does_not_return_raw_value(self) -> None:
        raw = "USB\\VID_0C4B&PID_0504\\SERIAL-EXAMPLE"
        hashed = readiness.hash_identifier(raw)
        self.assertIsNotNone(hashed)
        self.assertTrue(hashed.startswith("sha256:"))
        self.assertNotIn(raw, hashed)

    def test_overall_status_blocks_on_blocker_failure(self) -> None:
        checks = [
            readiness.check_result("card", "Card", "failed", "blocker", "Missing card"),
            readiness.check_result("pcsc", "PCSC", "passed", "info", "Running"),
        ]
        self.assertEqual(readiness.evaluate_overall_status(checks), "blocked")

    def test_overall_status_requires_manual_review_for_unknowns(self) -> None:
        checks = [
            readiness.check_result("card", "Card", "passed", "info", "Present"),
            readiness.check_result("reader", "Reader", "manual_review", "manual", "Confirm reader"),
        ]
        self.assertEqual(readiness.evaluate_overall_status(checks), "manual_review")

    def test_manual_attestations_are_reflected_in_evidence(self) -> None:
        args = argparse.Namespace(manual_card_present="yes", manual_rfid_off="no")
        original_probes = (
            readiness.probe_pcsc_service,
            readiness.probe_reader_detection,
            readiness.probe_named_process,
            readiness.probe_xnp_local_interface,
            readiness.probe_ausweisapp_status,
        )
        readiness.probe_pcsc_service = lambda: readiness.check_result("pcsc", "PCSC", "passed", "info", "Running")
        readiness.probe_reader_detection = lambda: readiness.check_result("reader", "Reader", "passed", "info", "Present")
        readiness.probe_named_process = lambda check_id, title, needles: readiness.check_result(
            check_id,
            title,
            "passed",
            "info",
            "Running",
        )
        readiness.probe_xnp_local_interface = lambda: readiness.check_result("xnp", "XNP", "passed", "info", "Open")
        readiness.probe_ausweisapp_status = lambda: readiness.check_result("ausweisapp", "AusweisApp", "passed", "info", "Reachable")
        try:
            evidence = readiness.build_evidence(args)
        finally:
            (
                readiness.probe_pcsc_service,
                readiness.probe_reader_detection,
                readiness.probe_named_process,
                readiness.probe_xnp_local_interface,
                readiness.probe_ausweisapp_status,
            ) = original_probes

        self.assertEqual(evidence["plugin"], "noc-cyberjack-rfid")
        self.assertEqual(evidence["overall_status"], "blocked")
        self.assertFalse(evidence["policy"]["pin_captured"])
        self.assertFalse(evidence["policy"]["card_data_captured"])
        self.assertFalse(evidence["policy"]["xnp_api_key_captured"])
        self.assertEqual(evidence["manual_attestations"]["bnotk_card_present"], "yes")
        self.assertEqual(
            evidence["manual_attestations"]["rfid_disabled_for_bnotk_chip_workflow"],
            "no",
        )


if __name__ == "__main__":
    unittest.main()
