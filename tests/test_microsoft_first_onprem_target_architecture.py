from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import validate_microsoft_first_onprem_target_architecture as validator


class MicrosoftFirstOnPremTargetArchitectureValidatorTests(unittest.TestCase):
    def _isolated_inputs(self) -> tuple[tempfile.TemporaryDirectory[str], dict[str, Path]]:
        temporary = tempfile.TemporaryDirectory(dir=validator.REPO_ROOT)
        root = Path(temporary.name)
        sources = {
            "CONTRACT": validator.CONTRACT,
            "DOC_DE": validator.DOC_DE,
            "DOC_EN": validator.DOC_EN,
            "SPEC_DE": validator.SPEC_DE,
            "SPEC_EN": validator.SPEC_EN,
            "PLAN_DE": validator.PLAN_DE,
            "PLAN_EN": validator.PLAN_EN,
        }
        paths: dict[str, Path] = {}
        for name, source in sources.items():
            target = root / source.relative_to(validator.REPO_ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            paths[name] = target
        return temporary, paths

    def test_current_contract_and_documents_pass(self) -> None:
        self.assertEqual([], validator.validate())

    def test_empty_english_architecture_document_is_rejected(self) -> None:
        temporary, paths = self._isolated_inputs()
        self.addCleanup(temporary.cleanup)
        paths["DOC_EN"].write_text("", encoding="utf-8")

        with mock.patch.multiple(validator, **paths):
            errors = validator.validate()

        self.assertTrue(
            any("must not be empty" in error and "docs/en/architecture" in error for error in errors),
            errors,
        )

    def test_mutated_storage_and_roadmap_values_are_rejected(self) -> None:
        temporary, paths = self._isolated_inputs()
        self.addCleanup(temporary.cleanup)
        contract = json.loads(paths["CONTRACT"].read_text(encoding="utf-8"))
        contract["storage_roles"] = {
            key: "wrong" for key in contract["storage_roles"]
        }
        contract["roadmap"] = {
            key: ["wrong"] for key in contract["roadmap"]
        }
        paths["CONTRACT"].write_text(
            json.dumps(contract, indent=2) + "\n",
            encoding="utf-8",
        )

        with mock.patch.multiple(validator, **paths):
            errors = validator.validate()

        self.assertIn(
            "storage_roles must match the conditional source-of-truth contract exactly",
            errors,
        )
        self.assertIn(
            "roadmap must match the accepted 90/180/365 values exactly",
            errors,
        )

    def test_incomplete_pdf_assessment_is_rejected(self) -> None:
        temporary, paths = self._isolated_inputs()
        self.addCleanup(temporary.cleanup)
        contract = json.loads(paths["CONTRACT"].read_text(encoding="utf-8"))
        del contract["pdf_assessment"]["spfx_1_22_heft_toolchain"]
        paths["CONTRACT"].write_text(
            json.dumps(contract, indent=2) + "\n",
            encoding="utf-8",
        )

        with mock.patch.multiple(validator, **paths):
            errors = validator.validate()

        self.assertIn(
            "pdf_assessment must classify every relevant recommendation exactly",
            errors,
        )

    def test_mutated_microsoft_first_edge_is_rejected(self) -> None:
        temporary, paths = self._isolated_inputs()
        self.addCleanup(temporary.cleanup)
        contract = json.loads(paths["CONTRACT"].read_text(encoding="utf-8"))
        contract["decisions"]["microsoft_first_edge"].append("azure_ai_runtime")
        paths["CONTRACT"].write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

        with mock.patch.multiple(validator, **paths):
            errors = validator.validate()

        self.assertIn(
            "decisions.microsoft_first_edge must match the Microsoft-first edge exactly",
            errors,
        )

    def test_mutated_onprem_core_is_rejected(self) -> None:
        temporary, paths = self._isolated_inputs()
        self.addCleanup(temporary.cleanup)
        contract = json.loads(paths["CONTRACT"].read_text(encoding="utf-8"))
        contract["decisions"]["onprem_core"].remove("worm_evidence_publisher")
        paths["CONTRACT"].write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

        with mock.patch.multiple(validator, **paths):
            errors = validator.validate()

        self.assertIn(
            "decisions.onprem_core must match the on-prem core exactly",
            errors,
        )

    def test_mutated_audit_boundary_is_rejected(self) -> None:
        temporary, paths = self._isolated_inputs()
        self.addCleanup(temporary.cleanup)
        original = json.loads(paths["CONTRACT"].read_text(encoding="utf-8"))
        mutations = {
            "required": lambda audit: audit["required"].remove("worm_retention"),
            "must_not": lambda audit: audit.update(
                {"sharepoint_version_history_is_sufficient": True}
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                contract = json.loads(json.dumps(original))
                mutate(contract["layer_boundaries"]["audit"])
                paths["CONTRACT"].write_text(
                    json.dumps(contract, indent=2) + "\n",
                    encoding="utf-8",
                )

                with mock.patch.multiple(validator, **paths):
                    errors = validator.validate()

                self.assertIn(
                    "layer_boundaries.audit must match the required evidence and SharePoint exclusion exactly",
                    errors,
                )

    def test_mutated_repository_ownership_is_rejected(self) -> None:
        temporary, paths = self._isolated_inputs()
        self.addCleanup(temporary.cleanup)
        contract = json.loads(paths["CONTRACT"].read_text(encoding="utf-8"))
        contract["repository_ownership"]["workflow_control_plane"] = "src/notary_kg/"
        paths["CONTRACT"].write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

        with mock.patch.multiple(validator, **paths):
            errors = validator.validate()

        self.assertIn(
            "repository_ownership must match the accepted component-to-path mapping exactly",
            errors,
        )

    def test_missing_matrix_marker_in_one_mirror_is_rejected(self) -> None:
        temporary, paths = self._isolated_inputs()
        self.addCleanup(temporary.cleanup)
        text = paths["DOC_EN"].read_text(encoding="utf-8")
        paths["DOC_EN"].write_text(
            text.replace("SPFx 1.22+", "SPFx current"),
            encoding="utf-8",
        )

        with mock.patch.multiple(validator, **paths):
            errors = validator.validate()

        self.assertTrue(
            any("docs/en/architecture" in error and "marker missing: SPFx 1.22+" in error for error in errors),
            errors,
        )


    def test_changed_pdf_verdict_in_one_mirror_is_rejected(self) -> None:
        temporary, paths = self._isolated_inputs()
        self.addCleanup(temporary.cleanup)
        text = paths["DOC_EN"].read_text(encoding="utf-8")
        paths["DOC_EN"].write_text(
            text.replace("| PostgreSQL | Adapt |", "| PostgreSQL | Adopt |"),
            encoding="utf-8",
        )

        with mock.patch.multiple(validator, **paths):
            errors = validator.validate()

        self.assertTrue(
            any("marker missing: | PostgreSQL | Adapt |" in error for error in errors),
            errors,
        )


if __name__ == "__main__":
    unittest.main()
