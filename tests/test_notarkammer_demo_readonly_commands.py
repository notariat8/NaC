import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_DOCS = sorted((ROOT / "docs" / "de" / "demo").glob("*.md")) + sorted(
    (ROOT / "docs" / "en" / "demo").glob("*.md")
)


def fenced_blocks(text):
    in_block = False
    block = []
    for line in text.splitlines():
        if line.startswith("```"):
            if in_block:
                yield "\n".join(block)
                block = []
                in_block = False
            else:
                in_block = True
            continue
        if in_block:
            block.append(line)


class NotarkammerDemoReadonlyCommandTests(unittest.TestCase):
    def test_preflight_docs_state_command_safety_boundary(self):
        german = (ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-preflight.md").read_text(
            encoding="utf-8"
        )
        english = (ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-preflight.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Befehlssicherheit", german)
        self.assertIn("nur vorbereiten oder lesen", german)
        self.assertIn("Command safety", english)
        self.assertIn("prepare or read only", english)

    def test_demo_command_blocks_do_not_contain_write_operations(self):
        forbidden_patterns = [
            re.compile(r"\bcurl\b.*\s-X\s*POST\b", re.IGNORECASE),
            re.compile(r"\boci\s+", re.IGNORECASE),
            re.compile(r"\bterraform\s+apply\b", re.IGNORECASE),
        ]

        for doc in DEMO_DOCS:
            text = doc.read_text(encoding="utf-8")
            for block in fenced_blocks(text):
                for pattern in forbidden_patterns:
                    self.assertIsNone(pattern.search(block), f"{doc} contains executable write command: {pattern.pattern}")

    def test_apply_request_examples_are_dry_run_only(self):
        for doc in DEMO_DOCS:
            for line in doc.read_text(encoding="utf-8").splitlines():
                if "python scripts/nac.py tenant apply-request" in line:
                    self.assertIn("--dry-run", line, f"{doc} apply-request example must remain dry-run only")

    def test_post_mentions_are_warning_text_not_executable_examples(self):
        for doc in DEMO_DOCS:
            for line in doc.read_text(encoding="utf-8").splitlines():
                if "POST /" not in line:
                    continue
                self.assertRegex(
                    line,
                    r"(Nicht ausführen|Do not execute|nicht ausführen|run no POST|Keine Admin-Review-POSTs ausführen)",
                    f"{doc} POST mention must be warning text only",
                )


if __name__ == "__main__":
    unittest.main()
