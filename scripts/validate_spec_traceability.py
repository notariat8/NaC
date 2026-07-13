from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CONTRACT_PATH = Path("workflows/contracts/spec-traceability.contract.json")
PROCESS_POLICY_PATH = Path("policies/process-policy.yaml")
SPEC_ROOTS = (
    Path("docs/de/superpowers/specs"),
    Path("docs/en/superpowers/specs"),
)
TEMPLATE_PATHS = (
    Path(".github/ISSUE_TEMPLATE/bug_report.md"),
    Path(".github/ISSUE_TEMPLATE/compliance_change.md"),
    Path(".github/ISSUE_TEMPLATE/feature_request.md"),
    Path(".github/ISSUE_TEMPLATE/process_release.md"),
    Path(".github/PULL_REQUEST_TEMPLATE.md"),
)
GIT_EXECUTABLE = os.environ.get("GIT_EXECUTABLE") or shutil.which("git") or "git"
REQUIRED_CONTRACT_FIELDS = [
    "schema_version",
    "spec_id",
    "leading_issue",
    "risk_gate",
    "delivery_mode",
    "acceptance_ids",
    "validation_commands",
]
REQUIRED_TEMPLATE_MARKERS = (
    "## Spec-Traceability",
    "Spec:",
    "Plan:",
    "Akzeptanzkriterien:",
    "AC-IDs:",
    "Test-/Validator-Nachweis:",
)


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [os.environ.get("GIT_EXECUTABLE") or GIT_EXECUTABLE, *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def changed_files() -> list[str]:
    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        run_git(["fetch", "--no-tags", "origin", base_ref])
        diff = run_git(["diff", "--name-only", f"origin/{base_ref}...HEAD"])
    else:
        diff = run_git(["diff", "--name-only", "HEAD"])

    if diff.returncode != 0:
        print("ERROR: Konnte geänderte Spec-Dateien nicht bestimmen.")
        print(diff.stderr.strip())
        return []

    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    if untracked.returncode != 0:
        print("ERROR: Konnte ungetrackte Spec-Dateien nicht bestimmen.")
        print(untracked.stderr.strip())
        return []

    files = {
        line.strip()
        for output in (diff.stdout, untracked.stdout)
        for line in output.splitlines()
        if line.strip()
    }
    return sorted(files)


def is_direct_spec_markdown_path(path: str) -> bool:
    relative_path = Path(path)
    return relative_path.suffix == ".md" and relative_path.parent in SPEC_ROOTS


def strip_yaml_inline_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
            continue
        if char in {'"', "'"}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            continue
        if char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value


def parse_simple_yaml_scalar(value: str) -> object:
    value = strip_yaml_inline_comment(value).strip()
    if value in {"true", "false"}:
        return value == "true"
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_simple_yaml_block(
    lines: list[tuple[int, str]], index: int, indent: int
) -> tuple[object, int]:
    if index >= len(lines):
        return {}, index

    if lines[index][1].startswith("- "):
        items: list[object] = []
        while index < len(lines):
            line_indent, content = lines[index]
            if line_indent != indent or not content.startswith("- "):
                break
            items.append(parse_simple_yaml_scalar(content[2:]))
            index += 1
        return items, index

    mapping: dict[str, object] = {}
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            index += 1
            continue
        if content.startswith("- "):
            break
        if ":" not in content:
            index += 1
            continue

        key, value = content.split(":", 1)
        key = key.strip()
        value = strip_yaml_inline_comment(value).strip()
        index += 1
        if value:
            mapping[key] = parse_simple_yaml_scalar(value)
            continue

        if index < len(lines) and lines[index][0] > line_indent:
            child, index = parse_simple_yaml_block(lines, index, lines[index][0])
            mapping[key] = child
        else:
            mapping[key] = {}

    return mapping, index


def load_simple_yaml_mapping(path: Path) -> dict[str, object]:
    lines: list[tuple[int, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line.strip()))

    parsed, _ = parse_simple_yaml_block(lines, 0, lines[0][0] if lines else 0)
    return parsed if isinstance(parsed, dict) else {}


def parse_manifest_text(text: str) -> dict[str, object]:
    lines: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line.strip()))
    parsed, _ = parse_simple_yaml_block(lines, 0, lines[0][0] if lines else 0)
    return parsed if isinstance(parsed, dict) else {}


def extract_manifest_blocks(text: str) -> tuple[list[dict[str, object]], str]:
    blocks: list[dict[str, object]] = []
    retained: list[str] = []
    in_block = False
    block_lines: list[str] = []

    for line in text.splitlines():
        if line.strip() == "```nac-spec-traceability":
            in_block = True
            block_lines = []
            continue
        if in_block and line.strip() == "```":
            blocks.append(parse_manifest_text("\n".join(block_lines)))
            in_block = False
            block_lines = []
            continue
        if in_block:
            block_lines.append(line)
            continue
        retained.append(line)

    return blocks, "\n".join(retained)


def validate_required_list(
    errors: list[str],
    *,
    path_label: str,
    field: str,
    actual: object,
) -> None:
    if not isinstance(actual, list) or not actual:
        errors.append(f"Pflichtliste fehlt im Spec-Manifest: {path_label} {field}")
        return
    if not all(isinstance(item, str) and item.strip() for item in actual):
        errors.append(f"Pflichtliste enthält leere Werte: {path_label} {field}")


