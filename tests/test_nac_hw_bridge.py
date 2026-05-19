from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
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
        header_nav = html.split('<nav class="site-nav"', maxsplit=1)[1].split("</nav>", maxsplit=1)[0]
        footer_nav = html.split('<footer class="site-footer">', maxsplit=1)[1].split("</footer>", maxsplit=1)[0]
        self.assertLess(header_nav.index('data-area-tab="allgemeines-zivilrecht"'), header_nav.index('data-area-tab="erbrecht"'))
        self.assertLess(header_nav.index('data-area-tab="erbrecht"'), header_nav.index('data-area-tab="familienrecht-vorsorge"'))
        self.assertLess(header_nav.index('data-area-tab="familienrecht-vorsorge"'), header_nav.index('data-area-tab="gesellschaft-register"'))
        self.assertLess(header_nav.index('data-area-tab="gesellschaft-register"'), header_nav.index('data-area-tab="immobilienrecht"'))
        self.assertNotIn("Tests", header_nav)
        self.assertNotIn("Anbindungen", header_nav)
        self.assertNotIn("Handbuch", header_nav)
        self.assertIn("Tests", footer_nav)
        self.assertIn("Anbindungen", footer_nav)
        self.assertIn("Konfig", footer_nav)
        self.assertIn("Handbuch", footer_nav)
        self.assertIn('data-area-tab="immobilienrecht"', html)
        self.assertIn('data-area-tab="gesellschaft-register"', html)
        self.assertIn('data-area-tab="erbrecht"', html)
        self.assertIn('data-area-tab="familienrecht-vorsorge"', html)
        self.assertIn('data-area-tab="allgemeines-zivilrecht"', html)
        self.assertIn('data-app-panel="cases"', html)
        self.assertIn('data-app-panel="tests"', html)
        self.assertIn('data-app-panel="anbindungen"', html)
        self.assertIn('data-app-panel="handbuch"', html)
        self.assertIn('data-app-panel="konfig"', html)
        self.assertIn('data-config-form', html)
        self.assertIn('data-config-field="nac_fork_git_url"', html)
        self.assertIn('data-config-field="data_git_url"', html)
        self.assertIn('data-config-field="data_repo_path"', html)
        self.assertIn("https://github.com/ofunk/demo8notariat.git", html)
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
        self.assertIn("sortCaseRows", js)
        self.assertIn("loadOperatorConfig", js)
        self.assertIn("saveOperatorConfig", js)
        self.assertIn("/api/operator-config", js)
        self.assertNotIn("Steuer-Readiness", js)
        self.assertNotIn("Alle Usecases", html)
        self.assertNotIn("Katalog", html)
        self.assertNotIn("Bautraeger", html)
        self.assertNotIn("Steuer-aaS", html)
        self.assertNotIn("/kg/steuer-aas", html)
        self.assertNotIn(">Vorgänge</", html)
        self.assertNotIn("Problem prüfen", html)
        self.assertNotIn('class="workbench-actions"', html)
        case_group_block = css.split(".case-group {", maxsplit=1)[1].split("}", maxsplit=1)[0]
        site_footer_block = css.split(".site-footer {", maxsplit=1)[1].split("}", maxsplit=1)[0]
        self.assertNotIn("text-transform", case_group_block)
        self.assertIn("display: flex;", site_footer_block)
        self.assertNotIn("display: none;", site_footer_block)
        self.assertNotIn("min-height: calc(100vh - 72px)", css)
        self.assertIn("min-height: 0;", css)
        self.assertIn("overflow-x: hidden;", css)
        self.assertNotIn(">Bridge<", html)
        self.assertNotIn("Betriebsmodell ansehen", html)
        self.assertNotIn("alles läuft über CLI", html.lower())

    def test_operator_config_allows_arbitrary_git_and_data_repo_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "operator-config.json"
            payload = bridge.save_operator_config(
                {
                    "values": {
                        "nac_fork_git_url": "ssh://git.example.invalid/nac/fork.git",
                        "data_git_url": "git@example.invalid:any/demo-data.git",
                        "data_repo_path": str(Path(temp_dir) / "data-store"),
                    }
                },
                config_path=config_path,
            )

            self.assertTrue(config_path.is_file())
            self.assertEqual(payload["values"]["nac_fork_git_url"], "ssh://git.example.invalid/nac/fork.git")
            self.assertEqual(payload["values"]["data_git_url"], "git@example.invalid:any/demo-data.git")
            self.assertEqual(payload["status"]["data_repo_exists"], False)

            reloaded = bridge.load_operator_config(config_path)
            self.assertEqual(reloaded["data_git_url"], "git@example.invalid:any/demo-data.git")

    def test_operator_config_defaults_to_demo8notariat(self) -> None:
        payload = bridge.build_operator_config_payload(config_path=Path("missing-operator-config.json"))

        self.assertEqual(payload["schema_version"], "nac.operator-config/v1")
        self.assertEqual(payload["values"]["data_git_url"], "https://github.com/ofunk/demo8notariat.git")
        self.assertTrue(payload["values"]["data_repo_path"].endswith("demo8notariat"))

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
