from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PrivacyAndCompletionGovernanceTest(unittest.TestCase):
    def test_secret_scan_uses_runnable_pinned_gitleaks_cli(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "privacy-and-secrets.yml").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("gitleaks/gitleaks-action@v2", workflow)
        self.assertIn('GITLEAKS_VERSION: "8.30.1"', workflow)
        self.assertIn("GITLEAKS_SHA256:", workflow)
        self.assertIn("sha256sum -c -", workflow)
        self.assertIn("gitleaks git --redact --verbose", workflow)

    def test_completion_rules_require_remote_ci_checks_after_push(self) -> None:
        required_markers = (
            "remote_ci_checks",
            "Privacy and Secrets Guard / secret-scan",
            "Privacy and Secrets Guard / privacy-lint",
            "NaC Quality Gate / quality-gate",
        )
        files = (
            "policies/process-policy.yaml",
            "AGENTS.md",
            "docs/de/regelarchitektur.md",
            "docs/en/regelarchitektur.md",
        )

        for rel_path in files:
            text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            with self.subTest(path=rel_path):
                for marker in required_markers:
                    self.assertIn(marker, text)

    def test_data_protection_policy_requires_runnable_secret_scanning_ci(self) -> None:
        policy = (REPO_ROOT / "policies" / "data-protection-policy.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("secret_scanning_ci:", policy)
        self.assertIn("must_run_without_unconfigured_commercial_license: true", policy)
        self.assertIn("require_checksum_for_downloaded_binary: true", policy)


if __name__ == "__main__":
    unittest.main()
