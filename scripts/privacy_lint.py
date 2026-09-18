from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_GLOBS = (
    ".agents/plugins/*.json",
    "docs/**/*.md",
    "plugins/**/*.json",
    "plugins/**/*.md",
    "processes/**/*.json",
    "prompts/**/*.md",
    "policies/**/*.yaml",
    "tests/test_activation_security_windows.py",
)

EMAIL_PATTERN = re.compile(r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
SECRET_PATTERN = re.compile(
    r"(?i)(ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|api[_-]?key\s*[:=]|client[_-]?secret\s*[:=]|BEGIN PRIVATE KEY)"
)
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)

ALLOWED_EMAIL_DOMAINS = {
    "example",
    "example.com",
    "example.org",
    "example.net",
}

SYNTHETIC_IDENTITY_FIXTURE_UUIDS = {
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
}

SYNTHETIC_IDENTITY_FIXTURE_FILES = {
    Path("tests/test_activation_security_windows.py"),
}

EXCLUDE_FILES = {
    "LICENSE",
}


def iter_files() -> list[Path]:
    files: list[Path] = []
    for pattern in SCAN_GLOBS:
        files.extend(REPO_ROOT.glob(pattern))
    return sorted({f for f in files if f.is_file() and f.name not in EXCLUDE_FILES})


def main() -> int:
    violations: list[str] = []
    for file_path in iter_files():
        text = file_path.read_text(encoding="utf-8", errors="ignore")

        if SECRET_PATTERN.search(text):
            violations.append(f"{file_path.relative_to(REPO_ROOT)}: moegliches Secret-Muster gefunden")

        for match in EMAIL_PATTERN.finditer(text):
            domain = match.group(2).lower()
            if not _is_allowed_example_domain(domain):
                violations.append(
                    f"{file_path.relative_to(REPO_ROOT)}: E-Mail-Domain {domain!r} ist nicht als Testdomain erlaubt"
                )

        relative_path = file_path.relative_to(REPO_ROOT)
        if relative_path in SYNTHETIC_IDENTITY_FIXTURE_FILES:
            for match in UUID_PATTERN.finditer(text):
                if match.group(0).lower() not in SYNTHETIC_IDENTITY_FIXTURE_UUIDS:
                    violations.append(
                        f"{relative_path}: nicht-synthetische Identity-UUID im Windows-Sicherheitsfixture"
                    )

    if violations:
        print("Privacy lint failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Privacy lint passed.")
    return 0


def _is_allowed_example_domain(domain: str) -> bool:
    return domain in ALLOWED_EMAIL_DOMAINS or domain.endswith(".example")


if __name__ == "__main__":
    raise SystemExit(main())
