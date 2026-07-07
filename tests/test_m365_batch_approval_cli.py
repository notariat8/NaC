from __future__ import annotations

import json
import shlex
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class M365BatchApprovalCliTests(unittest.TestCase):
    def test_batch_approval_renders_merge_text_without_writes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--batch-pr",
                "#383,385",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["summary"]["executes_github_writes"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertEqual(payload["result"]["merge"]["prs"], ["#383", "#385"])
        self.assertIn("Freigabe: PRs #383, #385 mergen", payload["result"]["merge"]["approval_text"])

    def test_batch_approval_renders_live_smoke_text_without_writes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--batch-mode",
                "live-smoke",
                "--workspace-id",
                "notary_team_01",
                "--synthetic-case-id",
                "NAC-SMOKE-WRITE-READ-20260706T123000Z",
                "--correlation-id",
                "batch-corr-1",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["owner_gates"], ["m365_tenant_write_and_delete"])
        live_smoke = payload["result"]["live_smoke"]
        self.assertIn("M365 MCP Smoke Suite live", live_smoke["approval_text"])
        self.assertIn("Cleanup im gleichen Lauf", live_smoke["approval_text"])
        self.assertEqual(live_smoke["synthetic_case_id"], "NAC-SMOKE-WRITE-READ-20260706T123000Z")
        self.assertIn("mcp-smoke-suite", live_smoke["commands"][0])
        self.assertIn("--mcp-suite-cleanup", live_smoke["commands"][0])
        self.assertIn("--mcp-smoke-case-id NAC-SMOKE-WRITE-READ-20260706T123000Z", live_smoke["commands"][0])
        self.assertIn("mcp-smoke-leftover-cleanup", live_smoke["commands"][1])
        self.assertIn("--mcp-leftover-dry-run", live_smoke["commands"][1])
        self.assertNotIn("mcp-positive-write-read-smoke", " ".join(live_smoke["commands"]))
        self.assertEqual(
            [step["step"] for step in live_smoke["operator_sequence"]],
            ["mcp_smoke_suite", "mcp_smoke_leftover_cleanup_dry_run"],
        )

    def test_batch_approval_live_smoke_defaults_to_suite_generated_case_id(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--batch-mode",
                "live-smoke",
                "--workspace-id",
                "notary_team_01",
                "--correlation-id",
                "batch-corr-2",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        live_smoke = payload["result"]["live_smoke"]
        self.assertEqual(live_smoke["synthetic_case_id"], "generated_in_process_memory")
        self.assertIn("mcp-smoke-suite", live_smoke["commands"][0])
        self.assertNotIn("--mcp-smoke-case-id", live_smoke["commands"][0])

    def test_batch_approval_renders_runtime_release_gate_with_mvp_readiness_default(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--batch-mode",
                "release-gate",
                "--workspace-id",
                "notary_team_01",
                "--correlation-id",
                "release-gate-corr",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["summary"]["executes_github_writes"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertEqual(payload["summary"]["owner_gates"], ["m365_runtime_release_gate"])
        self.assertTrue(payload["summary"]["release_gate_write_audit_pack"])
        self.assertTrue(payload["summary"]["release_gate_write_readiness"])
        self.assertTrue(payload["summary"]["release_gate_readiness_require_audit_pack"])
        release_gate = payload["result"]["release_gate"]
        self.assertIn("M365 Runtime Release-Gate", release_gate["approval_text"])
        self.assertIn("Release-Gate-Audit-Pack", release_gate["approval_text"])
        self.assertIn("MVP-Readiness-Status", release_gate["approval_text"])
        self.assertIn("Matter-Access-Apply-Readiness", release_gate["approval_text"])
        self.assertEqual(
            release_gate["commands"],
            [
                "python3 scripts/nac.py m365 teams-sharepoint release-gate-run --owner-approved "
                "--mcp-smoke-workspace-id notary_team_01 --mcp-smoke-correlation-id release-gate-corr "
                "--release-gate-write-audit-pack --release-gate-write-readiness "
                "--release-gate-readiness-require-audit-pack --format json",
            ],
        )
        self.assertEqual(
            [step["step"] for step in release_gate["operator_sequence"]],
            ["release_gate_run"],
        )
        self.assertEqual(release_gate["operator_sequence"][0]["owner_gate"], "m365_runtime_release_gate")
        self.assertEqual(
            release_gate["operator_sequence"][0]["covers_steps"],
            [
                "mcp_inventory_smoke",
                "matter_access_delegation_smoke",
                "matter_access_apply_readiness",
                "runtime_certificate_expiry_monitor",
                "runtime_smoke",
                "runtime_metadata",
                "mcp_smoke_suite",
                "mcp_smoke_leftover_cleanup_dry_run",
                "release_gate_evidence_export",
                "release_gate_audit_pack",
                "release_gate_readiness",
            ],
        )

    def test_batch_approval_release_gate_can_render_audit_pack_runner_command(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--batch-mode",
                "release-gate",
                "--workspace-id",
                "notary_team_01",
                "--correlation-id",
                "release-gate-corr",
                "--release-gate-compare-left",
                "baseline-corr",
                "--release-gate-audit-pack-dir",
                "out/m365/teams-sharepoint/release-gate-audit-packs/baseline current",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["summary"]["executes_github_writes"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertTrue(payload["summary"]["release_gate_write_audit_pack"])

        release_gate = payload["result"]["release_gate"]
        self.assertTrue(release_gate["release_gate_write_audit_pack"])
        self.assertEqual(release_gate["release_gate_compare_left"], "baseline-corr")
        self.assertEqual(
            release_gate["release_gate_audit_pack_dir"],
            "out/m365/teams-sharepoint/release-gate-audit-packs/baseline current",
        )
        self.assertIn("Release-Gate-Audit-Pack", release_gate["approval_text"])
        self.assertIn("baseline-corr", release_gate["approval_text"])

        command = release_gate["commands"][0]
        command_args = shlex.split(command)
        self.assertIn("--release-gate-write-audit-pack", command_args)
        self.assertEqual(
            command_args[command_args.index("--release-gate-compare-left") + 1],
            "baseline-corr",
        )
        self.assertEqual(
            command_args[command_args.index("--release-gate-audit-pack-dir") + 1],
            "out/m365/teams-sharepoint/release-gate-audit-packs/baseline current",
        )
        self.assertIn("release_gate_audit_pack", release_gate["operator_sequence"][0]["covers_steps"])

    def test_batch_approval_release_gate_can_render_readiness_runner_command(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--batch-mode",
                "release-gate",
                "--workspace-id",
                "notary_team_01",
                "--correlation-id",
                "release-gate-corr",
                "--release-gate-write-audit-pack",
                "--release-gate-write-readiness",
                "--release-gate-readiness-require-audit-pack",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["summary"]["release_gate_write_audit_pack"])
        self.assertTrue(payload["summary"]["release_gate_write_readiness"])
        self.assertTrue(payload["summary"]["release_gate_readiness_require_audit_pack"])

        release_gate = payload["result"]["release_gate"]
        self.assertTrue(release_gate["release_gate_write_readiness"])
        self.assertTrue(release_gate["release_gate_readiness_require_audit_pack"])
        self.assertIn("MVP-Readiness-Status", release_gate["approval_text"])
        command_args = shlex.split(release_gate["commands"][0])
        self.assertIn("--release-gate-write-audit-pack", command_args)
        self.assertIn("--release-gate-write-readiness", command_args)
        self.assertIn("--release-gate-readiness-require-audit-pack", command_args)
        self.assertIn("release_gate_readiness", release_gate["operator_sequence"][0]["covers_steps"])

    def test_batch_approval_renders_runtime_certificate_rotation_lifecycle_without_writes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--batch-mode",
                "runtime-certificate-rotation",
                "--workspace-id",
                "notary_team_01",
                "--correlation-id",
                "cert-rotation-corr",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["summary"]["executes_github_writes"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["reads_certificate_files"])
        self.assertFalse(payload["summary"]["reads_private_key_files"])
        self.assertFalse(payload["summary"]["reads_secret_values"])
        self.assertTrue(payload["summary"]["release_gate_write_audit_pack"])
        self.assertTrue(payload["summary"]["release_gate_write_readiness"])
        self.assertTrue(payload["summary"]["release_gate_readiness_require_audit_pack"])
        self.assertEqual(payload["summary"]["owner_gates"], ["m365_runtime_certificate_rotation_lifecycle"])

        rotation = payload["result"]["runtime_certificate_rotation"]
        self.assertIn("M365 Runtime-Zertifikat rotieren", rotation["approval_text"])
        self.assertIn("MVP-Readiness-Status", rotation["approval_text"])
        self.assertIn("lokale M365-CLI-Session abmelden", rotation["approval_text"])
        self.assertIn("runtime-certificate-readiness", rotation["commands"][0])
        self.assertEqual(
            rotation["commands"][1],
            "python3 scripts/nac.py m365 teams-sharepoint release-gate-run --owner-approved "
            "--mcp-smoke-workspace-id notary_team_01 --mcp-smoke-correlation-id cert-rotation-corr "
            "--release-gate-write-audit-pack --release-gate-write-readiness "
            "--release-gate-readiness-require-audit-pack --format json",
        )
        self.assertEqual(
            [step["step"] for step in rotation["operator_sequence"]],
            [
                "runtime_certificate_readiness",
                "generate_local_runtime_certificate",
                "upload_public_certificate_to_entra_runtime_app",
                "update_local_runtime_credential_boundary",
                "release_gate_run",
                "refresh_non_secret_runtime_evidence_pr",
                "remove_stale_entra_runtime_certificate",
                "delete_local_old_certificate_archive",
                "logout_local_delegated_m365_cli_session",
            ],
        )
        self.assertFalse(rotation["operator_sequence"][0]["executes_graph_requests"])
        self.assertFalse(rotation["operator_sequence"][2]["private_key_uploaded"])
        self.assertFalse(rotation["operator_sequence"][5]["stores_secret_material"])
        self.assertIn("matter_access_apply_readiness", rotation["operator_sequence"][4]["covers_steps"])
        self.assertIn("release_gate_audit_pack", rotation["operator_sequence"][4]["covers_steps"])
        self.assertIn("release_gate_readiness", rotation["operator_sequence"][4]["covers_steps"])

    def test_batch_approval_requires_prs_for_merge_mode(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("--batch-pr", payload["errors"][0])

    def test_batch_approval_release_gate_baseline_uses_mvp_audit_pack_default(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--batch-mode",
                "release-gate",
                "--release-gate-compare-left",
                "baseline-corr",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        release_gate = payload["result"]["release_gate"]
        self.assertTrue(release_gate["release_gate_write_audit_pack"])
        self.assertEqual(release_gate["release_gate_compare_left"], "baseline-corr")
        self.assertIn("--release-gate-write-audit-pack", shlex.split(release_gate["commands"][0]))
        self.assertIn("baseline-corr", release_gate["approval_text"])


if __name__ == "__main__":
    unittest.main()
