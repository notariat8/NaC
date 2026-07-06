from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class ReleaseLaneContextMemoryTests(unittest.TestCase):
    def test_release_memory_is_archived_but_keeps_context_pack_boundary(self) -> None:
        process_policy = read("policies/process-policy.yaml")
        skill = read("workflows/skills/nac-release-memory/SKILL.md")
        reference = read("workflows/skills/nac-release-memory/references/release-lane.md")

        self.assertIn("status: archived_legacy_oci_release_lane", process_policy)
        self.assertIn("enabled: false", process_policy)
        self.assertIn("require_before_oci_release_work: false", process_policy)

        for content in (skill, reference):
            self.assertIn("archivierter Legacy-Pfad", content)
            self.assertIn(
                "/home/ubuntu/src/oci-landing-zone/runbooks/release-lane-context.dev.json",
                content,
            )
            self.assertIn("dev-only nicht-sensitive OCIDs", content)
            self.assertIn("User-, Tenancy-, Vault-Secret-, KMS-Key- und Certificate-OCIDs", content)
            self.assertIn("Resource Manager outputs", content)


if __name__ == "__main__":
    unittest.main()
