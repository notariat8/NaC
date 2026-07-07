from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOC_MARKERS: dict[str, tuple[str, ...]] = {
    "docs/de/operations/m365-mcp-batch-approval.md": (
        "## MVP-Go/No-Go-Abnahmekriterium",
        "`batch-approval m365 --batch-mode release-gate` rendert den",
        "MVP-Go/No-Go-Standard standardmäßig",
        "Der eingebettete `release-gate-run` rendert denselben MVP-Go/No-Go-Standard",
        "`release-readiness` ist das verbindliche MVP-Go/No-Go-Abnahmekriterium",
        "`mvp_release_readiness=READY`",
        "`release_gate_readiness=READY`",
        "--release-gate-write-audit-pack",
        "--release-gate-write-readiness",
        "--release-gate-readiness-require-audit-pack",
        "Keine MVP-Freigabe erfolgt nur auf Basis",
    ),
    "docs/en/operations/m365-mcp-batch-approval.md": (
        "## MVP Go/No-Go Acceptance Criterion",
        "`batch-approval m365 --batch-mode release-gate` renders the MVP Go/No-Go",
        "standard by default",
        "The embedded `release-gate-run` renders the same MVP Go/No-Go standard",
        "`release-readiness` is the binding MVP Go/No-Go acceptance criterion",
        "`mvp_release_readiness=READY`",
        "`release_gate_readiness=READY`",
        "--release-gate-write-audit-pack",
        "--release-gate-write-readiness",
        "--release-gate-readiness-require-audit-pack",
        "No MVP approval is based only on",
    ),
    "docs/de/operations/release-checklist.md": (
        "Für M365-MVP-Laufzeitfreigaben",
        "`release-readiness` als Go/No-Go-Nachweis",
        "`mvp_release_readiness=READY`",
        "`release_gate_readiness=READY`",
    ),
    "docs/en/operations/release-checklist.md": (
        "For M365 MVP runtime approvals",
        "`release-readiness` as Go/No-Go evidence",
        "`mvp_release_readiness=READY`",
        "`release_gate_readiness=READY`",
    ),
    "docs/de/cli.md": (
        "release-readiness --format json",
        "release-gate-write-readiness",
        "release-gate-readiness-require-audit-pack",
        "release_gate_readiness=READY",
    ),
    "docs/en/cli.md": (
        "release-readiness --format json",
        "release-gate-write-readiness",
        "release-gate-readiness-require-audit-pack",
        "release_gate_readiness=READY",
    ),
    "docs/de/runbooks/m365-cli-admin-accelerator.md": (
        "rendert standardmäßig den MVP-Go/No-Go-Lauf",
        "--release-gate-readiness-require-audit-pack",
        "--release-gate-compare-left <baseline-correlation-id>",
    ),
    "docs/en/runbooks/m365-cli-admin-accelerator.md": (
        "renders the MVP Go/No-Go run by default",
        "--release-gate-readiness-require-audit-pack",
        "--release-gate-compare-left <baseline-correlation-id>",
    ),
}

REQUIRED_BATCH_APPROVAL_MARKERS: dict[str, tuple[str, ...]] = {
    "src/nac_cli/cli.py": (
        "_apply_m365_release_gate_mvp_defaults",
        "_m365_release_gate_run_readiness_audit_pack_dir",
        '"release-gate", "runtime-certificate-rotation"',
        "return (True, True, True)",
        "MVP-Standard impliziert",
    ),
    "tests/test_m365_batch_approval_cli.py": (
        "test_batch_approval_renders_runtime_release_gate_with_mvp_readiness_default",
        "test_batch_approval_release_gate_baseline_uses_mvp_audit_pack_default",
        "release_gate_readiness_require_audit_pack",
    ),
}

REQUIRED_QUALITY_GATE_MARKERS = (
    "m365_release_readiness_gate",
    "M365 Release Readiness Gate",
    "scripts/validate_m365_release_readiness_gate.py",
    "m365_release_readiness_report_lines",
    "mvp_release_readiness=READY",
    "release_gate_readiness=READY",
)

REQUIRED_REPORT_SURFACE_MARKERS: dict[str, tuple[str, ...]] = {
    "scripts/render_quality_gate_comment.py": (
        "### M365 MVP Readiness",
        "mvp_release_readiness=READY",
        "release_gate_readiness=READY",
        "release-gate-write-audit-pack",
        "release-gate-write-readiness",
        "release-gate-readiness-require-audit-pack",
    ),
    "docs/de/quality-gate.md": (
        "M365-MVP-Readiness-Status",
        "`mvp_release_readiness=READY`",
        "`release_gate_readiness=READY`",
    ),
    "docs/en/quality-gate.md": (
        "M365 MVP readiness status",
        "`mvp_release_readiness=READY`",
        "`release_gate_readiness=READY`",
    ),
}

PROHIBITED_MARKERS = (
    "BEGIN PRIVATE KEY",
    "client_secret",
    "password=",
)


def validate(repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    for relative_path, markers in REQUIRED_DOC_MARKERS.items():
        _validate_required_markers(repo_root / relative_path, markers, errors)
    for relative_path, markers in REQUIRED_BATCH_APPROVAL_MARKERS.items():
        _validate_required_markers(repo_root / relative_path, markers, errors)
    _validate_required_markers(repo_root / "scripts" / "quality_gate.py", REQUIRED_QUALITY_GATE_MARKERS, errors)
    for relative_path, markers in REQUIRED_REPORT_SURFACE_MARKERS.items():
        _validate_required_markers(repo_root / relative_path, markers, errors)
    return errors


def _validate_required_markers(path: Path, markers: tuple[str, ...], errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing file: {_display_path(path)}")
        return
    text = path.read_text(encoding="utf-8")
    _reject_prohibited_markers(path, text, errors)
    for marker in markers:
        if marker not in text:
            errors.append(f"{_display_path(path)} missing marker {marker}")


def _reject_prohibited_markers(path: Path, text: str, errors: list[str]) -> None:
    for marker in PROHIBITED_MARKERS:
        if marker in text:
            errors.append(f"{_display_path(path)} contains prohibited marker {marker}")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("STATUS: PASSED")
    print("M365 release readiness gate is enforced in docs and strict quality gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
