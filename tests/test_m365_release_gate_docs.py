from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
