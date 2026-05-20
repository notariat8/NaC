from __future__ import annotations

import unittest

from scripts import validate_gantt_progress


class GanttProgressValidationTest(unittest.TestCase):
    def test_regular_change_does_not_require_global_gantt(self) -> None:
        errors = validate_gantt_progress.validate_changed_files(
            {"docs/de/cli.md", "src/nac_cli/cli.py"}
        )

        self.assertEqual(errors, [])

    def test_area_change_is_guidance_not_blocker(self) -> None:
        errors = validate_gantt_progress.validate_changed_files(
            {"plugins/nac-cyberjack-rfid/README.md"}
        )
        guidance = validate_gantt_progress.gantt_update_guidance(
            {"plugins/nac-cyberjack-rfid/README.md"}
        )

        self.assertEqual(errors, [])
        self.assertTrue(any("Themen-Gantt" in entry for entry in guidance))

    def test_gantt_change_reports_render_safety_guidance(self) -> None:
        guidance = validate_gantt_progress.gantt_update_guidance(
            {"roadmap/GANTT.md"}
        )

        self.assertTrue(any("Mermaid-Render-Sicherheit" in entry for entry in guidance))


if __name__ == "__main__":
    unittest.main()
