from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class ReleaseLaneContextMemoryTests(unittest.TestCase):
    def test_release_memory_points_to_context_pack_and_dev_ocid_boundary(self) -> None:
        skill = read("workflows/skills/nac-release-memory/SKILL.md")
        reference = read("workflows/skills/nac-release-memory/references/release-lane.md")

        for content in (skill, reference):
            self.assertIn(
                "/home/ubuntu/src/oci-landing-zone/runbooks/release-lane-context.dev.json",
                content,
            )
            self.assertIn("dev-only nicht-sensitive OCIDs", content)
            self.assertIn("User-, Tenancy-, Vault-Secret-, KMS-Key- und Certificate-OCIDs", content)
            self.assertIn("Resource Manager outputs", content)


if __name__ == "__main__":
    unittest.main()
