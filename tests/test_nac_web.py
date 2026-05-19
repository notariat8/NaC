from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_web.bpmn import find_bpmn_model, list_bpmn_models, render_bpmn_svg  # noqa: E402
from nac_web.server import NaCLocalWebApp, build_home_page, build_kg_page  # noqa: E402
from notary_kg.editor import build_editor_view  # noqa: E402


class NaCLocalWebTests(unittest.TestCase):
    def test_home_page_links_bpmn_and_kg_views(self) -> None:
        html = build_home_page(REPO_ROOT)

        self.assertIn("/bpmn/immobilienkaufvertrag", html)
        self.assertIn("/kg/immobilienkaufvertrag", html)
        self.assertIn("Lokaler NaC-Webserver", html)

    def test_bpmn_svg_renders_local_model(self) -> None:
        model = find_bpmn_model(REPO_ROOT, "immobilienkaufvertrag")
        svg = render_bpmn_svg(model)

        self.assertIn("<svg", svg)
        self.assertIn("Offene Angaben", svg)
        self.assertTrue(model.has_diagram)

    def test_kg_page_blocks_value_field_surface(self) -> None:
        view = build_editor_view(REPO_ROOT, "immobilienkaufvertrag")
        html = build_kg_page(view)

        self.assertIn("Schutzregel", html)
        self.assertIn("Offene Angaben", html)
        self.assertNotIn("<td>value</td>", html)

    def test_app_serves_health_and_api(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        health_status, health_type, health_body = app.handle("/healthz")
        api_status, api_type, api_body = app.handle("/api/bpmn/immobilienkaufvertrag")

        self.assertEqual(health_status, 200)
        self.assertEqual(health_type, "application/json; charset=utf-8")
        self.assertIn(b'"status": "ok"', health_body)
        self.assertEqual(api_status, 200)
        self.assertEqual(api_type, "application/json; charset=utf-8")
        self.assertIn(b"Process_Immobilienkaufvertrag", api_body)

    def test_bpmn_model_catalog_is_not_empty(self) -> None:
        models = list_bpmn_models(REPO_ROOT)

        self.assertGreaterEqual(len(models), 1)
        self.assertTrue(any(model.stem == "immobilienkaufvertrag" for model in models))


if __name__ == "__main__":
    unittest.main()