def validate_contract_file() -> list[str]:
    errors: list[str] = []
    path = REPO_ROOT / CONTRACT_PATH
    if not path.exists():
        return [f"Pflichtvertrag fehlt: {CONTRACT_PATH}"]

    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Pflichtvertrag ist kein gültiges JSON: {CONTRACT_PATH} {exc}"]

    if contract.get("schema_version") != "nac.spec-traceability/v0.1":
        errors.append("Pflichtwert fehlt in Spec-Traceability-Vertrag: schema_version")
    if contract.get("required_manifest_fields") != REQUIRED_CONTRACT_FIELDS:
        errors.append(
            "Pflichtwert fehlt in Spec-Traceability-Vertrag: required_manifest_fields"
        )
    examples = contract.get("acceptance_id_pattern_examples")
    if not isinstance(examples, list) or "AC-001" not in examples:
        errors.append(
            "Pflichtwert fehlt in Spec-Traceability-Vertrag: acceptance_id_pattern_examples.AC-001"
        )
    return errors


def validate_process_policy_file() -> list[str]:
    errors: list[str] = []
    path = REPO_ROOT / PROCESS_POLICY_PATH
    if not path.exists():
        return [f"Pflichtdatei fehlt: {PROCESS_POLICY_PATH}"]

    policy = load_simple_yaml_mapping(path)
    spec_traceability = policy.get("spec_traceability")
    if not isinstance(spec_traceability, dict):
        return ["Pflichtabschnitt fehlt in process-policy: spec_traceability"]

    expected_true_keys = (
        "enabled",
        "require_acceptance_ids_for_nontrivial_specs",
        "require_validation_commands_for_nontrivial_specs",
        "allow_historical_specs_without_manifest",
    )
    for key in expected_true_keys:
        if spec_traceability.get(key) is not True:
            errors.append(f"Pflichtwert fehlt in process-policy: spec_traceability.{key}.true")

    if spec_traceability.get("contract") != CONTRACT_PATH.as_posix():
        errors.append("Pflichtwert fehlt in process-policy: spec_traceability.contract")

    enforced_by = spec_traceability.get("enforced_by")
    if (
        not isinstance(enforced_by, list)
        or "scripts/validate_spec_traceability.py" not in enforced_by
    ):
        errors.append(
            "Pflichtwert fehlt in process-policy: "
            "spec_traceability.enforced_by.scripts/validate_spec_traceability.py"
        )
    return errors


def validate_templates() -> list[str]:
    errors: list[str] = []
    for relative_path in TEMPLATE_PATHS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"Pflichttemplate fehlt: {relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in REQUIRED_TEMPLATE_MARKERS:
            if marker not in text:
                errors.append(f"Pflichtmarker fehlt in Template: {relative_path} {marker}")
    return errors


def validate_one_manifest(
    manifest: dict[str, object],
    *,
    body_text: str,
    path_label: str,
) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_CONTRACT_FIELDS:
        if field not in manifest:
            errors.append(f"Pflichtfeld fehlt im Spec-Manifest: {path_label} {field}")

    if manifest.get("schema_version") != "nac.spec-traceability/v0.1":
        errors.append(f"Falsche schema_version im Spec-Manifest: {path_label}")

    for scalar_field in ("spec_id", "leading_issue", "risk_gate", "delivery_mode"):
        value = manifest.get(scalar_field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Pflichtfeld leer im Spec-Manifest: {path_label} {scalar_field}")

    acceptance_ids = manifest.get("acceptance_ids")
    validate_required_list(
        errors,
        path_label=path_label,
        field="acceptance_ids",
        actual=acceptance_ids,
    )
    validation_commands = manifest.get("validation_commands")
    validate_required_list(
        errors,
        path_label=path_label,
        field="validation_commands",
        actual=validation_commands,
    )
    if isinstance(validation_commands, list):
        for command in validation_commands:
            if isinstance(command, str) and ("\\n" in command or "\n" in command):
                errors.append(
                    f"Validierungsbefehl enthält Zeilenumbruch: {path_label}"
                )


    if isinstance(acceptance_ids, list):
        for acceptance_id in acceptance_ids:
            if not isinstance(acceptance_id, str):
                continue
            if not acceptance_id.startswith("AC-"):
                errors.append(
                    f"Akzeptanz-ID nutzt nicht das AC-Präfix: {path_label} {acceptance_id}"
                )
                continue
            if acceptance_id not in body_text:
                errors.append(
                    f"Akzeptanz-ID aus Manifest fehlt im Spec-Text: {path_label} {acceptance_id}"
                )
    return errors


def validate_manifest_blocks() -> list[str]:
    errors: list[str] = []
    for root in SPEC_ROOTS:
        absolute_root = REPO_ROOT / root
        if not absolute_root.exists():
            continue
        for path in sorted(absolute_root.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            blocks, body_text = extract_manifest_blocks(text)
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            for manifest in blocks:
                errors.extend(
                    validate_one_manifest(
                        manifest,
                        body_text=body_text,
                        path_label=relative_path,
                    )
                )
    return errors


def validate_changed_spec_manifests() -> list[str]:
    errors: list[str] = []
    for relative_path in changed_files():
        if not is_direct_spec_markdown_path(relative_path):
            continue

        path = REPO_ROOT / relative_path
        if not path.exists():
            continue

        text = path.read_text(encoding="utf-8")
        blocks, _ = extract_manifest_blocks(text)
        if not blocks:
            errors.append(
                "Spec-Datei ohne nac-spec-traceability-Manifest geändert: "
                f"{relative_path}"
            )
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(validate_contract_file())
    errors.extend(validate_process_policy_file())
    errors.extend(validate_templates())
    errors.extend(validate_manifest_blocks())
    errors.extend(validate_changed_spec_manifests())

    if errors:
        print("STATUS: FAILED")
        for entry in errors:
            print(f"ERROR: {entry}")
        return 1

    print("STATUS: PASSED")
    print("OK: Spec-Traceability-Vertrag, Templates und Manifest-Blöcke sind gültig.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
