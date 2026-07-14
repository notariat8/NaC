from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.azure_readiness import (  # noqa: E402
    build_azure_bff_readiness,
)
from nac_cli.cli import main as nac_main  # noqa: E402


class AzureBffReadinessTests(unittest.TestCase):
    def test_current_repository_is_ready_with_bound_compile_evidence(self) -> None:
        payload = build_azure_bff_readiness(REPO_ROOT)

        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["mode"], "offline")
        self.assertEqual(payload["summary"]["checks_total"], 7)
        self.assertEqual(
            [check["id"] for check in payload["checks"]],
            [
                "source",
                "function_host",
                "packaging",
                "bicep",
                "managed_identity",
                "cors",
                "readiness_files",
            ],
        )
        self.assertTrue(all(value is False for value in payload["boundaries"].values()))
        statuses = {check["id"]: check["status"] for check in payload["checks"]}
        self.assertEqual(statuses["packaging"], "READY")
        self.assertEqual(statuses["managed_identity"], "READY")
        self.assertEqual(statuses["bicep"], "READY")

        self.assertTrue(all(value is False for value in payload["redaction"].values()))
        self.assertTrue(all(step["live_action"] is False for step in payload["plan"]))

    def test_builder_does_not_use_environment_network_dns_or_subprocesses(self) -> None:
        secret = "must-not-appear-in-readiness-output"
        with (
            patch.dict(os.environ, {"M365_CLIENT_SECRET": secret}),
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS access")),
            patch.object(urllib.request, "urlopen", side_effect=AssertionError("HTTP access")),
            patch("subprocess.run", side_effect=AssertionError("subprocess access")),
        ):
            payload = build_azure_bff_readiness(REPO_ROOT)

        self.assertEqual(payload["status"], "READY")
        self.assertNotIn(secret, json.dumps(payload))

    def test_package_builder_is_byte_deterministic_and_manifest_valid(self) -> None:
        builder = _load_package_builder(REPO_ROOT)

        first = builder.build_package_bytes()
        second = builder.build_package_bytes()

        self.assertEqual(first, second)
        self.assertEqual(builder.validate_package(first), [])

    def test_unhashed_or_incomplete_dependency_lock_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_readiness_inputs(root)
            lock_path = root / "deploy/runtime/azure/nac-bff/requirements.txt"
            lock_path.write_text(
                lock_path.read_text(encoding="utf-8")
                + "\nunlocked-dependency==1.0\n",
                encoding="utf-8",
            )

            payload = build_azure_bff_readiness(root)

        statuses = {check["id"]: check["status"] for check in payload["checks"]}
        self.assertEqual(statuses["packaging"], "NOT_READY")

    def test_stale_bicep_compile_evidence_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_readiness_inputs(root)
            evidence_path = (
                root
                / "workflows/verification-contracts/"
                "m365-azure-bff-offline-readiness.verification.json"
            )
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            compile_evidence = evidence["bicep_compile_evidence"]
            compile_evidence["status"] = "PASSED"
            compile_evidence["template"]["compiled_sha256"] = "0" * 64
            compile_evidence["parameters"]["compiled_sha256"] = "1" * 64
            evidence_path.write_text(
                json.dumps(evidence, indent=2) + "\n",
                encoding="utf-8",
            )

            payload = build_azure_bff_readiness(root)

        statuses = {check["id"]: check["status"] for check in payload["checks"]}
        self.assertEqual(statuses["bicep"], "NOT_READY")

    def test_missing_bicep_file_produces_not_ready_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_readiness_inputs(root)
            (root / "deploy/runtime/azure/nac-bff/infra/main.bicep").unlink()

            payload = build_azure_bff_readiness(root)

        self.assertEqual(payload["status"], "NOT_READY")
        statuses = {check["id"]: check["status"] for check in payload["checks"]}
        self.assertEqual(statuses["bicep"], "NOT_READY")
        self.assertEqual(statuses["managed_identity"], "NOT_READY")
        self.assertEqual(statuses["cors"], "NOT_READY")

    def test_central_cli_emits_json_and_ready_exit_code(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            return_code = nac_main(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "bff-azure-readiness",
                    "--format",
                    "json",
                ]
            )

        payload = json.loads(output.getvalue())
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(
            payload["command"],
            "nac m365 teams-sharepoint bff-azure-readiness --format json",
        )


class AzureBffReadinessValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        validator_path = (
            REPO_ROOT / "scripts/validate_m365_azure_bff_offline_readiness.py"
        )
        spec = importlib.util.spec_from_file_location(
            "validate_m365_azure_bff_offline_readiness",
            validator_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load {validator_path}")
        cls.validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.validator)

    def test_current_repository_passes_contract_validator(self) -> None:
        self.assertEqual(self.validator.validate(REPO_ROOT), [])

    def test_tampered_live_baseline_fails_evidence_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for descriptor in self.validator.EVIDENCE_DEPENDENCIES.values():
                relative_path = descriptor["path"]
                target = root / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO_ROOT / relative_path, target)
            evidence_path = root / self.validator.EVIDENCE_DEPENDENCIES[
                "live_redacted_evidence"
            ]["path"]
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["status"] = "FAILED"
            evidence_path.write_text(
                json.dumps(evidence, indent=2) + "\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            document = {
                "evidence_dependencies": self.validator.EVIDENCE_DEPENDENCIES
            }
            self.validator._validate_evidence_dependencies(
                document,
                root,
                "test",
                errors,
            )

        self.assertTrue(any("digest mismatch" in error for error in errors))
        self.assertTrue(any("must be PASSED" in error for error in errors))

    def test_strict_quality_gate_runs_contract_validator(self) -> None:
        quality_gate_path = REPO_ROOT / "scripts/quality_gate.py"
        spec = importlib.util.spec_from_file_location("azure_readiness_quality_gate", quality_gate_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load {quality_gate_path}")
        quality_gate = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = quality_gate
        spec.loader.exec_module(quality_gate)

        checks = {
            check_id: command
            for check_id, _title, command in quality_gate.build_checks("strict")
        }
        self.assertEqual(
            checks["m365_azure_bff_offline_readiness"],
            [
                sys.executable,
                "scripts/validate_m365_azure_bff_offline_readiness.py",
            ],
        )


def _load_package_builder(repo_root: Path):
    builder_path = repo_root / "deploy/runtime/azure/nac-bff/build_package.py"
    spec = importlib.util.spec_from_file_location(
        "nac_bff_package_builder",
        builder_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {builder_path}")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder


def _copy_readiness_inputs(destination: Path) -> None:
    for package_name in ("nac_bff", "nac_m365_graph"):
        shutil.copytree(
            REPO_ROOT / "src" / package_name,
            destination / "src" / package_name,
        )
    module_target = destination / "src/nac_mvp_test_environment.py"
    module_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "src/nac_mvp_test_environment.py", module_target)

    paths = (
        "deploy/runtime/azure/nac-bff/build_package.py",
        "deploy/runtime/azure/nac-bff/function_app.py",
        "deploy/runtime/azure/nac-bff/host.json",
        "deploy/runtime/azure/nac-bff/requirements.txt",
        "deploy/runtime/azure/nac-bff/.funcignore",
        "deploy/runtime/azure/nac-bff/infra/main.bicep",
        "deploy/runtime/azure/nac-bff/infra/main.example.bicepparam",
        "deploy/runtime/azure/nac-bff/infra/compiled/main.json",
        "deploy/runtime/azure/nac-bff/infra/compiled/main.example.json",
        (
            "workflows/verification-contracts/"
            "m365-azure-bff-offline-readiness.verification.json"
        ),
    )
    for relative_path in paths:
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative_path, target)


if __name__ == "__main__":
    unittest.main()
