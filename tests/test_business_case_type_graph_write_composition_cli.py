from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_cli.cli import main


class BusinessCaseTypeWriteCompositionCliTests(unittest.TestCase):
    def test_help_does_not_require_environment_access(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(
                [
                    "m365",
                    "teams-sharepoint",
                    "business-case-type-write-composition-smoke",
                    "--help",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("--database-path", output.getvalue())

    def test_json_smoke_reports_offline_ready_without_owner_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "state" / "evidence.sqlite"
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "m365",
                        "teams-sharepoint",
                        "business-case-type-write-composition-smoke",
                        "--database-path",
                        str(database_path),
                        "--format",
                        "json",
                    ]
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "S4C_COMPOSITION_READY_OFFLINE")
        self.assertEqual(payload["summary"]["live_graph_calls"], 0)
        self.assertEqual(payload["summary"]["tenant_writes"], 0)
        self.assertEqual(payload["summary"]["external_credential_store_reads"], 0)
        self.assertNotIn("owner", payload)
        serialized = json.dumps(payload).lower()
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("private_key", serialized)
        self.assertNotIn("certificate", serialized)

    def test_non_absolute_repo_root_is_rejected_before_expanduser(self) -> None:
        for repo_root in ("~", "relative"):
            with self.subTest(repo_root=repo_root):
                with self.assertRaisesRegex(
                    ValueError,
                    "must be absolute and must not contain ~",
                ):
                    main(
                        [
                            "m365",
                            "teams-sharepoint",
                            "business-case-type-write-composition-smoke",
                            "--repo-root",
                            repo_root,
                            "--database-path",
                            "/tmp/s4c-test.sqlite",
                        ]
                    )

    def test_database_path_must_be_absolute(self) -> None:
        with self.assertRaisesRegex(ValueError, "absolute"):
            main(
                [
                    "m365",
                    "teams-sharepoint",
                    "business-case-type-write-composition-smoke",
                    "--database-path",
                    "relative.sqlite",
                    "--format",
                    "json",
                ]
            )


if __name__ == "__main__":
    unittest.main()
