from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "render_quality_gate_comment.py"


def load_renderer_module():
    spec = importlib.util.spec_from_file_location("render_quality_gate_comment", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = load_renderer_module()


class RenderQualityGateCommentTests(unittest.TestCase):
    def test_renderer_keeps_src_package_before_scripts_shadow_module(self) -> None:
        self.assertEqual(sys.path[0], str(REPO_ROOT / "src"))
        self.assertTrue(renderer.load_catalogs.__module__.startswith("notary_kg."))

    def test_comment_renders_build_status_and_kg_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _write_graph(repo_root)
            payload = {
                "overall_status": "PASSED",
                "profile": "strict",
                "timestamp_utc": "2026-06-30T00:00:00+00:00",
                "checks": [
                    {"id": "unit_tests", "title": "Unit Tests", "passed": True, "duration_ms": 12},
                    {"id": "knowledge_graph", "title": "Knowledge Graph Baseline", "passed": False, "duration_ms": 34},
                    {
                        "id": "m365_release_readiness_gate",
                        "title": "M365 Release Readiness Gate",
                        "passed": True,
                        "duration_ms": 56,
                    },
                ],
            }

            comment = renderer._build_markdown(payload, renderer._build_kg_readiness(repo_root))

        self.assertIn("<!-- nac-quality-gate-comment -->", comment)
        self.assertIn("## NaC Developer CI", comment)
        self.assertIn("- Build Status: **PASSED**", comment)
        self.assertIn("- Checks: `2/3` bestanden", comment)
        self.assertIn("### M365 MVP Readiness", comment)
        self.assertIn("- Go/No-Go: `mvp_release_readiness=READY`", comment)
        self.assertIn("- Runner summary: `release_gate_readiness=READY`", comment)
        self.assertIn("- CI enforcement: **ENFORCED**", comment)
        self.assertIn("release-gate-write-readiness", comment)
        self.assertIn("### KG Readiness", comment)
        self.assertIn("- Status: **READY**", comment)
        self.assertIn("| `online-gmbh-gruendung` | `1` | `nac-bnotk-xnp` |", comment)
        self.assertIn("out/quality/comment.md", comment)

    def test_missing_status_file_still_renders_kg_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _write_graph(repo_root)
            status = renderer._load_status(repo_root / "missing.json")
            comment = renderer._build_markdown(status, renderer._build_kg_readiness(repo_root))

        self.assertIn("Statusdatei fehlt", comment)
        self.assertIn("### M365 MVP Readiness", comment)
        self.assertIn("- CI enforcement: **NOT_EVALUATED**", comment)
        self.assertIn("### KG Readiness", comment)

    def test_kg_readiness_reports_blocking_value_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _write_graph(repo_root, value="nicht-speichern")

            readiness = renderer._build_kg_readiness(repo_root)

        self.assertEqual(readiness["status"], "NEEDS_REVIEW")
        self.assertEqual(readiness["totals"]["value_fields"], 1)


def _write_graph(repo_root: Path, value: str | None = None) -> None:
    graph_path = repo_root / "usecases" / "online-gmbh-gruendung" / "knowledge-graph.graph.json"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    required_item = {
        "id": "company.name",
        "label": "Gesellschaft Name",
        "question": "Wie lautet der Name?",
        "status": "open",
    }
    if value is not None:
        required_item["value"] = value
    graph_path.write_text(
        json.dumps(
            {
                "schema_version": "nac.knowledge-graph/v0.1",
                "graph_id": "usecase.online-gmbh-gruendung",
                "title": "Online-GmbH-Gründung",
                "status": "draft",
                "cases": [
                    {
                        "id": "case.online-gmbh-gruendung",
                        "slug": "online-gmbh-gruendung",
                        "title": "Online-GmbH-Gründung",
                        "status": "draft",
                        "priority": "P0",
                        "usecase_path": "usecases/online-gmbh-gruendung",
                        "required_information": [required_item],
                        "documents": [],
                        "decisions": [],
                        "gates": [],
                        "evidence": [],
                        "plugin_dependencies": ["nac-bnotk-xnp"],
                        "workflow_dependencies": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
