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

    def test_docs_keep_inventory_smoke_attached_to_release_gate_run(self) -> None:
        for relative_path in (
            "docs/de/cli.md",
            "docs/en/cli.md",
            "docs/de/operations/m365-mcp-batch-approval.md",
            "docs/en/operations/m365-mcp-batch-approval.md",
            "docs/de/architecture/teams-sharepoint-graph-data-plane.md",
            "docs/en/architecture/teams-sharepoint-graph-data-plane.md",
        ):
            content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

            self.assertIn("mcp-inventory-smoke", content)
            self.assertNotIn("führt ihn nicht automatisch aus", content)
            self.assertNotIn("does not execute it automatically", content)
            self.assertNotIn("mcp-inventory-smoke.not-attached", content)

    def test_cli_docs_include_release_readiness_status(self) -> None:
        for relative_path in ("docs/de/cli.md", "docs/en/cli.md"):
            content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

            self.assertIn("release-readiness --format json", content)
            self.assertIn("mvp_release_readiness", content)
            self.assertIn("release-gate-readiness-correlation-id", content)
            self.assertIn("release-gate-write-readiness", content)
            self.assertIn("release_gate_readiness=READY", content)
            self.assertIn("release-gate-post-run-report", content)
            self.assertIn("release-gate-post-run-report-index", content)
            self.assertIn("release-gate-post-run-report-index-artifact", content)
            self.assertIn("release-gate-post-run-report-index-json-output", content)
            self.assertIn("release-gate-write-post-run-report", content)
            self.assertIn("release-gate-github-comment-output", content)

    def test_docs_define_release_readiness_as_mvp_go_no_go_standard(self) -> None:
        documents = (
            (
                "docs/de/operations/m365-mcp-batch-approval.md",
                "## MVP-Go/No-Go-Abnahmekriterium",
                "`release-readiness` ist das verbindliche MVP-Go/No-Go-Abnahmekriterium",
                "Keine MVP-Freigabe erfolgt nur auf Basis",
            ),
            (
                "docs/en/operations/m365-mcp-batch-approval.md",
                "## MVP Go/No-Go Acceptance Criterion",
                "`release-readiness` is the binding MVP Go/No-Go acceptance criterion",
                "No MVP approval is based only on",
            ),
        )

        for relative_path, heading, rule_marker, rejection_marker in documents:
            content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

            self.assertIn(heading, content)
            self.assertIn(rule_marker, content)
            self.assertIn(rejection_marker, content)
            self.assertIn("--release-gate-write-audit-pack", content)
            self.assertIn("--release-gate-write-readiness", content)
            self.assertIn("--release-gate-readiness-require-audit-pack", content)
            self.assertIn("mvp_release_readiness=READY", content)
            self.assertIn("release_gate_readiness=READY", content)

    def test_batch_approval_docs_make_readiness_the_default_for_release_gate_modes(self) -> None:
        documents = (
            (
                "docs/de/operations/m365-mcp-batch-approval.md",
                "MVP-Go/No-Go-Standard standardmäßig",
                "Der eingebettete `release-gate-run` rendert denselben MVP-Go/No-Go-Standard",
            ),
            (
                "docs/en/operations/m365-mcp-batch-approval.md",
                "standard by default",
                "The embedded `release-gate-run` renders the same MVP Go/No-Go standard",
            ),
            (
                "docs/de/runbooks/m365-cli-admin-accelerator.md",
                "rendert standardmäßig den MVP-Go/No-Go-Lauf",
                "--release-gate-readiness-require-audit-pack",
            ),
            (
                "docs/en/runbooks/m365-cli-admin-accelerator.md",
                "renders the MVP Go/No-Go run by default",
                "--release-gate-readiness-require-audit-pack",
            ),
            (
                "docs/de/cli.md",
                "diesem Batch-Modus der Standard",
                "release_gate_readiness",
            ),
            (
                "docs/en/cli.md",
                "default in this batch mode",
                "release_gate_readiness",
            ),
        )

        for relative_path, release_gate_marker, readiness_marker in documents:
            content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")

            self.assertIn(release_gate_marker, content)
            self.assertIn(readiness_marker, content)

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
