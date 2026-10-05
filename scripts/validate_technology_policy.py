from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath, PureWindowsPath


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_RUNTIME_POLICY = ("approved_stack", "process_logic", "python_runtime_selection")
PYTHON_RUNTIME_MIRROR_FILES = (
    "AGENTS.md",
    "docs/de/START_HERE.md",
    "docs/en/START_HERE.md",
    "docs/de/minimum-requirements.md",
    "docs/en/minimum-requirements.md",
    ".pi/README.md",
) + tuple(
    f"{directory}/nac-{name}.{extension}"
    for directory, extension in ((".codex/agents", "toml"), (".pi/agents", "md"))
    for name in (
        "scope-mapper", "policy-reviewer", "docs-parity-reviewer",
        "validation-reviewer", "kg-reviewer", "bpmn-reviewer",
    )
)

EXPECTED_SCALARS = {
    ("approved_stack", "documentation", "canonical_format"): "markdown",
    ("approved_stack", "documentation", "export", "pdf"): "pandoc",
    ("approved_stack", "documentation", "export", "assets"): "svg_png",
    ("approved_stack", "process_logic", "execution_language"): "python",
    ("approved_stack", "process_logic", "approach"): "model_first",
    ("approved_stack", "process_logic", "operating_surface"): "nac_cli",
    ("approved_stack", "process_logic", "cli_entrypoint"): "nac",
    ("approved_stack", "process_logic", "cli_wrapper"): "scripts/nac.py",
    ("approved_stack", "visualization", "canonical_business_model"): "bpmn_2_0",
    ("approved_stack", "visualization", "canonical_source_format"): "bpmn_xml",
    ("approved_stack", "visualization", "canonical_directory"): "bpmn/",
    ("approved_stack", "visualization", "visual_editor"): "bpmn_js",
    ("approved_stack", "visualization", "model_extension"): "bpmn/nac-moddle.json",
    ("approved_stack", "visualization", "validator"): "scripts/validate_bpmn_models.py",
    ("approved_stack", "visualization", "allowed_overview_format"): "mermaid",
    ("repository_constraints", "active_ai_ide"): "codex",
    PYTHON_RUNTIME_POLICY + ("scope",): "local_agent_checks",
    PYTHON_RUNTIME_POLICY + ("codex_desktop_preferred",): "tool_discovered_bundled_python",
    PYTHON_RUNTIME_POLICY + ("discovery_tool",): "load_workspace_dependencies",
    PYTHON_RUNTIME_POLICY + ("explicit_project_environment",): "takes_precedence",
    PYTHON_RUNTIME_POLICY + ("other_environments",): "verified_project_or_system_python",
    PYTHON_RUNTIME_POLICY + ("executable_binding",): "absolute_path",
    PYTHON_RUNTIME_POLICY + ("minimum_version",): "3.11",
    PYTHON_RUNTIME_POLICY + ("smoke_test",): "version_and_required_imports",
}

EXPECTED_TRUE_KEYS = (
    ("repository_constraints", "enforce_codex_agent_sync"),
    PYTHON_RUNTIME_POLICY + ("keep_selected_runtime",),
    PYTHON_RUNTIME_POLICY + ("preserve_dependency_constraints",),
)

EXPECTED_FALSE_KEYS = (
    ("repository_constraints", "cursor_workspace_files_allowed"),
    ("repository_constraints", "github_copilot_workspace_files_allowed"),
    PYTHON_RUNTIME_POLICY + ("retry_broken_path_python",),
    PYTHON_RUNTIME_POLICY + ("mutate_global_python_or_path",),
    PYTHON_RUNTIME_POLICY + ("auto_install_runtime_or_packages",),
    PYTHON_RUNTIME_POLICY + ("change_ci_or_release_runtime",),
)

EXPECTED_LISTS = {
    ("approved_stack", "visualization", "disallowed_for_bpmn_source"): (
        "mermaid",
        "plantuml",
    ),
    ("repository_constraints", "required_sync_targets"): (
        "AGENTS.md",
        ".codex/agents",
        "docs/de/START_HERE.md",
        "docs/en/START_HERE.md",
        "policies/language-policy.yaml",
    ),
}

IGNORED_DIRECTORY_NAMES = {
    ".cache",
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "cache",
    "dist",
    "env",
    "generated",
    "node_modules",
    "out",
    "tmp",
    "venv",
}

ASCIIDOC_SUFFIXES = {".adoc", ".asciidoc"}
BPMN_DISALLOWED_SUFFIXES = {".mmd", ".mermaid", ".puml", ".plantuml"}


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
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {'"', "'"}
    ):
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
    if isinstance(parsed, dict):
        return parsed
    return {}


def get_nested(mapping: dict[str, object], keys: tuple[str, ...]) -> object:
    current: object = mapping
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def dotted(keys: tuple[str, ...]) -> str:
    return ".".join(keys)


def relative_posix(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            dirname
            for dirname in dirnames
            if dirname not in IGNORED_DIRECTORY_NAMES
        )
        for filename in sorted(filenames):
            files.append(Path(dirpath) / filename)
    return files


