from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from nac_legal_graph.catalog import build_review_payload, legal_graph_status, load_domain_graph
from nac_legal_graph.patches import build_update_patch
from nac_legal_graph.sources import load_source_manifest, legal_graph_source_status, legal_source_inventory_status


REPO_ROOT = Path(__file__).resolve().parents[1]


class LegalGraphTests(unittest.TestCase):
    def test_erbrecht_graph_loads_without_mandate_values(self) -> None:
        graph = load_domain_graph(REPO_ROOT, "erbrecht")

        self.assertEqual(graph["schema_version"], "nac.legal-graph/v0.1")
        self.assertEqual(graph["domain"]["id"], "erbrecht")
        self.assertGreaterEqual(len(graph["nodes"]), 10)
        self.assertGreaterEqual(len(graph["edges"]), 8)
        self.assertFalse(_contains_key(graph, "value"))
        self.assertFalse(_contains_text(graph, "Max Mustermann"))

    def test_status_counts_all_legal_graph_domains(self) -> None:
        status = legal_graph_status(REPO_ROOT)
        domains = {item["id"]: item for item in status["domain_status"]}

        self.assertEqual(status["schema_version"], "nac.legal-graph-status/v0.1")
        self.assertEqual(status["domains"], 3)
        self.assertGreaterEqual(domains["erbrecht"]["nodes"], 10)
        self.assertGreaterEqual(domains["familienrecht"]["nodes"], 10)
        self.assertGreaterEqual(domains["gesellschaftsrecht"]["nodes"], 10)
        self.assertGreaterEqual(domains["erbrecht"]["review_required"], 1)
        self.assertGreaterEqual(domains["familienrecht"]["review_required"], 1)
        self.assertGreaterEqual(domains["gesellschaftsrecht"]["review_required"], 1)

    def test_review_payload_exposes_sources_and_commentary_boundary(self) -> None:
        payload = build_review_payload(REPO_ROOT, "erbrecht")

        self.assertEqual(payload["schema_version"], "nac.legal-graph-review/v0.1")
        self.assertEqual(payload["domain"], "erbrecht")
        self.assertIn("commentary_connector", {item["type"] for item in payload["review_items"]})
        self.assertTrue(payload["guardrails"]["human_review_required"])
        self.assertFalse(payload["guardrails"]["commentary_full_text_in_repo"])

    def test_erbrecht_graph_json_is_stable(self) -> None:
        graph_path = REPO_ROOT / "workflows" / "legal-graph" / "domains" / "erbrecht.graph.json"
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
        node_ids = {node["id"] for node in payload["nodes"]}

        self.assertIn("norm.bgb.1945", node_ids)
        self.assertIn("usecase.erbausschlagung", node_ids)
        self.assertIn("connector.beck-online", node_ids)

    def test_familienrecht_graph_json_is_stable(self) -> None:
        payload = load_domain_graph(REPO_ROOT, "familienrecht")
        node_ids = {node["id"] for node in payload["nodes"]}

        self.assertEqual(payload["domain"]["id"], "familienrecht")
        self.assertIn("norm.bgb.1408", node_ids)
        self.assertIn("usecase.ehevertrag", node_ids)
        self.assertIn("connector.juris", node_ids)

    def test_gesellschaftsrecht_graph_json_is_stable(self) -> None:
        payload = load_domain_graph(REPO_ROOT, "gesellschaftsrecht")
        node_ids = {node["id"] for node in payload["nodes"]}

        self.assertEqual(payload["domain"]["id"], "gesellschaftsrecht")
        self.assertIn("norm.gmbhg.2", node_ids)
        self.assertIn("usecase.gmbh-gruendung", node_ids)
        self.assertIn("connector.wolters-kluwer", node_ids)

    def test_update_patch_is_review_only_and_does_not_merge(self) -> None:
        patch = build_update_patch(REPO_ROOT, "erbrecht")

        self.assertEqual(patch["schema_version"], "nac.legal-graph-patch/v0.1")
        self.assertEqual(patch["domain"], "erbrecht")
        self.assertEqual(patch["status"], "proposed")
        self.assertFalse(patch["auto_merge_allowed"])
        self.assertTrue(patch["human_review_required"])
        self.assertEqual(patch["source_manifest"]["source_id"], "primary.gesetze-im-internet.bgb.erbrecht")
        self.assertEqual(patch["source_manifest"]["retrieval_mode"], "metadata_only_fixture")
        self.assertFalse(patch["source_manifest"]["commentary_access_allowed"])
        self.assertEqual(patch["changes"][0]["action"], "add_node")
        self.assertEqual(patch["changes"][0]["node"]["id"], "norm.bgb.1944")

    def test_update_patch_excludes_commentary_connector_changes_for_primary_source_pilot(self) -> None:
        patch = build_update_patch(REPO_ROOT, "erbrecht")
        commentary_changes = [
            change for change in patch["changes"]
            if change.get("node", {}).get("type") == "commentary_connector"
        ]

        self.assertEqual(commentary_changes, [])

    def test_primary_source_manifest_blocks_commentary_access(self) -> None:
        manifest = load_source_manifest(REPO_ROOT, "erbrecht")

        self.assertEqual(manifest["schema_version"], "nac.legal-graph-source/v0.1")
        self.assertEqual(manifest["domain"], "erbrecht")
        self.assertEqual(manifest["source_id"], "primary.gesetze-im-internet.bgb.erbrecht")
        self.assertEqual(manifest["source_type"], "primary_law")
        self.assertEqual(manifest["retrieval_mode"], "metadata_only_fixture")
        self.assertFalse(manifest["commentary_access_allowed"])
        self.assertFalse(manifest["credentials_required"])
        self.assertFalse(manifest["provider_query_allowed"])
        self.assertIn("candidate_node_metadata", manifest["allowed_outputs"])
        self.assertIn("query_commentary_connector", manifest["blocked_actions"])

    def test_source_status_reports_primary_source_pilot(self) -> None:
        status = legal_graph_source_status(REPO_ROOT)
        sources = {item["domain"]: item for item in status["source_status"]}

        self.assertEqual(status["schema_version"], "nac.legal-graph-source-status/v0.1")
        self.assertEqual(status["sources"], 3)
        self.assertEqual(set(sources), {"erbrecht", "familienrecht", "gesellschaftsrecht"})
        for source in sources.values():
            self.assertEqual(source["retrieval_mode"], "metadata_only_fixture")
            self.assertFalse(source["commentary_access_allowed"])

    def test_source_inventory_status_reports_license_tdm_gate_without_ingestion(self) -> None:
        status = legal_source_inventory_status(REPO_ROOT)
        sources = {item["source_id"]: item for item in status["source_status"]}

        self.assertEqual(status["schema_version"], "nac.legal-source-inventory-status/v0.1")
        self.assertEqual(status["status"], "source_inventory_readiness_no_ingestion")
        self.assertEqual(status["sources"], 3)
        self.assertTrue(status["planning_only"])
        self.assertFalse(status["source_text_ingestion_enabled"])
        self.assertFalse(status["benchmark_dataset_generated"])
        self.assertFalse(status["model_training_enabled"])
        self.assertTrue(status["owner_apply_required_before_ingestion"])
        self.assertIn("nvidia-nemotron-pretraining-legal-v1", sources)
        self.assertIn("recht-bund-bgbl-data-access", sources)
        self.assertIn("wikipedia-rechtsquelle-concept-reference", sources)
        self.assertEqual(
            sources["recht-bund-bgbl-data-access"]["tdm_status"],
            "tdm_and_bulk_access_terms_require_review",
        )
        self.assertIn(
            "download_full_text_corpus_without_owner_apply",
            status["blocked_actions"],
        )

    def test_update_patch_works_for_all_primary_source_domains_without_commentary_changes(self) -> None:
        for domain in ("erbrecht", "familienrecht", "gesellschaftsrecht"):
            with self.subTest(domain=domain):
                patch = build_update_patch(REPO_ROOT, domain)
                commentary_changes = [
                    change for change in patch["changes"]
                    if change.get("node", {}).get("type") == "commentary_connector"
                ]

                self.assertEqual(patch["domain"], domain)
                self.assertEqual(patch["source_manifest"]["retrieval_mode"], "metadata_only_fixture")
                self.assertFalse(patch["source_manifest"]["commentary_access_allowed"])
                self.assertEqual(commentary_changes, [])

    def test_update_patch_rejects_fixture_with_mandate_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            domain_dir = repo_root / "workflows" / "legal-graph" / "domains"
            fixture_dir = repo_root / "workflows" / "legal-graph" / "fixtures"
            domain_dir.mkdir(parents=True)
            fixture_dir.mkdir(parents=True)
            shutil.copyfile(
                REPO_ROOT / "workflows" / "legal-graph" / "domains" / "erbrecht.graph.json",
                domain_dir / "erbrecht.graph.json",
            )
            source_dir = repo_root / "workflows" / "legal-graph" / "sources"
            source_dir.mkdir(parents=True)
            shutil.copyfile(
                REPO_ROOT / "workflows" / "legal-graph" / "sources" / "erbrecht-primary-source.json",
                source_dir / "erbrecht-primary-source.json",
            )
            fixture = json.loads(
                (REPO_ROOT / "workflows" / "legal-graph" / "fixtures" / "erbrecht-source-update.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture["candidate_nodes"][0]["value"] = "UVZ-2026-0001"
            (fixture_dir / "erbrecht-source-update.json").write_text(
                json.dumps(fixture, ensure_ascii=False),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "mandate values"):
                build_update_patch(repo_root, "erbrecht")

    def test_update_patch_rejects_dangling_fixture_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            domain_dir = repo_root / "workflows" / "legal-graph" / "domains"
            fixture_dir = repo_root / "workflows" / "legal-graph" / "fixtures"
            domain_dir.mkdir(parents=True)
            fixture_dir.mkdir(parents=True)
            shutil.copyfile(
                REPO_ROOT / "workflows" / "legal-graph" / "domains" / "erbrecht.graph.json",
                domain_dir / "erbrecht.graph.json",
            )
            source_dir = repo_root / "workflows" / "legal-graph" / "sources"
            source_dir.mkdir(parents=True)
            shutil.copyfile(
                REPO_ROOT / "workflows" / "legal-graph" / "sources" / "erbrecht-primary-source.json",
                source_dir / "erbrecht-primary-source.json",
            )
            fixture = json.loads(
                (REPO_ROOT / "workflows" / "legal-graph" / "fixtures" / "erbrecht-source-update.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture["candidate_edges"][0]["from"] = "norm.bgb.missing"
            (fixture_dir / "erbrecht-source-update.json").write_text(
                json.dumps(fixture, ensure_ascii=False),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unknown endpoint"):
                build_update_patch(repo_root, "erbrecht")


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def _contains_text(value: object, text: str) -> bool:
    if isinstance(value, str):
        return text in value
    if isinstance(value, dict):
        return any(_contains_text(item, text) for item in value.values())
    if isinstance(value, list):
        return any(_contains_text(item, text) for item in value)
    return False


if __name__ == "__main__":
    unittest.main()
