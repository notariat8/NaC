from __future__ import annotations

from pathlib import Path
import sys
import unittest


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.azure_activation_composition import _spfx_deployment_failure_code
from nac_bff.azure_activation_runner import ActivationStepError
from nac_m365_graph.spfx_site_deployment import (
    APPROVED_WEB_API_PERMISSION_REQUESTS,
    _normalize_catalog_permissions,
)


class SpfxBffCatalogReadbackRegressionTests(unittest.TestCase):
    def test_exact_cli_permission_string_is_normalized(self) -> None:
        self.assertEqual(
            _normalize_catalog_permissions("NaC M365 BFF, Matter.Read"),
            list(APPROVED_WEB_API_PERMISSION_REQUESTS),
        )

    def test_broader_or_ambiguous_cli_permission_strings_fail_closed(self) -> None:
        unsafe_values = (
            "NaC M365 BFF, Matter.Read, Sites.Read.All",
            "NaC M365 BFF, Matter.Write",
            "Matter.Read, NaC M365 BFF",
            "NaC M365 BFF,Matter.Read",
        )

        for value in unsafe_values:
            with self.subTest(value=value):
                self.assertEqual(_normalize_catalog_permissions(value), [])

    def test_redacted_failure_shape_becomes_stable_error_code(self) -> None:
        evidence = {
            "status": "FAILED",
            "steps": [
                {
                    "name": "validate_control_plane_response",
                    "status": "FAILED",
                    "error": {
                        "category": "unsafe_control_plane_response",
                        "message": "raw command output was withheld",
                    },
                }
            ],
        }

        code = _spfx_deployment_failure_code(evidence)
        self.assertEqual(
            code,
            "SPFX_CONTROL_PLANE_RESPONSE_UNSAFE",
        )
        self.assertEqual(ActivationStepError(code).code, code)

    def test_incomplete_failure_shape_uses_generic_code(self) -> None:
        self.assertEqual(
            _spfx_deployment_failure_code({"status": "FAILED", "steps": []}),
            "SPFX_DEPLOYMENT_FAILED",
        )

    def test_unknown_failure_category_is_not_reflected(self) -> None:
        evidence = {
            "status": "FAILED",
            "steps": [
                {
                    "name": "unexpected-secret-step",
                    "status": "FAILED",
                    "error": {"category": "unexpected-secret-category"},
                }
            ],
        }

        self.assertEqual(
            _spfx_deployment_failure_code(evidence),
            "SPFX_DEPLOYMENT_FAILED",
        )


if __name__ == "__main__":
    unittest.main()
