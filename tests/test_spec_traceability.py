from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import validate_spec_traceability


REPO_ROOT = Path(__file__).resolve().parents[1]


class SpecTraceabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_repo_root = validate_spec_traceability.REPO_ROOT

    def tearDown(self) -> None:
        validate_spec_traceability.REPO_ROOT = self.original_repo_root

    def test_contract_declares_required_spec_manifest_fields(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "workflows/contracts/spec-traceability.contract.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(contract["schema_version"], "nac.spec-traceability/v0.1")
        self.assertEqual(
            contract["required_manifest_fields"],
            [
                "schema_version",
                "spec_id",
                "leading_issue",
                "risk_gate",
                "delivery_mode",
                "acceptance_ids",
                "validation_commands",
            ],
        )
        self.assertIn("AC-001", contract["acceptance_id_pattern_examples"])

    def test_process_policy_enables_spec_traceability(self) -> None:
        policy = validate_spec_traceability.load_simple_yaml_mapping(
            REPO_ROOT / "policies/process-policy.yaml"
        )
        spec_traceability = policy["spec_traceability"]

        self.assertTrue(spec_traceability["enabled"])
        self.assertTrue(spec_traceability["require_acceptance_ids_for_nontrivial_specs"])
        self.assertEqual(
            spec_traceability["contract"],
            "workflows/contracts/spec-traceability.contract.json",
        )
        self.assertIn("scripts/validate_spec_traceability.py", spec_traceability["enforced_by"])

    def test_issue_and_pr_templates_expose_spec_traceability_fields(self) -> None:
        required_markers = (
            "## Spec-Traceability",
            "Spec:",
            "Plan:",
            "Akzeptanzkriterien:",
            "AC-IDs:",
            "Test-/Validator-Nachweis:",
        )
        for relative_path in (
            ".github/ISSUE_TEMPLATE/bug_report.md",
            ".github/ISSUE_TEMPLATE/compliance_change.md",
            ".github/ISSUE_TEMPLATE/feature_request.md",
            ".github/ISSUE_TEMPLATE/process_release.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
        ):
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            with self.subTest(path=relative_path):
                for marker in required_markers:
                    self.assertIn(marker, text)

    def test_strict_quality_gate_runs_spec_traceability_validator(self) -> None:
        quality_gate = (REPO_ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")

        self.assertIn("spec_traceability", quality_gate)
        self.assertIn("scripts/validate_spec_traceability.py", quality_gate)

    def test_validator_accepts_well_formed_manifest_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs/de/superpowers/specs").mkdir(parents=True)
            spec = root / "docs/de/superpowers/specs/example.md"
            spec.write_text(
                "\n".join(
                    (
                        "# Example Spec",
                        "",
                        "```nac-spec-traceability",
                        "schema_version: nac.spec-traceability/v0.1",
                        "spec_id: example-spec",
                        "leading_issue: https://github.com/notariat8/NaC/issues/1",
                        "risk_gate: Policy",
                        "delivery_mode: Owner Direct",
                        "acceptance_ids:",
                        "  - AC-001",
                        "validation_commands:",
                        "  - python scripts/validate_spec_traceability.py",
                        "```",
                        "",
                        "## Akzeptanz",
                        "",
                        "- AC-001: Beispielkriterium.",
                    )
                ),
                encoding="utf-8",
            )
            validate_spec_traceability.REPO_ROOT = root

            self.assertEqual(validate_spec_traceability.validate_manifest_blocks(), [])

    def test_validator_reports_missing_acceptance_id_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs/de/superpowers/specs").mkdir(parents=True)
            spec = root / "docs/de/superpowers/specs/example.md"
            spec.write_text(
                "\n".join(
                    (
                        "# Example Spec",
                        "",
                        "```nac-spec-traceability",
                        "schema_version: nac.spec-traceability/v0.1",
                        "spec_id: example-spec",
                        "leading_issue: https://github.com/notariat8/NaC/issues/1",
                        "risk_gate: Policy",
                        "delivery_mode: Owner Direct",
                        "acceptance_ids:",
                        "  - AC-404",
                        "validation_commands:",
                        "  - python scripts/validate_spec_traceability.py",
                        "```",
                        "",
                        "## Akzeptanz",
                        "",
                        "- AC-001: Beispielkriterium.",
                    )
                ),
                encoding="utf-8",
            )
            validate_spec_traceability.REPO_ROOT = root

            errors = validate_spec_traceability.validate_manifest_blocks()

        self.assertIn(
            "Akzeptanz-ID aus Manifest fehlt im Spec-Text: docs/de/superpowers/specs/example.md AC-404",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
