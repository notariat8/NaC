from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli.cli import main  # noqa: E402


def run_cli(*argv: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        rc = main(["--repo-root", str(REPO_ROOT), *argv])
    return rc, buffer.getvalue()


def run_cli_with_exit(*argv: str) -> tuple[int, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            rc = main(["--repo-root", str(REPO_ROOT), *argv])
        except SystemExit as exc:
            rc = int(exc.code or 0)
    return rc, stdout.getvalue() + stderr.getvalue()


class NaCCliTests(unittest.TestCase):
    def test_status_shows_single_entrypoint(self) -> None:
        rc, output = run_cli("status")

        self.assertEqual(rc, 0)
        self.assertIn("NaC Status", output)
        self.assertIn("nac doctor --profile strict", output)
        self.assertIn("nac web", output)
        self.assertIn("nac operator --open", output)
        self.assertIn("nac legal-graph status", output)
        self.assertIn("nac legal-graph sources", output)

    def test_config_list_includes_language_policy(self) -> None:
        rc, output = run_cli("config", "list")

        self.assertEqual(rc, 0)
        self.assertIn("language-policy", output)
        self.assertIn("policies/language-policy.yaml", output)

    def test_bpmn_list_includes_immobilienkaufvertrag(self) -> None:
        rc, output = run_cli("bpmn", "list")

        self.assertEqual(rc, 0)
        self.assertIn("immobilienkaufvertrag", output)

    def test_bpmn_show_can_emit_svg(self) -> None:
        rc, output = run_cli("bpmn", "show", "immobilienkaufvertrag", "--format", "svg")

        self.assertEqual(rc, 0)
        self.assertIn("<svg", output)
        self.assertIn("Auftrag und Beteiligte", output)
        self.assertIn("xnp_local", output)

    def test_contracts_validate_secure_document_links(self) -> None:
        rc, output = run_cli("contracts", "validate")

        self.assertEqual(rc, 0, output)
        self.assertIn("GNotKG Cost Review", output)
        self.assertIn("Secure Document Link", output)
        self.assertIn("Legal Research Connectors", output)
        self.assertIn("Legal Graph Contracts", output)
        self.assertIn("Spec Traceability", output)
        self.assertIn("STATUS: PASSED", output)

    def test_kg_status_is_available_through_nac_cli(self) -> None:
        rc, output = run_cli("kg", "status")

        self.assertEqual(rc, 0)
        self.assertIn("NaC KG development status", output)

    def test_kg_cost_view_is_available_through_nac_cli(self) -> None:
        rc, output = run_cli("kg", "--format", "json", "cost-view", "immobilienkaufvertrag")

        self.assertEqual(rc, 0)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.gnotkg-cost-review/v0.1")
        self.assertEqual(payload["usecase_slug"], "immobilienkaufvertrag")
        self.assertEqual(payload["rendering"]["preferred_renderer"], "xyflow")

    def test_kg_workflow_contract_is_available_through_nac_cli(self) -> None:
        rc, output = run_cli("kg", "--format", "json", "workflow-contract", "immobilienkaufvertrag")

        self.assertEqual(rc, 0)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.workflow-contract-draft/v0.1")
        self.assertEqual(payload["source"]["usecase_slug"], "immobilienkaufvertrag")
        self.assertFalse(payload["guardrails"]["real_mandate_data_in_git"])
        self.assertFalse(_contains_key(payload, "value"))

    def test_kg_pilot_checklist_is_available_through_nac_cli(self) -> None:
        rc, output = run_cli("kg", "--format", "json", "pilot-checklist", "online-gmbh-gruendung")

        self.assertEqual(rc, 0)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.pilot-intake-checklist/v0.1")
        self.assertEqual(payload["pilot_usecase"]["slug"], "online-gmbh-gruendung")
        self.assertEqual(payload["summary"]["next_step"]["id"], "company.name")
        self.assertFalse(payload["guardrails"]["productive_register_or_xnp_action"])
        self.assertFalse(_contains_key(payload, "value"))

    def test_gnotkg_quote_is_available_through_nac_cli(self) -> None:
        rc, output = run_cli(
            "gnotkg",
            "quote",
            "--business-value",
            "500000",
            "--table",
            "A",
            "--fee-rate",
            "1.0",
            "--kv-number",
            "21100",
            "--format",
            "json",
        )

        self.assertEqual(rc, 0)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.gnotkg-cost-quote/v0.1")
        self.assertEqual(payload["base_fee"], "4138.00")
        self.assertEqual(payload["fee_amount"], "4138.00")

    def test_ai_sbom_export_mapping_cli_returns_json(self) -> None:
        rc, output = run_cli("ai-sbom", "export-mapping", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        profile_ids = {item["id"] for item in payload["target_profiles"]}
        self.assertEqual(payload["schema_version"], "nac.ai-sbom-export-mapping-status/v0.1")
        self.assertEqual(payload["status"], "mapping_selected_no_release_export")
        self.assertEqual(profile_ids, {"cyclonedx-json", "spdx-json"})
        self.assertFalse(payload["release_export_enabled"])
        self.assertFalse(payload["external_tool_execution_enabled"])
        self.assertFalse(payload["mandate_data_allowed"])
        self.assertFalse(payload["secret_material_allowed"])
        self.assertTrue(payload["owner_apply_required_before_release_binding"])

    def test_legal_graph_status_cli_returns_json(self) -> None:
        rc, output = run_cli("legal-graph", "status", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        domains = {item["id"] for item in payload["domain_status"]}
        self.assertEqual(payload["schema_version"], "nac.legal-graph-status/v0.1")
        self.assertGreaterEqual(domains, {"erbrecht", "familienrecht", "gesellschaftsrecht"})

    def test_legal_graph_sources_cli_returns_primary_source_status(self) -> None:
        rc, output = run_cli("legal-graph", "sources", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        sources = {item["domain"]: item for item in payload["source_status"]}
        self.assertEqual(payload["schema_version"], "nac.legal-graph-source-status/v0.1")
        self.assertEqual(payload["sources"], 3)
        self.assertEqual(set(sources), {"erbrecht", "familienrecht", "gesellschaftsrecht"})
        for source in sources.values():
            self.assertEqual(source["retrieval_mode"], "metadata_only_fixture")
            self.assertFalse(source["commentary_access_allowed"])

    def test_legal_graph_source_inventory_cli_returns_gate_status(self) -> None:
        rc, output = run_cli("legal-graph", "source-inventory", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        sources = {item["source_id"]: item for item in payload["source_status"]}
        self.assertEqual(payload["schema_version"], "nac.legal-source-inventory-status/v0.1")
        self.assertEqual(payload["sources"], 3)
        self.assertTrue(payload["planning_only"])
        self.assertFalse(payload["source_text_ingestion_enabled"])
        self.assertFalse(payload["benchmark_dataset_generated"])
        self.assertFalse(payload["model_training_enabled"])
        self.assertTrue(payload["owner_apply_required_before_ingestion"])
        self.assertIn("recht-bund-bgbl-data-access", sources)
        self.assertEqual(sources["recht-bund-bgbl-data-access"]["terms_review_ref"], "pending")
        self.assertEqual(
            sources["recht-bund-bgbl-data-access"]["review_depth"]["next_required_review"],
            "review_terms_tdm_bulk_access_and_storage_boundary",
        )

    def test_legal_graph_model_card_proposal_cli_returns_gate_status(self) -> None:
        rc, output = run_cli("legal-graph", "model-card-proposal", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        candidates = {item["id"]: item for item in payload["candidate_references"]}
        self.assertEqual(payload["schema_version"], "nac.legal-model-card-proposal-status/v0.1")
        self.assertEqual(payload["status"], "proposal_no_checkpoint_no_training")
        self.assertTrue(payload["owner_apply_required_before_use"])
        self.assertTrue(payload["no_mandate_data"])
        self.assertTrue(payload["no_checkpoint_published"])
        self.assertIn("nvidia-nemotron-pretraining-legal-v1", candidates)

    def test_legal_graph_ai_sbom_delta_proposal_cli_returns_gate_status(self) -> None:
        rc, output = run_cli("legal-graph", "ai-sbom-delta-proposal", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        candidates = {item["id"]: item for item in payload["candidate_components"]}
        self.assertEqual(payload["schema_version"], "nac.legal-ai-sbom-delta-proposal-status/v0.1")
        self.assertEqual(payload["status"], "proposal_no_runtime_no_checkpoint")
        self.assertTrue(payload["owner_apply_required_before_runtime_or_checkpoint"])
        self.assertTrue(payload["no_mandate_data"])
        self.assertTrue(payload["no_source_text_stored"])
        self.assertTrue(payload["no_checkpoint_published"])
        self.assertTrue(payload["no_runtime_enabled"])
        self.assertIn("recht-bund-bgbl-data-access", candidates)

    def test_legal_graph_review_cli_returns_json(self) -> None:
        rc, output = run_cli("legal-graph", "review", "erbrecht", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.legal-graph-review/v0.1")
        self.assertFalse(payload["guardrails"]["commentary_full_text_in_repo"])

    def test_legal_graph_update_dry_run_cli_returns_patch(self) -> None:
        for domain in ("erbrecht", "familienrecht", "gesellschaftsrecht"):
            with self.subTest(domain=domain):
                rc, output = run_cli("legal-graph", "update-dry-run", domain, "--format", "json")

                self.assertEqual(rc, 0, output)
                payload = json.loads(output)
                self.assertEqual(payload["schema_version"], "nac.legal-graph-patch/v0.1")
                self.assertEqual(payload["domain"], domain)
                self.assertFalse(payload["auto_merge_allowed"])
                self.assertFalse(payload["source_manifest"]["commentary_access_allowed"])

    def test_legal_graph_json_errors_are_machine_readable(self) -> None:
        rc, output = run_cli("legal-graph", "review", "unknown", "--format", "json")

        self.assertEqual(rc, 1)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.error/v0.1")
        self.assertEqual(payload["command"], "legal-graph")
        self.assertIn("Unknown legal graph domain", payload["error"])

    def test_tenant_domain_check_cli_returns_json(self) -> None:
        rc, output = run_cli(
            "tenant",
            "domain-check",
            "--domain",
            "kanzlei-notariat.example",
            "--tenant-slug",
            "kanzlei-notariat",
            "--admin-email",
            "admin@kanzlei-notariat.example",
            "--format",
            "json",
        )

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["verification"]["dns_record_name"], "_nac.kanzlei-notariat.example")

    def test_tenant_provision_admin_cli_is_dry_run(self) -> None:
        rc, output = run_cli(
            "tenant",
            "provision-admin",
            "--tenant-slug",
            "kanzlei-notariat",
            "--domain",
            "kanzlei-notariat.example",
            "--admin-email",
            "admin@kanzlei-notariat.example",
            "--admin-display-name",
            "Admin Notariat",
            "--identity-domain-url",
            "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            "--identity-domain-id",
            "ocid1.domain.oc1..aaaaaaaarealidentitydomain",
            "--dry-run",
            "--format",
            "json",
        )

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        self.assertEqual(payload["mode"], "dry_run")
        self.assertTrue(payload["requires_human_approval"])
        self.assertFalse(payload["console_access_required_for_end_users"])

    def test_tenant_apply_request_cli_is_review_artifact_only(self) -> None:
        rc, output = run_cli(
            "tenant",
            "apply-request",
            "--tenant-slug",
            "kanzlei-notariat",
            "--domain",
            "kanzlei-notariat.example",
            "--admin-email",
            "admin@kanzlei-notariat.example",
            "--admin-display-name",
            "Admin Notariat",
            "--identity-domain-url",
            "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            "--identity-domain-id",
            "ocid1.domain.oc1..aaaaaaaarealidentitydomain",
            "--dns-verified",
            "--owner-approval-id",
            "OWNER-APPROVED-32",
            "--audit-event-id",
            "AUDIT-32",
            "--rollback-plan-id",
            "ROLLBACK-32",
            "--dry-run",
            "--format",
            "json",
        )

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        self.assertTrue(payload["ready_to_apply"])
        self.assertEqual(payload["mode"], "review_artifact_only")
        self.assertFalse(payload["productive_write_executed"])
        self.assertEqual(payload["approval"]["owner_approval_id"], "OWNER-APPROVED-32")

    def test_customer_onboarding_plan_cli_returns_json(self) -> None:
        rc, output = run_cli(
            "tenant",
            "customer-plan",
            "--domain",
            "kanzlei-notariat.example",
            "--tenant-slug",
            "kanzlei-notariat",
            "--admin-email",
            "admin@kanzlei-notariat.example",
            "--saas-admin-email",
            "saas-owner@example.com",
            "--format",
            "json",
        )

        self.assertEqual(rc, 0)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.customer-tenant-plan/v0.1")
        self.assertEqual(payload["oci"]["identity"]["customer_domain_strategy"], "single_secondary_domain")
        self.assertEqual(payload["oci"]["resource_isolation"]["compartment_strategy"], "one_compartment_per_customer_domain")
        self.assertEqual(payload["atp"]["strategy"], "shared_atp_with_tenant_id")
        self.assertIn("tenant_id", payload["atp"]["required_controls"])
        self.assertTrue(payload["requires_owner_apply"])

    def test_tenant_dns_check_cli_returns_live_dns_json(self) -> None:
        def fake_resolver(record_name: str) -> dict:
            return {
                "name": record_name,
                "values": ["nac-domain-verification=36685e54c3d26580dace709f1f09c702"],
                "resolver_error": "",
            }

        with patch("nac_identity.dns_txt.resolve_txt_records", fake_resolver):
            rc, output = run_cli(
                "tenant",
                "dns-check",
                "--domain",
                "kanzlei-notariat.example",
                "--tenant-slug",
                "kanzlei-notariat",
                "--admin-email",
                "admin@kanzlei-notariat.example",
                "--format",
                "json",
            )

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        self.assertEqual(payload["schema_version"], "nac.dns-readiness-check/v0.1")
        self.assertEqual(payload["status"], "verified")
        self.assertEqual(payload["source"], "live_dns")

    def test_plugin_actions_are_listed(self) -> None:
        rc, output = run_cli("plugins", "actions")

        self.assertEqual(rc, 0)
        self.assertIn("nac plugins card-readiness", output)
        self.assertIn("nac plugins xnp-reader-prompt", output)
        self.assertIn("nac plugins xnp-workflow-gate", output)
        self.assertIn("nac plugins pkcs7-inspect", output)
        self.assertIn("nac plugins status nac-grundbuch-portal", output)
        self.assertIn("geplant", output)

    def test_plugin_status_lists_every_marketplace_plugin_as_cli_reachable(self) -> None:
        rc, output = run_cli_with_exit("plugins", "status", "--format", "json")

        self.assertEqual(rc, 0, output)
        payload = json.loads(output)
        plugins = {plugin["name"]: plugin for plugin in payload["plugins"]}
        self.assertEqual(
            set(plugins),
            {
                "nac-regulated-core",
                "nac-idaas",
                "nac-cyberjack-rfid",
                "nac-bnotk-xnp",
                "nac-pkcs7-certbundle",
                "nac-handelsregister",
                "nac-grundbuch-portal",
                "nac-oci-evidence",
            },
        )
        self.assertEqual(plugins["nac-cyberjack-rfid"]["cli_status"], "executable")
        self.assertEqual(plugins["nac-cyberjack-rfid"]["command"], "nac plugins card-readiness")
        self.assertEqual(plugins["nac-bnotk-xnp"]["command"], "nac plugins xnp-reader-prompt")
        self.assertEqual(plugins["nac-pkcs7-certbundle"]["command"], "nac plugins pkcs7-inspect")
        self.assertEqual(plugins["nac-grundbuch-portal"]["cli_status"], "planned")
        self.assertEqual(plugins["nac-grundbuch-portal"]["command"], "nac plugins status nac-grundbuch-portal")
        self.assertIn("Codex-Plugin", plugins["nac-grundbuch-portal"]["plugin_role"])
        self.assertIn("NaC-CLI", plugins["nac-grundbuch-portal"]["cli_role"])

    def test_single_plugin_status_explains_cli_and_plugin_boundary(self) -> None:
        rc, output = run_cli_with_exit("plugins", "status", "nac-grundbuch-portal")

        self.assertEqual(rc, 0, output)
        self.assertIn("NaC-Anbindung: Grundbuch", output)
        self.assertIn("CLI-Status: geplant", output)
        self.assertIn("CLI-Befehl: nac plugins status nac-grundbuch-portal", output)
        self.assertIn("Plugin-Rolle: Sichtbarkeit", output)
        self.assertIn("CLI-Rolle: kanonische Bedienkante", output)

    def test_unknown_plugin_status_fails_with_available_names(self) -> None:
        rc, output = run_cli_with_exit("plugins", "status", "nac-unbekannt")

        self.assertEqual(rc, 1)
        self.assertIn("Unbekannte NaC-Anbindung: nac-unbekannt", output)
        self.assertIn("nac-grundbuch-portal", output)

    def test_pkcs7_plugin_action_is_reachable_through_nac_cli(self) -> None:
        rc, output = run_cli("plugins", "pkcs7-inspect", "--json")

        self.assertEqual(rc, 0)
        self.assertIn('"plugin": "nac-pkcs7-certbundle"', output)
        self.assertIn('"overall_status": "manual_review"', output)

    def test_xnp_workflow_gate_consumes_reader_prompt_evidence_through_nac_cli(self) -> None:
        evidence = {
            "schema_version": "nac.xnp.reader-prompt/v1",
            "plugin": "nac-bnotk-xnp",
            "prompt_id": "XNP-RP-00000000-0000-0000-0000-000000000000",
            "generated_at": "2026-06-29T00:00:00+00:00",
            "overall_status": "prompted",
            "mode": "local_dry_run",
            "intent": "reader_function_check",
            "reader_prompt": {
                "target": "local_cyberjack_reader",
                "route": "nac-bnotk-xnp -> nac-cyberjack-rfid",
                "text": "Bitte testen. Kein Secret.",
                "operator_actions": [],
                "dry_run_only": True,
            },
            "xnp_local_interface": {"status": "reachable", "host": "127.0.0.1", "open_ports": [12774]},
            "card_gate_evidence": {"overall_status": "ready", "evidence_id": "CJ-000"},
            "policy": {
                "pin_captured": False,
                "card_data_captured": False,
                "xnp_api_key_captured": False,
                "xnp_login_performed": False,
                "external_network_calls": False,
                "localhost_only": True,
                "productive_xnp_write": False,
            },
            "checks": [],
            "next_required_action": "Proceed with the local XNP reader-function check.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "xnp-reader-prompt.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            rc, output = run_cli(
                "plugins",
                "xnp-workflow-gate",
                "--evidence",
                str(evidence_path),
                "--json",
            )

        self.assertEqual(rc, 0)
        payload = json.loads(output)
        serialized = json.dumps(payload, sort_keys=True).lower()
        self.assertEqual(payload["schema_version"], "nac.xnp.workflow-gate/v1")
        self.assertEqual(payload["workflow_gate"]["status"], "ready_for_operator_review")
        self.assertTrue(payload["decision"]["workflow_can_prepare_next_step"])
        self.assertFalse(payload["decision"]["productive_xnp_action_allowed"])
        self.assertNotIn("bitte testen", serialized)
        self.assertFalse(_contains_key(payload, "value"))

    def test_qms_status_and_documents_are_reachable(self) -> None:
        rc, output = run_cli("qms", "status")

        self.assertEqual(rc, 0)
        self.assertIn("NaC-QMS Status", output)
        self.assertIn("Qualitätsziele: 4", output)
        self.assertIn("Rollen: 4", output)

        rc, output = run_cli("qms", "iso9001-map")
        self.assertEqual(rc, 0)
        self.assertIn("ISO-9001-Mapping", output)

        rc, output = run_cli("qms", "audit-plan")
        self.assertEqual(rc, 0)
        self.assertIn("Internes Auditprogramm", output)

    def test_tenant_init_status_and_write_demo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tenant_repo = Path(temp_dir) / "demo8notariat"

            rc, output = run_cli(
                "tenant",
                "init",
                "--repo",
                str(tenant_repo),
                "--name",
                "demo8notariat",
                "--remote-url",
                "https://github.com/notariat8/demo8notariat.git",
            )
            self.assertEqual(rc, 0)
            self.assertIn("NaC-Datenrepo initialisiert", output)
            self.assertTrue((tenant_repo / ".nac-tenant.json").is_file())

            rc, output = run_cli("tenant", "status", "--repo", str(tenant_repo))
            self.assertEqual(rc, 0)
            self.assertIn("Demo-Vorgänge: 0", output)
            self.assertIn("Akten: 0", output)
            self.assertIn("https://github.com/notariat8/demo8notariat.git", output)

            rc, output = run_cli(
                "tenant",
                "write-demo",
                "immobilienkaufvertrag",
                "--repo",
                str(tenant_repo),
                "--case-id",
                "DEMO-2026-0001",
            )
            self.assertEqual(rc, 0)
            self.assertIn("NaC-Demo-Vorgang geschrieben", output)

            case_file = tenant_repo / "daten" / "demo" / "DEMO-2026-0001" / "case.json"
            self.assertTrue(case_file.is_file())
            case_text = case_file.read_text(encoding="utf-8")
            self.assertIn('"data_classification": "synthetic_demo_only"', case_text)
            self.assertIn('"real_mandate_data_allowed": false', case_text)

            rc, output = run_cli(
                "tenant",
                "write-sample-akte",
                "--repo",
                str(tenant_repo),
                "--akten-id",
                "UVZ-2026-0001",
            )
            self.assertEqual(rc, 0)
            self.assertIn("NaC-Musterakte geschrieben", output)

            matter_file = tenant_repo / "akten" / "2026" / "UVZ-2026-0001" / "akte.json"
            person_file = tenant_repo / "personen" / "PER-DEMO-VERKAEUFER-ANNA-BERGER.json"
            document_file = tenant_repo / "dokumente" / "DOC-DEMO-2026-0001-GRUNDBUCH" / "metadata.json"
            self.assertTrue(matter_file.is_file())
            self.assertTrue(person_file.is_file())
            self.assertTrue(document_file.is_file())
            matter_text = matter_file.read_text(encoding="utf-8")
            self.assertIn('"participant_person_ids"', matter_text)
            self.assertIn('"document_ids"', matter_text)

            rc, output = run_cli("tenant", "status", "--repo", str(tenant_repo))
            self.assertEqual(rc, 0)
            self.assertIn("Akten: 1", output)
            self.assertIn("Personen: 3", output)
            self.assertIn("Dokumente: 3", output)

            rc, output = run_cli("tenant", "list-akten", "--repo", str(tenant_repo))
            self.assertEqual(rc, 0)
            self.assertIn("UVZ-2026-0001", output)
            self.assertIn("Immobilienkaufvertrag Berger/Lange", output)
            self.assertIn("Grundbuchauszug prüfen", output)

            rc, output = run_cli(
                "tenant",
                "show-akte",
                "--repo",
                str(tenant_repo),
                "--akten-id",
                "UVZ-2026-0001",
            )
            self.assertEqual(rc, 0)
            self.assertIn("NaC-Akte", output)
            self.assertIn("Beteiligte: 2", output)
            self.assertIn("Dokumente: 3", output)
            self.assertIn("Aufgaben: 5", output)
            self.assertIn("Nebenakten-Export: vorbereitet", output)

            enriched_matter = json.loads(matter_file.read_text(encoding="utf-8"))
            self.assertEqual(enriched_matter["schema_version"], "nac.matter/v0.3")
            self.assertIn("notary_software_layers", enriched_matter)
            self.assertIn("contacts", enriched_matter["notary_software_layers"])
            self.assertIn("electronic_side_file", enriched_matter["notary_software_layers"])
            self.assertTrue((tenant_repo / "akten" / "2026" / "UVZ-2026-0001" / "aufgaben.json").is_file())
            self.assertTrue((tenant_repo / "akten" / "2026" / "UVZ-2026-0001" / "grundbuch.json").is_file())
            self.assertTrue((tenant_repo / "akten" / "2026" / "UVZ-2026-0001" / "kosten.json").is_file())
            self.assertTrue((tenant_repo / "akten" / "2026" / "UVZ-2026-0001" / "nachweise.json").is_file())
            document_links = json.loads(
                (tenant_repo / "akten" / "2026" / "UVZ-2026-0001" / "dokumente.json").read_text(encoding="utf-8")
            )
            document_roles = {item["document_id"]: item["role"] for item in document_links["documents"]}
            self.assertEqual(document_roles["DOC-DEMO-2026-0001-ENTWURF"], "draft_document")

            rc, output = run_cli("qms", "evidence", "--repo", str(tenant_repo))
            self.assertEqual(rc, 0)
            self.assertIn("NaC-QMS Nachweisbild", output)
            self.assertIn("Akten: 1", output)
            self.assertIn("Dokumente: 3", output)

    def test_import_job_cli_creates_processes_and_applies_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tenant_repo = Path(temp_dir) / "tenant"
            proposal_id = "IMP-20260521-UNTERSCHRIFTSBEGLAUBIGUNG-ERIKA"
            source = tenant_repo / "eingang" / "dateien" / proposal_id / "personalausweis-erika.jpg"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"synthetic-image")
            (tenant_repo / "eingang" / "import-vorschlaege").mkdir(parents=True, exist_ok=True)
            (tenant_repo / ".nac-tenant.json").write_text(
                json.dumps({"schema_version": "nac.tenant/v0.2", "name": "tenant", "mode": "demo"}) + "\n",
                encoding="utf-8",
            )
            (tenant_repo / "eingang" / "import-vorschlaege" / f"{proposal_id}.json").write_text(
                json.dumps(
                    {
                        "schema_version": "nac.import-proposal/v0.1",
                        "proposal_id": proposal_id,
                        "status": "pending",
                        "synthetic_test_data": True,
                        "matter_values": {
                            "participant_name": "Erika Mustermann",
                            "document_title": "Personalausweis zur Identitätsprüfung",
                            "metadata": {"document_number": "LZ6311T47"},
                        },
                        "source_files": [
                            {
                                "label": "Vorderseite",
                                "filename": "personalausweis-erika.jpg",
                                "media_type": "image/jpeg",
                                "staged_path": f"eingang/dateien/{proposal_id}/personalausweis-erika.jpg",
                            }
                        ],
                        "review": {"requires_human_confirmation": True},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            rc, output = run_cli(
                "import",
                "jobs",
                "create",
                "--repo",
                str(tenant_repo),
                "--proposal-id",
                proposal_id,
                "--format",
                "json",
            )
            self.assertEqual(rc, 0)
            created = json.loads(output)
            self.assertEqual(created["status"], "queued")

            rc, output = run_cli(
                "import",
                "jobs",
                "process",
                "--repo",
                str(tenant_repo),
                "--job-id",
                created["job_id"],
                "--format",
                "json",
            )
            self.assertEqual(rc, 0)
            processed = json.loads(output)
            self.assertEqual(processed["job"]["status"], "completed")
            self.assertEqual(processed["extraction"]["metadata"]["document_number"], "LZ6311T47")

            rc, output = run_cli(
                "import",
                "jobs",
                "apply-result",
                "--repo",
                str(tenant_repo),
                "--job-id",
                created["job_id"],
                "--format",
                "json",
            )
            self.assertEqual(rc, 0)
            applied = json.loads(output)
            self.assertEqual(applied["job"]["status"], "applied")
            self.assertEqual(applied["proposal"]["matter_values"]["metadata"]["ocr_review_status"], "ready_for_human_review")


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


if __name__ == "__main__":
    unittest.main()
