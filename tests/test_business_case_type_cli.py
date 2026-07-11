from __future__ import annotations

import argparse
import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli import cli as nac_cli  # noqa: E402
from notary_kg.business_case_type_runtime import BusinessCaseTypeCatalog  # noqa: E402
from scripts.validate_business_case_type_runtime import validate_agent_context, validate_verification_contract  # noqa: E402
from notary_kg.cli import main as notary_kg_main  # noqa: E402


class BusinessCaseTypeRuntimeCliTests(unittest.TestCase):
    def _fixture(self, business_case_type_id: str) -> dict[str, object]:
        catalog = BusinessCaseTypeCatalog.from_repo(REPO_ROOT)
        return {
            "status": "OK",
            "rows": [
                {
                    "business_case_type_id": business_case_type_id,
                    "lifecycle_status": "active",
                    "selectable": True,
                    "catalog_version": catalog.catalog_version,
                    "etag": '"fixture-etag"',
                }
            ],
        }

    def test_central_cli_returns_valid_json_from_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_path = Path(directory) / "registry.json"
            fixture_path.write_text(
                json.dumps(self._fixture("immobilienkaufvertrag")),
                encoding="utf-8",
            )
            args = nac_cli.build_parser().parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "kg",
                    "business-case-type-get",
                    "immobilienkaufvertrag",
                    "--site-id",
                    "synthetic-site-01",
                    "--purpose",
                    "canonical_assignment",
                    "--registry-fixture",
                    str(fixture_path),
                    "--format",
                    "json",
                ]
            )
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = args.func(args)

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "VALID")
        self.assertEqual(payload["canonical_business_case_type_id"], "immobilienkaufvertrag")
        self.assertNotIn("token", json.dumps(payload).lower())

    def test_alias_assignment_is_invalid_and_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_path = Path(directory) / "registry.json"
            fixture_path.write_text(
                json.dumps(self._fixture("immobilienkaufvertrag")),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = notary_kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--format",
                        "json",
                        "business-case-type-get",
                        "grundstueckskaufvertrag",
                        "--site-id",
                        "synthetic-site-01",
                        "--purpose",
                        "canonical_assignment",
                        "--registry-fixture",
                        str(fixture_path),
                    ]
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["status"], "INVALID")
        self.assertEqual(payload["reason_code"], "alias_not_allowed")

    def test_legacy_alias_is_valid_and_audit_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_path = Path(directory) / "registry.json"
            fixture_path.write_text(
                json.dumps(self._fixture("immobilienkaufvertrag")),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = notary_kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--format",
                        "json",
                        "business-case-type-get",
                        "grundstueckskaufvertrag",
                        "--site-id",
                        "synthetic-site-01",
                        "--purpose",
                        "legacy_read",
                        "--registry-fixture",
                        str(fixture_path),
                    ]
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "VALID")
        self.assertTrue(payload["resolved_from_alias"])
        self.assertTrue(payload["audit_required"])
        self.assertFalse(payload["selectable"])

    def test_malformed_fixture_is_redacted_and_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_path = Path(directory) / "registry.json"
            fixture_path.write_text('{"secret": "must-not-be-echoed"}', encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = notary_kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "business-case-type-get",
                        "immobilienkaufvertrag",
                        "--site-id",
                        "synthetic-site-01",
                        "--purpose",
                        "canonical_assignment",
                        "--registry-fixture",
                        str(fixture_path),
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: business-case-type lookup failed", output.getvalue())
        self.assertNotIn("must-not-be-echoed", output.getvalue())

    def test_help_exposes_fixture_but_no_live_options(self) -> None:
        parser = nac_cli.build_parser()
        kg_parser = parser._subparsers._group_actions[0].choices["kg"]
        command = next(
            action.choices["business-case-type-get"]
            for action in kg_parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        help_text = command.format_help().lower()

        self.assertIn("--registry-fixture", help_text)
        self.assertNotIn("--token", help_text)
        self.assertNotIn("--graph", help_text)
        self.assertNotIn("--tenant", help_text)


    def test_catalog_error_is_redacted_and_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_path = Path(directory) / "registry.json"
            fixture_path.write_text(json.dumps(self._fixture("immobilienkaufvertrag")), encoding="utf-8")
            output = io.StringIO()
            with patch("notary_kg.cli.BusinessCaseTypeCatalog.from_repo", side_effect=RuntimeError("catalog-secret-detail")):
                with redirect_stdout(output):
                    exit_code = notary_kg_main([
                        "--repo-root", str(REPO_ROOT), "business-case-type-get",
                        "immobilienkaufvertrag", "--site-id", "synthetic-site-01",
                        "--purpose", "canonical_assignment", "--registry-fixture", str(fixture_path),
                    ])
        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "ERROR: business-case-type lookup failed")
        self.assertNotIn("catalog-secret-detail", output.getvalue())

    def test_runtime_error_is_redacted_and_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture_path = Path(directory) / "registry.json"
            fixture_path.write_text(json.dumps(self._fixture("immobilienkaufvertrag")), encoding="utf-8")
            output = io.StringIO()
            with patch("notary_kg.cli.business_case_type_get", side_effect=RuntimeError("runtime-secret-detail")):
                with redirect_stdout(output):
                    exit_code = notary_kg_main([
                        "--repo-root", str(REPO_ROOT), "business-case-type-get",
                        "immobilienkaufvertrag", "--site-id", "synthetic-site-01",
                        "--purpose", "canonical_assignment", "--registry-fixture", str(fixture_path),
                    ])
        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "ERROR: business-case-type lookup failed")
        self.assertNotIn("runtime-secret-detail", output.getvalue())

    def test_verification_validator_rejects_shape_and_traceability_drift(self) -> None:
        verification = json.loads((REPO_ROOT / "workflows/verification-contracts/business-case-type-runtime.verification.json").read_text(encoding="utf-8"))
        mutations = []
        missing_ac = copy.deepcopy(verification)
        missing_ac["acceptance_ids"].remove("AC-S3-06")
        mutations.append(missing_ac)
        malformed_applies = copy.deepcopy(verification)
        malformed_applies["applies_when"] = ["src/notary_kg/business_case_type_runtime.py"]
        mutations.append(malformed_applies)
        missing_cli_test = copy.deepcopy(verification)
        missing_cli_test["checks"] = [check for check in missing_cli_test["checks"] if "tests.test_business_case_type_cli" not in check]
        mutations.append(missing_cli_test)
        missing_strict_evidence = copy.deepcopy(verification)
        missing_strict_evidence["required_evidence"].remove("strict_gate_result")
        mutations.append(missing_strict_evidence)
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assertTrue(validate_verification_contract(mutation))

    def test_agent_context_validator_requires_runtime_cli_tests_and_docs(self) -> None:
        context = json.loads((REPO_ROOT / "agent-context/index.json").read_text(encoding="utf-8"))
        self.assertEqual([], validate_agent_context(context))
        mutated = copy.deepcopy(context)
        route = next(
            category
            for layer in mutated["layers"] if layer["id"] == "on_demand"
            for category in layer["categories"] if category["id"] == "business_case_type_runtime_s3"
        )
        route["paths"].remove("src/notary_kg/business_case_type_transport.py")
        self.assertTrue(validate_agent_context(mutated))

if __name__ == "__main__":
    unittest.main()
