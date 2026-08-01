from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.validate_generic_workbench_foundation as validator
from scripts import quality_gate


class GenericWorkbenchFoundationValidatorTests(unittest.TestCase):
    def test_strict_quality_gate_registers_foundation_validator(self) -> None:
        strict_checks = {
            check_id: command
            for check_id, _title, command in quality_gate.build_checks("strict")
        }
        self.assertEqual(
            strict_checks["generic_workbench_foundation"][-1],
            "scripts/validate_generic_workbench_foundation.py",
        )

    def test_rejects_missing_required_build_artifact(self) -> None:
        errors: list[str] = []
        validator._verify_manifest_entries(
            [{"relativePath": "build/not-yet-created.js", "sha256": "0" * 64}],
            errors,
            require_present=True,
        )
        self.assertEqual(errors, ["visual evidence file missing: build/not-yet-created.js"])

    def test_rejects_backend_domain_state_derivation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            backend = Path(directory) / "workbench_projection.py"
            backend.write_text(
                'attention.append({"reason": "derived"})\n'
                'if item["decision"] != "deny":\n'
                '    raise ValueError\n',
                encoding="utf-8",
            )
            original_path = Path.read_text

            def read_text(path: Path, *args: object, **kwargs: object) -> str:
                if path == validator.REPO_ROOT / "src" / "nac_bff" / "workbench_projection.py":
                    return backend.read_text(encoding="utf-8")
                return original_path(path, *args, **kwargs)

            with patch.object(Path, "read_text", read_text):
                errors = validator.validate()

        self.assertIn(
            "BFF projection must not derive domain state: attention.append",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