def validate_policy_structure(root: Path) -> list[str]:
    errors: list[str] = []
    policy_path = root / "policies" / "technology-policy.yaml"
    if not policy_path.exists():
        return ["Pflichtdatei fehlt: policies/technology-policy.yaml"]

    policy = load_simple_yaml_mapping(policy_path)
    for keys, expected in EXPECTED_SCALARS.items():
        if get_nested(policy, keys) != expected:
            errors.append(
                "Pflichtwert fehlt in technology-policy: "
                f"{dotted(keys)}.{expected}"
            )

    for keys in EXPECTED_TRUE_KEYS:
        if get_nested(policy, keys) is not True:
            errors.append(
                "Pflichtwert fehlt in technology-policy: "
                f"{dotted(keys)}.true"
            )

    for keys in EXPECTED_FALSE_KEYS:
        if get_nested(policy, keys) is not False:
            errors.append(
                "Pflichtwert fehlt in technology-policy: "
                f"{dotted(keys)}.false"
            )

    for keys, expected_values in EXPECTED_LISTS.items():
        actual = get_nested(policy, keys)
        if not isinstance(actual, list):
            errors.append(f"Pflichtabschnitt fehlt in technology-policy: {dotted(keys)}")
            continue
        for expected in expected_values:
            if expected not in actual:
                errors.append(
                    "Pflichtwert fehlt in technology-policy: "
                    f"{dotted(keys)}.{expected}"
                )

    return errors


def validate_required_sync_targets(root: Path) -> list[str]:
    errors: list[str] = []
    policy_path = root / "policies" / "technology-policy.yaml"
    if not policy_path.exists():
        return []

    policy = load_simple_yaml_mapping(policy_path)
    sync_targets = get_nested(policy, ("repository_constraints", "required_sync_targets"))
    if not isinstance(sync_targets, list):
        return ["Pflichtabschnitt fehlt in technology-policy: repository_constraints.required_sync_targets"]

    for rel_path in sync_targets:
        if not isinstance(rel_path, str):
            errors.append("Pflichtziel fuer Codex-Agent-Sync ist kein Pfad-String")
            continue
        target = Path(rel_path)
        normalized_parts = PurePosixPath(rel_path.replace("\\", "/")).parts
        if (
            target.is_absolute()
            or PurePosixPath(rel_path).is_absolute()
            or PureWindowsPath(rel_path).is_absolute()
            or ".." in normalized_parts
        ):
            errors.append(
                "Codex-Agent-Sync-Ziel muss relativer Repo-Pfad innerhalb des Repos sein: "
                f"{rel_path}"
            )
            continue
        if not (root / target).exists():
            errors.append(f"Pflichtziel fuer Codex-Agent-Sync fehlt: {rel_path}")
    return errors


def validate_python_runtime_mirrors(root: Path) -> list[str]:
    """Check instruction parity only; do not discover or launch local runtimes."""
    if not (root / "policies/technology-policy.yaml").is_file():
        return []
    errors: list[str] = []
    for rel_path in PYTHON_RUNTIME_MIRROR_FILES:
        path = root / rel_path
        if not path.is_file():
            errors.append(f"Python-Laufzeitspiegel fehlt: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        if not all(marker in text for marker in (
            "policies/technology-policy.yaml",
            "python_runtime_selection",
            "load_workspace_dependencies",
        )):
            errors.append(f"Python-Laufzeitregel fehlt im Spiegel: {rel_path}")
    return errors


def validate_forbidden_formats(root: Path) -> list[str]:
    errors: list[str] = []
    for path in iter_files(root):
        suffix = path.suffix.lower()
        rel_path = relative_posix(root, path)
        if suffix in ASCIIDOC_SUFFIXES:
            errors.append(
                "Manuell gepflegte AsciiDoc-Quelle ist nicht erlaubt: "
                f"{rel_path}"
            )

    bpmn_root = root / "bpmn"
    if bpmn_root.exists():
        for path in iter_files(bpmn_root):
            if path.suffix.lower() in BPMN_DISALLOWED_SUFFIXES:
                errors.append(
                    "BPMN-Quellen muessen BPMN XML bleiben, nicht Mermaid/PlantUML: "
                    f"{relative_posix(root, path)}"
                )
    return errors


def validate_codex_only_workspace(root: Path) -> list[str]:
    errors: list[str] = []
    forbidden_paths = (
        ".cursor",
        ".github/copilot-instructions.md",
        ".github/copilot-instructions.yml",
        ".github/copilot-instructions.yaml",
    )
    for rel_path in forbidden_paths:
        if (root / rel_path).exists():
            errors.append(f"Codex-only Workspace darf kein {rel_path} enthalten")
    return errors


def validate(repo_root: Path = REPO_ROOT) -> list[str]:
    root = repo_root.resolve()
    errors = validate_policy_structure(root)
    errors.extend(validate_required_sync_targets(root))
    errors.extend(validate_python_runtime_mirrors(root))
    errors.extend(validate_forbidden_formats(root))
    errors.extend(validate_codex_only_workspace(root))
    return sorted(errors)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validiert den verbindlichen NaC-Technologie-Policy-Stack."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository-Wurzel fuer die Validierung.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate(args.repo_root)
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: Technology-Policy-Struktur, Codex-Agent-Sync und Dateiformate stimmen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
