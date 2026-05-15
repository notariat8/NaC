from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REQ_FILE = REPO_ROOT / "policies" / "startup-requirements.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Startup verification for local IDE/tooling setup.")
    parser.add_argument(
        "--profile",
        choices=["base", "plugin-dev", "notary-workstation"],
        default="base",
        help="Environment profile to verify.",
    )
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


def parse_command_version(text: str) -> tuple[int, int] | None:
    token = text.strip().splitlines()[0].strip() if text.strip() else ""
    token = token.lstrip("vV")
    parts = token.split(".")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def command_version(command: str) -> tuple[int, int] | None:
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return parse_command_version(result.stdout or result.stderr)


def check_node_runtime(requirements: dict[str, Any]) -> tuple[list[str], list[str]]:
    ok: list[str] = []
    errors: list[str] = []
    for command in ("node", "npm"):
        if command_exists(command):
            ok.append(f"Command vorhanden: {command}")
        else:
            errors.append(f"Command fehlt: {command}")

    min_version = requirements.get("node", {}).get("min_version", "20")
    node_version = command_version("node")
    if node_version is None:
        errors.append("Node.js-Version konnte nicht bestimmt werden.")
        return ok, errors

    min_major = int(str(min_version).split(".", 1)[0])
    if node_version[0] >= min_major:
        ok.append(f"Node.js-Version ok: {node_version[0]}.{node_version[1]}")
    else:
        errors.append(
            f"Node.js-Version zu alt: {node_version[0]}.{node_version[1]}, benoetigt >= {min_version}"
        )
    return ok, errors


def check_windows_service(service_name: str) -> bool | None:
    if os.name != "nt":
        return None
    result = subprocess.run(
        ["sc.exe", "query", service_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    output = f"{result.stdout}\n{result.stderr}".upper()
    return "RUNNING" in output


def path_exists_any(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def check_notary_workstation() -> tuple[list[str], list[str], list[str]]:
    ok: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    if os.name != "nt":
        errors.append("Notariatsarbeitsplatz-Profil benoetigt Windows.")
        return ok, warnings, errors
    ok.append(f"Betriebssystem erkannt: {platform.platform()}")

    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))

    driver_path = path_exists_any(
        [
            program_files / "REINER SCT" / "DriverPackage",
            Path(r"C:\Program Files\REINER SCT\DriverPackage"),
        ]
    )
    if driver_path:
        ok.append(f"REINER SCT DriverPackage gefunden: {driver_path}")
    else:
        warnings.append("REINER SCT DriverPackage nicht gefunden; fuer echte Kartenleser-Tests vor Nutzung installieren oder manuell bestaetigen.")

    morris_path = path_exists_any(
        [
            program_files_x86 / "REINER SCT" / "morris",
            program_files / "REINER SCT" / "morris",
            Path(r"C:\Program Files (x86)\REINER SCT\morris"),
        ]
    )
    if morris_path:
        ok.append(f"REINER SCT morris gefunden: {morris_path}")
    else:
        errors.append("REINER SCT morris nicht gefunden.")

    pcsc_running = check_windows_service("SCardSvr")
    if pcsc_running is True:
        ok.append("PC/SC-Dienst SCardSvr laeuft.")
    elif pcsc_running is False:
        errors.append("PC/SC-Dienst SCardSvr ist nicht erreichbar oder laeuft nicht.")
    else:
        warnings.append("PC/SC-Dienst konnte auf diesem System nicht geprueft werden.")

    warnings.append("XNP-Installation und SAK-lite/XNP-Kartenpfad muessen manuell oder per Plugin-Check bestaetigt werden.")
    warnings.append("morris-Loopback bitte mit `plugins/noc-cyberjack-rfid/scripts/check_readiness.py --json --probe-morris-api` pruefen.")

    return ok, warnings, errors


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


def build_python_env() -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    )
    return env


def main() -> int:
    args = parse_args()
    requirements = parse_simple_yaml(REQ_FILE)

    ok: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    ok.append(f"Profil: {args.profile}")

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

    if args.profile in {"plugin-dev", "notary-workstation"}:
        node_ok, node_errors = check_node_runtime(requirements)
        ok.extend(node_ok)
        errors.extend(node_errors)

    if args.profile == "notary-workstation":
        workstation_ok, workstation_warnings, workstation_errors = check_notary_workstation()
        ok.extend(workstation_ok)
        warnings.extend(workstation_warnings)
        errors.extend(workstation_errors)

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
        python_env = build_python_env()
        validate = subprocess.run(
            [sys.executable, "-m", "business_os", "validate-all", "--repo-root", "."],
            cwd=REPO_ROOT,
            env=python_env,
            check=False,
        )
        tests = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            cwd=REPO_ROOT,
            env=python_env,
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
