from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "superpowers" / "plans" / "2026-06-20-notarkammer-demo-readiness.md",
    "en": REPO_ROOT / "docs" / "en" / "superpowers" / "plans" / "2026-06-20-notarkammer-demo-readiness.md",
}


def read_plans() -> dict[str, str]:
    for path in PLAN_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing Notarkammer demo readiness plan: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in PLAN_DOCS.items()}


class NotarkammerDemoReadinessPlanTests(unittest.TestCase):
    def test_plan_exists_in_german_and_english(self) -> None:
        for path in PLAN_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_plan_defines_multi_agent_day_mode_and_parallel_lanes(self) -> None:
        plans = read_plans()

        self.assertIn("Aktueller Tagesmodus Für Große Schritte", plans["de"])
        self.assertIn("Current Day Mode For Larger Steps", plans["en"])

        for content in plans.values():
            lowered = content.lower()
            self.assertIn("multi-agent", lowered)
            self.assertIn("pr-only", lowered)
            self.assertIn("www-n8", content)
            self.assertIn("BPMN", content)
            self.assertIn("Live", content)
            self.assertIn("worktree", lowered)

    def test_plan_keeps_routine_read_only_owner_free_but_preserves_gates(self) -> None:
        combined = "\n".join(read_plans().values())

        owner_free_terms = [
            "GitHub PR-, Issue-, Branch-, Check- und Diff-Status lesen",
            "Read GitHub PR, issue, branch, check and diff status",
            "Lokale Tests",
            "Run local tests",
            "read-only",
        ]
        for term in owner_free_terms:
            self.assertIn(term, combined)

        required_gates = [
            "Design Approval",
            "Review/Merge",
            "Release Approval",
            "Apply Approval",
            "Secret",
            "destruktive Git",
            "destructive Git",
        ]
        for gate in required_gates:
            self.assertIn(gate, combined)

    def test_plan_does_not_turn_demo_prep_into_live_oci_or_secret_work(self) -> None:
        combined = "\n".join(read_plans().values())
        lowered = combined.lower()

        required_boundaries = [
            "no mandate data",
            "no live portal writes",
            "no real grundbuch/register actions",
            "no customer mail dispatch",
            "without a separate owner gate",
        ]
        for boundary in required_boundaries:
            self.assertIn(boundary, lowered)

        self.assertNotIn("read secret value", lowered)
        self.assertNotIn("apply without approval", lowered)


if __name__ == "__main__":
    unittest.main()
