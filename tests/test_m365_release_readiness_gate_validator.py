from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_m365_release_readiness_gate.py"
SPEC = importlib.util.spec_from_file_location("validate_m365_release_readiness_gate", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError("Could not load validate_m365_release_readiness_gate.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class M365ReleaseReadinessGateValidatorTests(unittest.TestCase):
    def test_current_repo_passes_release_readiness_gate_validator(self) -> None:
        self.assertEqual(validator.validate(REPO_ROOT), [])

    def test_quality_gate_runs_release_readiness_gate_validator_in_strict_profile(self) -> None:
        quality_gate_spec = importlib.util.spec_from_file_location(
            "quality_gate",
            REPO_ROOT / "scripts" / "quality_gate.py",
        )
        if quality_gate_spec is None or quality_gate_spec.loader is None:
            raise ImportError("Could not load quality_gate.py")
        quality_gate = importlib.util.module_from_spec(quality_gate_spec)
        sys.modules[quality_gate_spec.name] = quality_gate
        quality_gate_spec.loader.exec_module(quality_gate)

        checks = {check_id: command for check_id, _title, command in quality_gate.build_checks("strict")}

        self.assertIn("m365_release_readiness_gate", checks)
        self.assertEqual(
            checks["m365_release_readiness_gate"],
            [validator.sys.executable, "scripts/validate_m365_release_readiness_gate.py"],
        )

    def test_validator_reports_missing_go_no_go_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_valid_tree(root)
            batch_doc = root / "docs" / "de" / "operations" / "m365-mcp-batch-approval.md"
            batch_doc.write_text("missing readiness gate\n", encoding="utf-8")

            errors = validator.validate(root)

        self.assertIn("docs/de/operations/m365-mcp-batch-approval.md", "\n".join(errors))
        self.assertIn("MVP-Go/No-Go-Abnahmekriterium", "\n".join(errors))


def _write_minimal_valid_tree(root: Path) -> None:
    for relative_path, markers in validator.REQUIRED_DOC_MARKERS.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(markers) + "\n", encoding="utf-8")
    quality_gate = root / "scripts" / "quality_gate.py"
    quality_gate.parent.mkdir(parents=True, exist_ok=True)
    quality_gate.write_text("\n".join(validator.REQUIRED_QUALITY_GATE_MARKERS) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
