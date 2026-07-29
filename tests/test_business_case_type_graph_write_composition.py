from __future__ import annotations

import builtins
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_m365_graph.business_case_type_write_composition import (
    build_offline_business_case_type_write_composition,
)
from nac_m365_graph.business_case_type_write_composition_smoke import (
    S4C_COMPOSITION_READY_OFFLINE,
    _authorization,
    _mutations,
    _responses,
    _ScriptedHttpPort,
    _SyntheticTokenProvider,
    _target,
    build_business_case_type_write_composition_smoke,
)


class _ForbiddenEnvironment(dict):
    def __getitem__(self, key):
        raise AssertionError(f"environment read: {key}")

    def get(self, key, default=None):
        raise AssertionError(f"environment read: {key}")

    def __iter__(self):
        raise AssertionError("environment iteration")

    def items(self):
        raise AssertionError("environment iteration")


class BusinessCaseTypeWriteCompositionTests(unittest.TestCase):
    def test_offline_smoke_blocks_network_environment_and_file_reads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "state" / "evidence.sqlite"
            with (
                mock.patch.object(
                    socket,
                    "socket",
                    side_effect=AssertionError("socket access"),
                ),
                mock.patch.object(
                    socket,
                    "getaddrinfo",
                    side_effect=AssertionError("DNS access"),
                ),
                mock.patch.object(os, "environ", _ForbiddenEnvironment()),
                mock.patch.object(
                    os,
                    "getenv",
                    side_effect=AssertionError("environment access"),
                ),
                mock.patch.object(
                    builtins,
                    "open",
                    side_effect=AssertionError("file credential access"),
                ),
                mock.patch.object(
                    Path,
                    "read_text",
                    side_effect=AssertionError("text credential access"),
                ),
                mock.patch.object(
                    Path,
                    "read_bytes",
                    side_effect=AssertionError("binary credential access"),
                ),
            ):
                result = build_business_case_type_write_composition_smoke(
                    database_path=database_path,
                )

        self.assertEqual(result["status"], S4C_COMPOSITION_READY_OFFLINE)
        self.assertEqual(result["summary"]["socket_or_dns_calls"], 0)
        self.assertEqual(
            result["summary"]["external_credential_store_reads"],
            0,
        )

    def test_offline_guard_is_active_before_actual_cli_import(self) -> None:
        guard_root = (
            ROOT
            / "tests/fixtures/business-case-type-graph-write-composition"
        )
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "state" / "evidence.sqlite"
            runner = (
                "from nac_cli.cli import main\n"
                "raise SystemExit(main([\n"
                "    \"m365\", \"teams-sharepoint\",\n"
                "    \"business-case-type-write-composition-smoke\",\n"
                f"    \"--repo-root\", {str(ROOT)!r},\n"
                f"    \"--database-path\", {str(database_path)!r},\n"
                "    \"--format\", \"json\",\n"
                "    ]))\n"
            )
            completed = subprocess.run(
                [sys.executable, "-B", "-c", runner],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
                env={
                    "PYTHONPATH": f"{guard_root}:{SRC}",
                    "S4C_DATABASE_PATH": str(database_path),
                    "S4C_REPOSITORY_ROOT": str(ROOT),
                },
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], S4C_COMPOSITION_READY_OFFLINE)
        self.assertEqual(payload["summary"]["socket_or_dns_calls"], 0)
        self.assertEqual(
            payload["summary"]["external_credential_store_reads"],
            0,
        )

    def test_import_time_guard_blocks_bypass_primitives(self) -> None:
        guard_root = (
            ROOT
            / "tests/fixtures/business-case-type-graph-write-composition"
        )
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "state" / "evidence.sqlite"
            credential_path = Path(directory) / "credential.pem"
            credential_path.write_text("synthetic", encoding="utf-8")
            environment = {
                "PYTHONPATH": f"{guard_root}:{SRC}",
                "S4C_DATABASE_PATH": str(database_path),
                "S4C_REPOSITORY_ROOT": str(ROOT),
            }
            probes = (
                (
                    "path_open",
                    f"from pathlib import Path; Path({str(credential_path)!r}).open()",
                    "S4C_AUDIT_BLOCKED:external_file_access_blocked:",
                ),
                (
                    "io_open",
                    f"import io; io.open({str(credential_path)!r}, \"rb\")",
                    "S4C_AUDIT_BLOCKED:external_file_access_blocked:",
                ),
                (
                    "os_open",
                    f"import os; os.open({str(credential_path)!r}, os.O_RDONLY)",
                    "S4C_AUDIT_BLOCKED:external_file_access_blocked:",
                ),
                (
                    "dns",
                    "import socket; socket.gethostbyname(\"localhost\")",
                    "S4C_AUDIT_BLOCKED:network_or_dns_access_blocked",
                ),
                (
                    "environment",
                    "import os; os.getenv(\"S4C_DATABASE_PATH\")",
                    "S4C_AUDIT_BLOCKED:environment_access_blocked",
                ),
                (
                    "environment_copy",
                    "import os; os.environ.copy()",
                    "S4C_AUDIT_BLOCKED:environment_access_blocked",
                ),
                (
                    "environment_len",
                    "import os; len(os.environ)",
                    "S4C_AUDIT_BLOCKED:environment_access_blocked",
                ),
                (
                    "environment_equality",
                    "import os; os.environ == {}",
                    "S4C_AUDIT_BLOCKED:environment_access_blocked",
                ),
                (
                    "environment_repr",
                    "import os; repr(os.environ)",
                    "S4C_AUDIT_BLOCKED:environment_access_blocked",
                ),
                (
                    "environment_str",
                    "import os; str(os.environ)",
                    "S4C_AUDIT_BLOCKED:environment_access_blocked",
                ),
                (
                    "binary_environment",
                    "import os; os.environb.get(b\"S4C_DATABASE_PATH\")",
                    "S4C_AUDIT_BLOCKED:environment_access_blocked",
                ),
                (
                    "binary_environment_copy",
                    "import os; os.environb.copy()",
                    "S4C_AUDIT_BLOCKED:environment_access_blocked",
                ),
                (
                    "binary_environment_function",
                    "import os; os.getenvb(b\"S4C_DATABASE_PATH\")",
                    "S4C_AUDIT_BLOCKED:environment_access_blocked",
                ),
            )
            for name, probe, expected_marker in probes:
                with self.subTest(name=name):
                    completed = subprocess.run(
                        [sys.executable, "-B", "-c", probe],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        env=environment,
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn(expected_marker, completed.stderr)


    def test_all_five_operations_use_the_offline_composition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "state" / "evidence.sqlite"

            result = build_business_case_type_write_composition_smoke(
                database_path=database_path,
            )

            self.assertEqual(result["status"], S4C_COMPOSITION_READY_OFFLINE)
            self.assertEqual(
                [item["operation"] for item in result["operations"]],
                [
                    "case_create",
                    "case_status_update",
                    "task_create",
                    "task_update",
                    "business_case_type_backfill",
                ],
            )
            self.assertEqual(
                [item["status"] for item in result["operations"]],
                ["APPLIED"] * 5,
            )
            self.assertEqual(result["summary"]["synthetic_http_port_calls"], 15)
            self.assertEqual(
                result["summary"]["synthetic_token_provider_calls"],
                15,
            )
            for counter in (
                "socket_or_dns_calls",
                "external_credential_store_reads",
                "live_graph_calls",
                "tenant_writes",
                "automatic_retries",
            ):
                self.assertEqual(result["summary"][counter], 0)
            self.assertEqual(database_path.stat().st_mode & 0o777, 0o600)

    def test_plan_revalidation_block_does_not_call_token_provider(self) -> None:
        target = _target()
        mutation = _mutations()[0]
        token_provider = _SyntheticTokenProvider()
        http_port = _ScriptedHttpPort(_responses([mutation]))
        with tempfile.TemporaryDirectory() as directory:
            composition = build_offline_business_case_type_write_composition(
                target=target,
                database_path=Path(directory) / "state" / "evidence.sqlite",
                token_provider=token_provider,
                http_port=http_port,
            )
            plan = composition.build_plan(mutation, _authorization(target))
            forged = replace(
                plan,
                write_url="https://graph.microsoft.com/v1.0/foreign",
            )

            result = composition.edge.execute(forged)

        self.assertEqual(result.status, "BLOCKED_PLAN")
        self.assertEqual(result.transport_calls, 0)
        self.assertEqual(token_provider.calls, 0)
        self.assertEqual(http_port.calls, 0)

    def test_persistent_closure_blocks_replay_after_restart(self) -> None:
        target = _target()
        mutation = _mutations()[0]
        database_root = Path(tempfile.mkdtemp())
        self.addCleanup(
            lambda: __import__("shutil").rmtree(database_root, ignore_errors=True)
        )
        database_path = database_root / "state" / "evidence.sqlite"
        first_token = _SyntheticTokenProvider()
        first_http = _ScriptedHttpPort(_responses([mutation]))
        first = build_offline_business_case_type_write_composition(
            target=target,
            database_path=database_path,
            token_provider=first_token,
            http_port=first_http,
        )
        authorization = _authorization(target)
        first_result = first.execute(mutation, authorization)
        self.assertEqual(first_result.status, "APPLIED")

        second_token = _SyntheticTokenProvider()
        second_http = _ScriptedHttpPort([])
        restarted = build_offline_business_case_type_write_composition(
            target=target,
            database_path=database_path,
            token_provider=second_token,
            http_port=second_http,
        )
        second_result = restarted.execute(mutation, authorization)

        self.assertEqual(second_result.status, "BLOCKED_COMPLETED_MUTATION")
        self.assertEqual(second_result.transport_calls, 0)
        self.assertEqual(second_token.calls, 0)
        self.assertEqual(second_http.calls, 0)


if __name__ == "__main__":
    unittest.main()
