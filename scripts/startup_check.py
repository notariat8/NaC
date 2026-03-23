from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REQ_FILE = REPO_ROOT / "policies" / "startup-requirements.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Startup verification for local IDE/tooling setup.")
    parser.add_argument("--ide", choices=["auto", "cursor", "vscode"], default="auto")
    parser.add_argument("--run-tests", action="store_true")
    return parser.parse_args()


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    """
    Minimal parser fuer den aktuell verwendeten, einfachen YAML-Stil.
    Nutzt absichtlich keine externen Dependencies.
    """
    data: dict[str, Any] = {}
    current_list_key: str | None = None
    current_map_key: str | None = None
    current_map: dict[str, Any] = {}

    lines = path.read_text(encoding="utf-8").splitlines()
    for raw in lines:
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        if line.startswith("  - ") and current_list_key:
            data[current_list_key].append(line[4:].strip())
            continue

        if line.startswith("  ") and current_map_key and ":" in line:
            key, value = line.strip().split(":", 1)
            current_map[key.strip()] = value.strip().strip('"')
            data[current_map_key] = current_map
            continue

        current_list_key = None
        current_map_key = None
        current_map = {}

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value == "":
            # list oder map startet
            if key.endswith("_commands") or key.endswith("_files") or key.endswith("_required"):
                data[key] = []
                current_list_key = key
            else:
                data[key] = {}
                current_map_key = key
                current_map = {}
        else:
            data[key] = value.strip('"')

    return data


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def get_python_version() -> tuple[int, int]:
    return sys.version_info.major, sys.version_info.minor


def parse_version(text: str) -> tuple[int, int]:
    major, minor = text.split(".", 1)
    return int(major), int(minor)


def check_vscode_extensions(required_extensions: list[str]) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    ok: list[str] = []

    if not command_exists("code"):
        warnings.append("VS Code CLI `code` nicht gefunden, Extension-Check uebersprungen.")
        return ok, warnings, errors

    try:
        result = subprocess.run(
            ["code", "--list-extensions"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        warnings.append("VS Code CLI konnte trotz PATH-Eintrag nicht gestartet werden.")
        return ok, warnings, errors
    if result.returncode != 0:
        warnings.append("Konnte VS Code Extensions nicht auslesen.")
        return ok, warnings, errors

    installed = {line.strip().lower() for line in result.stdout.splitlines() if line.strip()}
    for extension in required_extensions:
        if extension.lower() in installed:
            ok.append(f"VS Code Extension vorhanden: {extension}")
        else:
            errors.append(f"VS Code Extension fehlt: {extension}")

    return ok, warnings, errors


def main() -> int:
    args = parse_args()
    requirements = parse_simple_yaml(REQ_FILE)

    ok: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    for command in requirements.get("required_commands", []):
        if command_exists(command):
            ok.append(f"Command vorhanden: {command}")
        else:
            errors.append(f"Command fehlt: {command}")

    for command in requirements.get("recommended_commands", []):
        if command_exists(command):
            ok.append(f"Empfohlener Command vorhanden: {command}")
        else:
            warnings.append(f"Empfohlener Command fehlt: {command}")

    py_major, py_minor = get_python_version()
    min_version = requirements.get("python", {}).get("min_version", "3.11")
    min_major, min_minor = parse_version(min_version)
    if (py_major, py_minor) >= (min_major, min_minor):
        ok.append(f"Python-Version ok: {py_major}.{py_minor}")
    else:
        errors.append(f"Python-Version zu alt: {py_major}.{py_minor}, benoetigt >= {min_version}")

    for rel_path in requirements.get("required_files", []):
        if (REPO_ROOT / rel_path).exists():
            ok.append(f"Datei vorhanden: {rel_path}")
        else:
            errors.append(f"Datei fehlt: {rel_path}")

    ide_mode = args.ide
    if ide_mode == "vscode" or (ide_mode == "auto" and command_exists("code")):
        ext_ok, ext_warn, ext_err = check_vscode_extensions(
            requirements.get("vscode_extensions_required", [])
        )
        ok.extend(ext_ok)
        warnings.extend(ext_warn)
        errors.extend(ext_err)

    if args.run_tests:
        validate = subprocess.run(
            [sys.executable, "-m", "business_os", "validate-all", "--repo-root", "."],
            cwd=REPO_ROOT,
            check=False,
        )
        tests = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            cwd=REPO_ROOT,
            check=False,
        )
        if validate.returncode == 0:
            ok.append("Process validation erfolgreich.")
        else:
            errors.append("Process validation fehlgeschlagen.")
        if tests.returncode == 0:
            ok.append("Unit tests erfolgreich.")
        else:
            errors.append("Unit tests fehlgeschlagen.")

    print("=== Startup Check Result ===")
    for entry in ok:
        print(f"OK: {entry}")
    for entry in warnings:
        print(f"WARN: {entry}")
    for entry in errors:
        print(f"ERROR: {entry}")

    if errors:
        print("STATUS: FAILED")
        return 1
    print("STATUS: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
