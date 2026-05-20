from __future__ import annotations

import base64
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
        self.assertIn('data-app-panel="matter-new"', html)
        self.assertIn('data-app-panel="matters"', html)
        self.assertIn('data-app-panel="imports"', html)
        self.assertIn('data-import-upload-form', html)
        self.assertIn('data-import-upload-files', html)
        self.assertIn('data-import-extract', html)
        self.assertIn("Metadaten extrahieren", html)
        self.assertIn('data-import-list', html)
        self.assertIn('data-import-count', html)
        self.assertIn('data-config-form', html)
        self.assertIn('data-config-field="nac_fork_git_url"', html)
        self.assertIn('data-config-field="data_git_url"', html)
        self.assertIn('data-config-field="data_repo_path"', html)
        self.assertIn('data-matter-form', html)
        self.assertIn('data-matter-list', html)
        self.assertIn('data-matter-search', html)
        self.assertIn("Akten und Eingang suchen", html)
        self.assertIn("Eingang prüfen", html)
        self.assertIn('data-matter-field="client_name"', html)
        self.assertIn('data-matter-field="participant_name"', html)
        self.assertIn('data-matter-field="status"', html)
        self.assertIn("https://github.com/funktion8/demo8notariat.git", html)
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
        self.assertIn("enhanceCaseRows", js)
        self.assertIn("loadMatters", js)
        self.assertIn("saveMatter", js)
        self.assertIn("/api/matters", js)
        self.assertIn("/api/matters/status", js)
        self.assertIn("loadImportProposals", js)
        self.assertIn("saveImportUpload", js)
        self.assertIn("extractImportUploadMetadata", js)
        self.assertIn("refreshVisibleData", js)
        self.assertIn("installPanelNavigation", js)
        self.assertIn("goBackPanel", js)
        self.assertIn("goCasesPanel", js)
        self.assertIn("Aktenverwaltung", js)
        self.assertIn("Kontrolle", js)
        self.assertIn("Kanzlei-Workflow", js)
        self.assertIn("Änderung vorschlagen", js)
        self.assertIn("Nächster Schritt", js)
        self.assertIn("Akten-Checkliste", js)
        self.assertIn("ownerRoleLabel", js)
        self.assertIn("← Zurück", js)
        self.assertIn("Übersicht", js)
        self.assertIn("searchableMatterText", js)
        self.assertIn("searchableImportText", js)
        self.assertIn("Passender Eingang", js)
        self.assertIn("Import-Vorschlag", js)
        self.assertIn("FileReader", js)
        self.assertIn("synthetic_demo_profile", js)
        self.assertIn("acceptImportProposal", js)
        self.assertIn("/api/import-proposals", js)
        self.assertIn("/api/import-proposals/accept", js)
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
        self.assertIn(".panel-navigation", css)
        self.assertIn(".matter-toolbar", css)
        self.assertIn(".matter-related", css)
        self.assertIn(".matter-checklist", css)
        self.assertIn(".case-action-group-daily", css)
        self.assertIn(".case-workflow-actions", css)
        self.assertNotIn(">Bridge<", html)
        self.assertNotIn("Betriebsmodell ansehen", html)
        self.assertNotIn("alles läuft über CLI", html.lower())

    def test_operator_matter_api_creates_lists_and_updates_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tenant_repo = Path(temp_dir) / "tenant"
            tenant_repo.mkdir()
            bridge.write_json(
                tenant_repo / ".nac-tenant.json",
                {
                    "schema_version": "nac.tenant/v0.2",
                    "name": "tenant",
                    "mode": "demo",
                },
            )
            config_path = Path(temp_dir) / "operator-config.json"
            bridge.save_operator_config(
                {
                    "values": {
                        "nac_fork_git_url": "https://github.com/funktion8/NaC.git",
                        "data_git_url": "https://github.com/funktion8/demo8notariat.git",
                        "data_repo_path": str(tenant_repo),
                    }
                },
                config_path=config_path,
            )

            created = bridge.create_operator_matter(
                {
                    "values": {
                        "usecase_slug": "unterschriftsbeglaubigung",
                        "usecase_title": "Unterschriftsbeglaubigung",
                        "title": "Unterschriftsbeglaubigung Demo",
                        "client_name": "Mara Muster",
                        "participant_name": "Timo Test",
                        "document_title": "Vollmacht Demo",
                        "status": "open",
                    }
                },
                config_path=config_path,
            )

            matter_id = created["matter"]["matter_id"]
            workflow_binding = created["matter"]["workflow_binding"]
            checklist_summary = created["matter"]["checklist_summary"]
            self.assertEqual(created["matter"]["usecase_slug"], "unterschriftsbeglaubigung")
            self.assertEqual(created["matter"]["status"], "open")
            self.assertEqual(workflow_binding["workflow_version"], "v1")
            self.assertEqual(workflow_binding["usecase_slug"], "unterschriftsbeglaubigung")
            self.assertEqual(workflow_binding["workflow_id"], "unterschriftsbeglaubigung:kanzlei-standard")
            self.assertEqual(workflow_binding["approval_state"], "approved_for_demo")
            self.assertTrue(workflow_binding["workflow_revision_hash"])
            self.assertIn("Akte bleibt auf dieser Workflow-Version", workflow_binding["binding_policy"])
            self.assertIn("bpmn", {artifact["type"] for artifact in workflow_binding["artifacts"]})
            self.assertIn("checklist", {artifact["type"] for artifact in workflow_binding["artifacts"]})
            self.assertGreater(checklist_summary["open_count"], 0)
            self.assertGreater(checklist_summary["total_count"], 0)
            self.assertEqual(checklist_summary["next_step"]["label"], "Unterzeichner Identität")
            self.assertEqual(checklist_summary["next_step"]["section"], "Offene Angaben")
            self.assertTrue((tenant_repo / "akten" / "2026" / matter_id / "akte.json").is_file())
            self.assertTrue((tenant_repo / "akten" / "2026" / matter_id / "checkliste.json").is_file())
            self.assertTrue((tenant_repo / "index" / "akten.json").is_file())
            persisted_matter = bridge.read_json(tenant_repo / "akten" / "2026" / matter_id / "akte.json")
            self.assertEqual(persisted_matter["workflow_binding"]["workflow_revision_hash"], workflow_binding["workflow_revision_hash"])
            persisted_checklist = bridge.read_json(tenant_repo / "akten" / "2026" / matter_id / "checkliste.json")
            self.assertEqual(persisted_checklist["workflow_version"], "v1")
            self.assertEqual(persisted_checklist["sections"][0]["id"], "required_information")

            listed = bridge.list_operator_matters(config_path=config_path)
            self.assertEqual(listed["counts"]["unterschriftsbeglaubigung"]["open"], 1)
            self.assertEqual(listed["matters"][0]["participants"], ["Mara Muster", "Timo Test"])
            self.assertEqual(listed["matters"][0]["workflow_binding"]["workflow_version"], "v1")
            self.assertEqual(listed["matters"][0]["checklist_summary"]["next_step"]["label"], "Unterzeichner Identität")

            updated = bridge.update_operator_matter_status(
                {"matter_id": matter_id, "status": "waiting", "status_reason": "wartet auf Unterlage"},
                config_path=config_path,
            )
            self.assertEqual(updated["matter"]["status"], "waiting")
            relisted = bridge.list_operator_matters(config_path=config_path)
            self.assertEqual(relisted["counts"]["unterschriftsbeglaubigung"]["waiting"], 1)
            self.assertEqual(relisted["counts"]["unterschriftsbeglaubigung"]["open"], 0)

    def test_operator_import_proposal_accepts_into_matter_with_staged_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tenant_repo = Path(temp_dir) / "tenant"
            tenant_repo.mkdir()
            bridge.write_json(
                tenant_repo / ".nac-tenant.json",
                {
                    "schema_version": "nac.tenant/v0.2",
                    "name": "tenant",
                    "mode": "demo",
                },
            )
            source_file = Path(temp_dir) / "personalausweis-vorderseite.jpg"
            source_file.write_bytes(b"synthetic-image")
            config_path = Path(temp_dir) / "operator-config.json"
            bridge.save_operator_config(
                {
                    "values": {
                        "nac_fork_git_url": "https://github.com/funktion8/NaC.git",
                        "data_git_url": "https://github.com/funktion8/demo8notariat.git",
                        "data_repo_path": str(tenant_repo),
                    }
                },
                config_path=config_path,
            )

            created = bridge.create_import_proposal(
                {
                    "values": {
                        "title": "Unterschriftsbeglaubigung Erika Mustermann",
                        "usecase_slug": "unterschriftsbeglaubigung",
                        "usecase_title": "Unterschriftsbeglaubigung",
                        "client_name": "Erika Mustermann",
                        "participant_name": "Erika Mustermann",
                        "document_title": "Personalausweis zur Identitätsprüfung",
                        "document_type": "id_document_scan",
                        "media_type": "image/jpeg",
                        "data_classification": "synthetic_identity_document",
                        "status": "open",
                        "status_reason": "Ausweisdaten aus synthetischem Testscan übernommen, manuelle Prüfung offen",
                        "synthetic_test_data": True,
                        "metadata": {"document_number": "LZ6311T47"},
                        "source_files": [
                            {
                                "label": "Vorderseite",
                                "path": str(source_file),
                                "filename": "personalausweis-vorderseite-erika-mustermann.jpg",
                                "media_type": "image/jpeg",
                            }
                        ],
                    }
                },
                config_path=config_path,
            )

            proposal_id = created["proposal"]["proposal_id"]
            listed = bridge.list_import_proposals(config_path=config_path)
            self.assertEqual(listed["counts"]["pending"], 1)
            self.assertTrue((tenant_repo / "eingang" / "dateien" / proposal_id / "personalausweis-vorderseite-erika-mustermann.jpg").is_file())

            accepted = bridge.accept_import_proposal({"proposal_id": proposal_id}, config_path=config_path)
            matter_id = accepted["matter"]["matter_id"]
            self.assertEqual(accepted["proposal"]["status"], "accepted")
            self.assertEqual(accepted["matter"]["participants"], ["Erika Mustermann", "Erika Mustermann"])
            self.assertEqual(accepted["matter"]["workflow_binding"]["workflow_version"], "v1")
            self.assertEqual(accepted["matter"]["checklist_summary"]["next_step"]["label"], "Unterzeichner Identität")
            matter = bridge.read_json(tenant_repo / "akten" / "2026" / matter_id / "akte.json")
            self.assertEqual(matter["workflow_binding"]["workflow_id"], "unterschriftsbeglaubigung:kanzlei-standard")
            document_id = matter["document_ids"][0]
            document = bridge.read_json(tenant_repo / "dokumente" / document_id / "metadata.json")
            self.assertEqual(document["document_type"], "id_document_scan")
            self.assertEqual(document["extracted_metadata"]["document_number"], "LZ6311T47")
            self.assertEqual(document["storage"]["originals"][0]["label"], "Vorderseite")
            self.assertTrue((tenant_repo / document["storage"]["originals"][0]["path"]).is_file())

    def test_operator_import_proposal_accepts_browser_upload_base64(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tenant_repo = Path(temp_dir) / "tenant"
            tenant_repo.mkdir()
            bridge.write_json(
                tenant_repo / ".nac-tenant.json",
                {
                    "schema_version": "nac.tenant/v0.2",
                    "name": "tenant",
                    "mode": "demo",
                },
            )
            config_path = Path(temp_dir) / "operator-config.json"
            bridge.save_operator_config(
                {
                    "values": {
                        "nac_fork_git_url": "https://github.com/funktion8/NaC.git",
                        "data_git_url": "https://github.com/funktion8/demo8notariat.git",
                        "data_repo_path": str(tenant_repo),
                    }
                },
                config_path=config_path,
            )

            created = bridge.create_import_proposal(
                {
                    "values": {
                        "title": "Unterschriftsbeglaubigung Erika Mustermann",
                        "usecase_slug": "unterschriftsbeglaubigung",
                        "usecase_title": "Unterschriftsbeglaubigung",
                        "client_name": "Erika Mustermann",
                        "participant_name": "Erika Mustermann",
                        "document_title": "Personalausweis zur Identitätsprüfung",
                        "document_type": "id_document_scan",
                        "media_type": "image/jpeg",
                        "data_classification": "synthetic_identity_document",
                        "status": "open",
                        "synthetic_test_data": True,
                        "metadata": {"document_number": "LZ6311T47"},
                        "source_files": [
                            {
                                "label": "Vorderseite",
                                "filename": "personalausweis-erika-mustermann-vorderseite.jpg",
                                "media_type": "image/jpeg",
                                "content_base64": base64.b64encode(b"synthetic-browser-upload").decode("ascii"),
                            }
                        ],
                    }
                },
                config_path=config_path,
            )

            proposal_id = created["proposal"]["proposal_id"]
            staged = tenant_repo / "eingang" / "dateien" / proposal_id / "personalausweis-erika-mustermann-vorderseite.jpg"
            self.assertEqual(staged.read_bytes(), b"synthetic-browser-upload")
            self.assertEqual(created["proposal"]["source_files"][0]["staged_path"], staged.relative_to(tenant_repo).as_posix())

            accepted = bridge.accept_import_proposal({"proposal_id": proposal_id}, config_path=config_path)
            matter = bridge.read_json(tenant_repo / "akten" / "2026" / accepted["matter"]["matter_id"] / "akte.json")
            document = bridge.read_json(tenant_repo / "dokumente" / matter["document_ids"][0] / "metadata.json")
            self.assertEqual(document["extracted_metadata"]["document_number"], "LZ6311T47")
            self.assertEqual((tenant_repo / document["storage"]["originals"][0]["path"]).read_bytes(), b"synthetic-browser-upload")

    def test_operator_checklist_state_is_available_for_all_usecases(self) -> None:
        for graph_path in sorted((REPO_ROOT / "usecases").glob("*/knowledge-graph.graph.json")):
            slug = graph_path.parent.name
            checklist = bridge.build_checklist_state(
                slug,
                slug,
                "2026-05-20T00:00:00Z",
                {
                    "workflow_id": f"{slug}:kanzlei-standard",
                    "workflow_version": "v1",
                    "workflow_revision_hash": "test",
                },
            )
            summary = bridge.summarize_checklist_state(checklist)
            with self.subTest(slug=slug):
                self.assertEqual(checklist["usecase_slug"], slug)
                self.assertEqual(checklist["workflow_version"], "v1")
                self.assertTrue(checklist["source"]["path"].endswith("knowledge-graph.graph.json"))
                self.assertGreater(summary["total_count"], 0)
                self.assertTrue(summary["next_step"]["label"])

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
        self.assertEqual(payload["values"]["data_git_url"], "https://github.com/funktion8/demo8notariat.git")
        self.assertTrue(payload["values"]["data_repo_path"].endswith("funktion8-demo8notariat"))

    def test_operator_bridge_disables_local_cache(self) -> None:
        self.assertIn(("Cache-Control", "no-store, max-age=0"), bridge.LOCAL_NO_STORE_HEADERS)
        self.assertIn(("Pragma", "no-cache"), bridge.LOCAL_NO_STORE_HEADERS)

    def test_operator_bridge_delegates_bpmn_routes(self) -> None:
        self.assertTrue(bridge.is_local_web_route("/bpmn/handelsregisteranmeldung/edit"))
        self.assertTrue(bridge.is_local_web_route("/api/bpmn/handelsregisteranmeldung/xml"))
        self.assertTrue(bridge.is_local_web_route("/api/bpmn-moddle"))
        self.assertFalse(bridge.is_local_web_route("/assets/site.js"))
        server = bridge.build_server("127.0.0.1", 0)
        self.assertGreater(server.server_port, 0)
        server.server_close()

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
