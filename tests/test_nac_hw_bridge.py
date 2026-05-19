from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "nac_hw_bridge.py"


def load_bridge_module():
    spec = importlib.util.spec_from_file_location("nac_hw_bridge", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load_bridge_module()


class NaCHardwareBridgeTests(unittest.TestCase):
    def test_static_site_root_is_nac_owned(self) -> None:
        self.assertEqual(bridge.SITE_ROOT, REPO_ROOT / "web" / "local-operator")
        self.assertEqual(
            bridge.READINESS_SCRIPT,
            REPO_ROOT / "plugins" / "nac-cyberjack-rfid" / "scripts" / "check_readiness.py",
        )
        self.assertNotIn("funktion8-nac-website", str(bridge.SITE_ROOT))

    def test_operator_copy_keeps_bridge_as_cli_started_local_adapter(self) -> None:
        html = (bridge.SITE_ROOT / "index.html").read_text(encoding="utf-8")
        js = (bridge.SITE_ROOT / "assets" / "site.js").read_text(encoding="utf-8")

        self.assertIn("lokal per CLI gestartete Bridge", html)
        self.assertIn("python scripts\\nac.py operator --open", html)
        self.assertIn("freigegebene CLI-Pruefskripte", html)
        self.assertIn("python scripts\\\\nac.py operator --open", js)
        self.assertNotIn("alles laeuft ueber CLI", html.lower())

    def test_manual_review_is_logged_as_fail_without_raw_output(self) -> None:
        entry = bridge.build_test_log_entry(
            {
                "generated_at": "2026-05-19T11:45:00+00:00",
                "localhost_only": True,
                "overall_status": "manual_review",
                "startup_check": {"warnings": ["WARN: example"]},
                "readiness": {
                    "checks": [
                        {"status": "passed", "details": {"raw_secret": "must-not-appear"}},
                        {"status": "manual_review"},
                    ]
                },
                "readiness_command": {"stdout": "must-not-appear", "stderr": "must-not-appear"},
            }
        )

        self.assertEqual(entry["result"], "fail")
        self.assertEqual(entry["status"], "manual_review")
        self.assertEqual(entry["summary"]["check_counts"]["passed"], 1)
        self.assertEqual(entry["summary"]["check_counts"]["manual_review"], 1)
        self.assertNotIn("must-not-appear", str(entry))

    def test_ready_status_is_logged_as_success(self) -> None:
        self.assertEqual(bridge.result_from_status("ready"), "success")
        self.assertEqual(bridge.result_from_status("passed"), "success")
        self.assertEqual(bridge.result_from_status("manual_review"), "fail")


if __name__ == "__main__":
    unittest.main()
