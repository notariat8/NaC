from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_teams_sharepoint_graph_data_plane",
    SCRIPTS_ROOT / "validate_teams_sharepoint_graph_data_plane.py",
)
if VALIDATOR_SPEC is None or VALIDATOR_SPEC.loader is None:
    raise ImportError("Could not load validate_teams_sharepoint_graph_data_plane.py")
data_plane_validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(data_plane_validator)


class M365ReleaseGateDocsTests(unittest.TestCase):
    def test_accelerator_runbooks_use_nac_cli_for_runtime_smokes(self) -> None:
        for relative_path in (
            "docs/de/runbooks/m365-cli-admin-accelerator.md",
            "docs/en/runbooks/m365-cli-admin-accelerator.md",
        ):
            content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

            self.assertIn("scripts/nac.py m365 teams-sharepoint runtime-smoke", content)
            self.assertIn("scripts/nac.py m365 teams-sharepoint runtime-metadata", content)
            self.assertNotIn("scripts/provision_teams_sharepoint_graph.py runtime-smoke", content)
            self.assertNotIn("scripts/provision_teams_sharepoint_graph.py runtime-metadata", content)
            self.assertNotIn("scripts/provision_teams_sharepoint_graph.py privileged-apply", content)

    def test_first_cli_commands_lead_with_release_gate_run(self) -> None:
        documents = (
            ("docs/de/cli.md", "## Erste Befehle", "## Technische Bedienflächen"),
            ("docs/en/cli.md", "## First Commands", "## Technical Operating Areas"),
        )

        for relative_path, start_marker, end_marker in documents:
            content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            first_commands = content.split(start_marker, maxsplit=1)[1].split(end_marker, maxsplit=1)[0]

            self.assertIn("release-gate-run --owner-approved", first_commands)
            self.assertNotIn("runtime-smoke --owner-approved", first_commands)
            self.assertNotIn("runtime-metadata --owner-approved", first_commands)

    def test_architecture_docs_distinguish_release_gate_from_mcp_suite(self) -> None:
        for relative_path in (
            "docs/de/architecture/teams-sharepoint-graph-data-plane.md",
            "docs/en/architecture/teams-sharepoint-graph-data-plane.md",
        ):
            content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

            self.assertIn("release-gate-run", content)
            self.assertIn("mcp-smoke-suite --owner-approved --mcp-suite-cleanup", content)
            self.assertIn("scripts/nac.py m365 teams-sharepoint privileged-plan", content)
            self.assertNotIn("python3 scripts/provision_teams_sharepoint_graph.py", content)

    def test_batch_approval_docs_make_release_gate_run_the_standard(self) -> None:
        documents = (
            (
                "docs/de/operations/m365-mcp-batch-approval.md",
                "`release-gate-run` ist der Standard-Betriebsnachweis",
                "Die Smoke Suite ist der Standard-Betriebsnachweis",
            ),
            (
                "docs/en/operations/m365-mcp-batch-approval.md",
                "`release-gate-run` is the standard runtime evidence",
                "The smoke suite is the standard runtime evidence",
            ),
        )

        for relative_path, expected_marker, rejected_marker in documents:
            content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

            self.assertIn(expected_marker, content)
            self.assertNotIn(rejected_marker, content)

    def test_data_plane_validator_accepts_product_edge_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            arch_de = temp_root / "arch-de.md"
            arch_en = temp_root / "arch-en.md"
            batch_de = temp_root / "batch-de.md"
            batch_en = temp_root / "batch-en.md"
            arch_de.write_text("scripts/nac.py m365 teams-sharepoint privileged-plan", encoding="utf-8")
            arch_en.write_text("scripts/nac.py m365 teams-sharepoint privileged-plan", encoding="utf-8")
            batch_de.write_text(
                "`release-gate-run` ist der Standard-Betriebsnachweis\nDiagnose-/Komponentenpfad",
                encoding="utf-8",
            )
            batch_en.write_text(
                "`release-gate-run` is the standard runtime evidence\ndiagnostic/component path",
                encoding="utf-8",
            )

            errors = _run_product_edge_validator(arch_de, arch_en, batch_de, batch_en)

        self.assertEqual(errors, [])

    def test_data_plane_validator_rejects_old_product_edge_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            arch_de = temp_root / "arch-de.md"
            arch_en = temp_root / "arch-en.md"
            batch_de = temp_root / "batch-de.md"
            batch_en = temp_root / "batch-en.md"
            arch_de.write_text("python3 scripts/provision_teams_sharepoint_graph.py plan", encoding="utf-8")
            arch_en.write_text("python3 scripts/provision_teams_sharepoint_graph.py plan", encoding="utf-8")
            batch_de.write_text("Die Smoke Suite ist der Standard-Betriebsnachweis", encoding="utf-8")
            batch_en.write_text("The smoke suite is the standard runtime evidence", encoding="utf-8")

            errors = _run_product_edge_validator(arch_de, arch_en, batch_de, batch_en)

        error_text = "\n".join(errors)
        self.assertIn("missing marker scripts/nac.py m365 teams-sharepoint privileged-plan", error_text)
        self.assertIn("contains prohibited product-edge marker", error_text)
        self.assertIn("Die Smoke Suite ist der Standard-Betriebsnachweis", error_text)
        self.assertIn("The smoke suite is the standard runtime evidence", error_text)


def _run_product_edge_validator(
    arch_de: Path,
    arch_en: Path,
    batch_de: Path,
    batch_en: Path,
) -> list[str]:
    original_paths = (
        data_plane_validator.DOC_DE,
        data_plane_validator.DOC_EN,
        data_plane_validator.BATCH_APPROVAL_DE,
        data_plane_validator.BATCH_APPROVAL_EN,
    )
    try:
        data_plane_validator.DOC_DE = arch_de
        data_plane_validator.DOC_EN = arch_en
        data_plane_validator.BATCH_APPROVAL_DE = batch_de
        data_plane_validator.BATCH_APPROVAL_EN = batch_en
        errors: list[str] = []
        data_plane_validator._validate_product_edge_docs(errors)
        return errors
    finally:
        (
            data_plane_validator.DOC_DE,
            data_plane_validator.DOC_EN,
            data_plane_validator.BATCH_APPROVAL_DE,
            data_plane_validator.BATCH_APPROVAL_EN,
        ) = original_paths


if __name__ == "__main__":
    unittest.main()
