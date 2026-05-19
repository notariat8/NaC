from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
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

    def test_bridge_help_works_when_src_is_already_on_pythonpath(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT / "src")

        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--port", completed.stdout)

    def test_operator_copy_is_usecase_first_workbench(self) -> None:
        html = (bridge.SITE_ROOT / "index.html").read_text(encoding="utf-8")
        js = (bridge.SITE_ROOT / "assets" / "site.js").read_text(encoding="utf-8")
        css = (bridge.SITE_ROOT / "assets" / "site.css").read_text(encoding="utf-8")

        self.assertIn('src="assets/n8.svg"', html)
        self.assertIn('href="assets/site.css?v=', html)
        self.assertIn('src="assets/site.js?v=', html)
        self.assertTrue((bridge.SITE_ROOT / "assets" / "n8.svg").is_file())
        self.assertIn("Immobilienrecht", html)
        self.assertIn('data-area-tab="immobilienrecht"', html)
        self.assertIn('data-area-tab="gesellschaft-register"', html)
        self.assertIn('data-area-tab="erbrecht"', html)
        self.assertIn('data-area-tab="familienrecht-vorsorge"', html)
        self.assertIn('data-area-tab="allgemeines-zivilrecht"', html)
        self.assertIn('data-app-panel="cases"', html)
        self.assertIn('data-app-panel="tests"', html)
        self.assertIn('data-app-panel="anbindungen"', html)
        self.assertIn('data-app-panel="handbuch"', html)
        self.assertNotIn('href="#bpmn-modelle"', html)
        self.assertNotIn('href="#tests"', html)
        self.assertNotIn('href="#anbindungen"', html)
        self.assertNotIn('href="#handbuch"', html)
        self.assertEqual(html.count('class="case-row"'), 22)
        self.assertIn('data-area="immobilienrecht"', html)
        self.assertIn('data-area="gesellschaft-register"', html)
        self.assertIn('data-area="erbrecht"', html)
        self.assertIn('data-area="familienrecht-vorsorge"', html)
        self.assertIn('data-area="allgemeines-zivilrecht"', html)
        self.assertIn("/kg/immobilienkaufvertrag", html)
        self.assertIn("/bpmn/handelsregisteranmeldung/edit", html)
        self.assertIn("/kg/bautraegervertrag", html)
        self.assertIn("/bpmn/bautraegervertrag", html)
        self.assertIn("Bauträgervertrag", html)
        self.assertIn("Vorgang suchen", html)
        self.assertIn("/bpmn/vorsorgevollmacht-patientenverfuegung/edit", html)
        self.assertIn("HW-Test starten", html)
        self.assertIn("XNP prüfen", html)
        self.assertIn("Repository öffnen", html)
        self.assertIn("python scripts\\nac.py operator --open", html)
        self.assertIn("python scripts\\\\nac.py operator --open", js)
        self.assertIn("[data-case-search]", js)
        self.assertIn("[data-area-tab]", js)
        self.assertIn("filterCases", js)
        self.assertIn("showPanel", js)
        self.assertNotIn("Steuer-Readiness", js)
        self.assertNotIn("Alle Usecases", html)
        self.assertNotIn("Katalog", html)
        self.assertNotIn("Bautraeger", html)
        self.assertNotIn("Steuer-aaS", html)
        self.assertNotIn("/kg/steuer-aas", html)
        self.assertNotIn(">Vorgänge</", html)
        case_group_block = css.split(".case-group {", maxsplit=1)[1].split("}", maxsplit=1)[0]
        self.assertNotIn("text-transform", case_group_block)
        self.assertNotIn("min-height: calc(100vh - 72px)", css)
        self.assertIn("min-height: 0;", css)
        self.assertIn("overflow-x: hidden;", css)
        self.assertNotIn(">Bridge<", html)
        self.assertNotIn("Betriebsmodell ansehen", html)
        self.assertNotIn("alles läuft über CLI", html.lower())

    def test_operator_bridge_disables_local_cache(self) -> None:
        self.assertIn(("Cache-Control", "no-store, max-age=0"), bridge.LOCAL_NO_STORE_HEADERS)
        self.assertIn(("Pragma", "no-cache"), bridge.LOCAL_NO_STORE_HEADERS)

    def test_operator_bridge_delegates_bpmn_routes(self) -> None:
        self.assertTrue(bridge.is_local_web_route("/bpmn/handelsregisteranmeldung/edit"))
        self.assertTrue(bridge.is_local_web_route("/api/bpmn/handelsregisteranmeldung/xml"))
        self.assertTrue(bridge.is_local_web_route("/api/bpmn-moddle"))
        self.assertFalse(bridge.is_local_web_route("/assets/site.js"))

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
