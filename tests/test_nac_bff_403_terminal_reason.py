"""Synthetic checks for the inactive Stage B terminal-reason contract."""

from __future__ import annotations

import copy
import json
import unittest

from nac_bff.bff_403_terminal_reason import (
    ACTOR_ASSIGNMENT_MISSING,
    CASE_BINDING_INVALID,
    PrivateDecisionResult,
    TERMINAL_REASONS,
    TerminalReasonCapture,
)
from nac_bff.test_environment import AccessDecision
from scripts.quality_gate import build_checks
from scripts.validate_m365_bff_403_terminal_reason import (
    CONTRACT_PATH,
    _unique_pairs,
    validate_contract,
)


class TerminalReasonContractTests(unittest.TestCase):
    def test_duplicate_contract_keys_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            json.loads('{"status":"LOCAL_INACTIVE_ONLY","status":"ACTIVE"}', object_pairs_hook=_unique_pairs)

    def test_strict_quality_gate_runs_terminal_reason_validator(self) -> None:
        check_ids = {check_id for check_id, _, _ in build_checks("strict")}
        self.assertIn("m365_bff_403_terminal_reason", check_ids)

    def test_inactive_contract_and_privacy_boundary_are_fixed(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(validate_contract(contract), [])
        self.assertEqual(contract["status"], "LOCAL_INACTIVE_ONLY")
        self.assertEqual(set(contract["result"]["reason_classes"]), TERMINAL_REASONS)
        self.assertEqual(contract["gates"]["maximum_provider_reads"], 0)
        self.assertEqual(contract["gates"]["maximum_deployments"], 0)
        self.assertFalse(contract["gates"]["sink_authorized"])
        self.assertEqual(
            contract["privacy"]["inference_bearing_classes"],
            ["ACTOR_ASSIGNMENT_MISSING", "DEPUTY_GRANT_INVALID", "GRANT_AUDIT_INVALID"],
        )
        for path, value in (
            (("gates", "sink_authorized"), True),
            (("gates", "provider_read_authorized"), True),
            (("gates", "maximum_deployments"), 1),
            (("privacy", "default_external_reason"), ACTOR_ASSIGNMENT_MISSING),
            (("privacy", "raw_graph_values_allowed"), True),
        ):
            with self.subTest(path=path):
                changed = copy.deepcopy(contract)
                changed[path[0]][path[1]] = value
                self.assertTrue(validate_contract(changed))

    def test_private_result_has_no_sink_and_capture_is_one_shot(self) -> None:
        result = PrivateDecisionResult(AccessDecision.deny(), ACTOR_ASSIGNMENT_MISSING)
        self.assertNotIn(ACTOR_ASSIGNMENT_MISSING, repr(result))
        capture = TerminalReasonCapture()
        capture.record(CASE_BINDING_INVALID)
        self.assertEqual(capture.reason_class, CASE_BINDING_INVALID)
        with self.assertRaises(ValueError):
            capture.record(ACTOR_ASSIGNMENT_MISSING)
        self.assertNotIn(CASE_BINDING_INVALID, repr(capture))
        self.assertFalse(hasattr(capture, "emit"))
        self.assertFalse(hasattr(capture, "flush"))


if __name__ == "__main__":
    unittest.main()
