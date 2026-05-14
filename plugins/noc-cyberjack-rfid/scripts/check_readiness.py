from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


PLUGIN_NAME = "noc-cyberjack-rfid"
SCHEMA_VERSION = "noc.cyberjack.readiness/v1"
XNP_PORTS = range(12774, 12785)
AUSWEISAPP_STATUS_URL = "http://127.0.0.1:24727/eID-Client?Status=json"
LINUX_READER_PATTERNS = re.compile(r"(REINER|cyberJack|SCT|Smart Card|0c4b)", re.IGNORECASE)
WINDOWS_READER_PATTERNS = re.compile(r"(REINER|cyberJack|SCT)", re.IGNORECASE)
WINDOWS_SMARTCARD_PATTERNS = re.compile(r"(SmartCardReader|Smart Card|Smartcard|Smartcard-Leser)", re.IGNORECASE)
MORRIS_ENDPOINT_PATTERNS = re.compile(r"net\.pipe://localhost/[A-Za-z0-9]+", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def hash_identifier(value: str | None) -> str | None:
    if not value:
        return None
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()
    return f"sha256:{digest}"


def normalize_attestation(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"yes", "y", "true", "1", "ja"}:
        return "yes"
    if normalized in {"no", "n", "false", "0", "nein"}:
        return "no"
    return "unknown"


def check_result(
    check_id: str,
    title: str,
    status: str,
    severity: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": status,
        "severity": severity,
        "message": message,
        "details": details or {},
    }


def run_command(command: list[str], timeout: float = 3.0) -> tuple[int | None, str, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return None, "", str(exc)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def safe_error(value: str, limit: int = 240) -> str:
    return value.replace("\r", " ").replace("\n", " ").strip()[:limit]


def file_metadata(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError:
        return {"path": str(path), "exists": False}
    return {
        "path": str(path),
        "exists": True,
        "size": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=UTC).replace(microsecond=0).isoformat(),
    }


def windows_driver_package_paths() -> list[Path]:
    candidates = []
    for env_name in ["ProgramFiles", "ProgramW6432"]:
        root = os.environ.get(env_name)
        if root:
            candidates.append(Path(root) / "REINER SCT" / "DriverPackage")
    candidates.append(Path("C:/Program Files/REINER SCT/DriverPackage"))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def windows_morris_paths() -> list[Path]:
    candidates = []
    for env_name in ["ProgramFiles(x86)", "ProgramFiles", "ProgramW6432"]:
        root = os.environ.get(env_name)
        if root:
            candidates.append(Path(root) / "REINER SCT" / "morris")
    candidates.append(Path("C:/Program Files (x86)/REINER SCT/morris"))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def read_text_if_exists(path: Path, limit: int = 20000) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def parse_reiner_driver_provider(raw: str) -> dict[str, Any]:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    provider_seen = any(
        line.lower().startswith(("anbietername:", "provider name:")) and "reiner" in line.lower()
        for line in lines
    )
    smartcard_seen = any("smartcardreader" in line.lower() or "smart card reader" in line.lower() for line in lines)
    version = None
    for line in lines:
        lower = line.lower()
        if lower.startswith(("treiberversion:", "driver version:")):
            version = line.split(":", 1)[1].strip()
            break
    return {
        "provider_seen": provider_seen,
        "smartcard_reader_class_seen": smartcard_seen,
        "driver_version": version,
    }


def probe_windows_driver_stack(base_paths: list[Path] | None = None) -> dict[str, Any]:
    if platform.system().lower() != "windows":
        return check_result(
            "windows_driver_stack",
            "Windows REINER SCT driver stack",
            "passed",
            "info",
            "Windows driver package check is not required on this operating system.",
        )

    candidates = base_paths if base_paths is not None else windows_driver_package_paths()
    base_path = next((path for path in candidates if path.exists()), None)
    details: dict[str, Any] = {
        "candidate_paths": [str(path) for path in candidates],
        "driver_package_path": str(base_path) if base_path else None,
    }

    if base_path:
        expected_files = [
            base_path / "dpcc.exe",
            base_path / "PCSC.dll",
            base_path / "x64-W10" / "dpumdf-W10.inf",
            base_path / "x64-W10" / "dpumdf.dll",
            base_path / "ctapi" / "ctrsct32.dll",
        ]
        details["files"] = [file_metadata(path) for path in expected_files]

    provider_details: dict[str, Any] = {}
    if command_exists("pnputil.exe") or command_exists("pnputil"):
        code, stdout, stderr = run_command(["pnputil.exe", "/enum-drivers"], timeout=12.0)
        provider_details = parse_reiner_driver_provider(stdout) if code == 0 else {"error": safe_error(stderr)}
        provider_details["exit_code"] = code
    details["pnputil_driver"] = provider_details

    required_files_present = bool(base_path) and all(item.get("exists") for item in details.get("files", []))
    provider_seen = bool(provider_details.get("provider_seen") and provider_details.get("smartcard_reader_class_seen"))

    if required_files_present and provider_seen:
        return check_result(
            "windows_driver_stack",
            "Windows REINER SCT driver stack",
            "passed",
            "info",
            "REINER SCT DriverPackage and installed SmartCardReader driver provider are visible.",
            details,
        )
    if required_files_present:
        return check_result(
            "windows_driver_stack",
            "Windows REINER SCT driver stack",
            "manual_review",
            "manual",
            "REINER SCT DriverPackage is installed on disk, but the installed driver provider was not confirmed.",
            details,
        )
    if provider_seen:
        return check_result(
            "windows_driver_stack",
            "Windows REINER SCT driver stack",
            "manual_review",
            "manual",
            "REINER SCT SmartCardReader driver provider is installed, but the DriverPackage path was not confirmed.",
            details,
        )
    return check_result(
        "windows_driver_stack",
        "Windows REINER SCT driver stack",
        "manual_review",
        "manual",
        "REINER SCT DriverPackage and driver provider were not confirmed.",
        details,
    )


def parse_sc_state(raw: str) -> str:
    for line in raw.splitlines():
        if "STATE" not in line.upper() or ":" not in line:
            continue
        state = line.split(":", 1)[1].strip().upper()
        if "RUNNING" in state:
            return "running"
        if "STOPPED" in state:
            return "stopped"
        return state.lower()
    return "unknown"


def tasklist_processes() -> list[str]:
    code, stdout, _stderr = run_command(["tasklist", "/fo", "csv", "/nh"], timeout=6.0)
    if code == 0 and stdout:
        names: list[str] = []
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            first = stripped.split(",", 1)[0].strip().strip('"')
            if first:
                names.append(first)
        return names

    code, stdout, _stderr = run_command(
        ["powershell.exe", "-NoProfile", "-Command", "Get-Process | Select-Object -ExpandProperty ProcessName"],
        timeout=6.0,
    )
    if code != 0 or not stdout:
        return []
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def probe_windows_morris_stack(base_paths: list[Path] | None = None) -> dict[str, Any]:
    if platform.system().lower() != "windows":
        return check_result(
            "windows_morris_stack",
            "Windows morris browser middleware",
            "passed",
            "info",
            "morris browser middleware check is not required on this operating system.",
        )

    candidates = base_paths if base_paths is not None else windows_morris_paths()
    base_path = next((path for path in candidates if path.exists()), None)
    details: dict[str, Any] = {
        "candidate_paths": [str(path) for path in candidates],
        "morris_path": str(base_path) if base_path else None,
    }

    if base_path:
        expected_files = [
            base_path / "Server" / "morrisServer.exe",
            base_path / "Server" / "IMorrisExternalPlugin.dll",
            base_path / "Server" / "morrisServer.exe.config",
            base_path / "Service" / "morrisDispatcherService.exe",
            base_path / "Service" / "morrisDispatcherService.exe.config",
        ]
        details["files"] = [file_metadata(path) for path in expected_files]
        endpoints = []
        for config in [
            base_path / "Server" / "morrisServer.exe.config",
            base_path / "Service" / "morrisDispatcherService.exe.config",
        ]:
            endpoints.extend(MORRIS_ENDPOINT_PATTERNS.findall(read_text_if_exists(config)))
        details["local_endpoints"] = sorted(set(endpoints))

    code, stdout, stderr = run_command(["sc.exe", "query", "morris"], timeout=4.0)
    service_state = parse_sc_state(stdout) if code == 0 else "unknown"
    details["service"] = {
        "name": "morris",
        "query_exit_code": code,
        "state": service_state,
        "error": safe_error(stderr) if stderr else None,
    }

    matched_processes = sorted(
        name
        for name in tasklist_processes()
        if name.lower().removesuffix(".exe") in {"morrisserver", "morrisdispatcherservice"}
    )
    details["processes"] = matched_processes

    required_files_present = bool(base_path) and all(item.get("exists") for item in details.get("files", []))
    service_running = service_state == "running"
    normalized_processes = {name.lower().removesuffix(".exe") for name in matched_processes}
    server_running = "morrisserver" in normalized_processes
    dispatcher_running = "morrisdispatcherservice" in normalized_processes

    if required_files_present and service_running and server_running and dispatcher_running:
        return check_result(
            "windows_morris_stack",
            "Windows morris browser middleware",
            "passed",
            "info",
            "REINER SCT morris is installed and running as local browser middleware.",
            details,
        )
    if required_files_present and service_running:
        return check_result(
            "windows_morris_stack",
            "Windows morris browser middleware",
            "manual_review",
            "manual",
            "REINER SCT morris is installed and the service is running, but all expected processes were not confirmed.",
            details,
        )
    if required_files_present:
        return check_result(
            "windows_morris_stack",
            "Windows morris browser middleware",
            "manual_review",
            "manual",
            "REINER SCT morris is installed, but the service is not confirmed as running.",
            details,
        )
    return check_result(
        "windows_morris_stack",
        "Windows morris browser middleware",
        "manual_review",
        "manual",
        "REINER SCT morris installation was not confirmed.",
        details,
    )


def linux_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def dpkg_package_state(package: str) -> dict[str, Any]:
    code, stdout, _stderr = run_command(
        ["dpkg-query", "-W", "-f=${Status}|${Version}", package],
        timeout=4.0,
    )
    installed = code == 0 and stdout.startswith("install ok installed")
    version = stdout.split("|", 1)[1] if installed and "|" in stdout else None
    return {"package": package, "installed": installed, "version": version}


def apt_candidate(package: str) -> str | None:
    if not command_exists("apt-cache"):
        return None
    code, stdout, _stderr = run_command(["apt-cache", "policy", package], timeout=4.0)
    if code != 0:
        return None
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("Candidate:"):
            candidate = stripped.split(":", 1)[1].strip()
            return None if candidate == "(none)" else candidate
    return None


def probe_linux_driver_stack() -> dict[str, Any]:
    if platform.system().lower() != "linux":
        return check_result(
            "linux_driver_stack",
            "Linux cyberJack driver stack",
            "passed",
            "info",
            "Linux driver package check is not required on this operating system.",
        )

    distro = linux_os_release()
    details: dict[str, Any] = {"os_release": distro}

    if command_exists("dpkg-query"):
        packages = [dpkg_package_state(name) for name in ["cyberjack", "pcscd", "pcsc-tools", "libccid"]]
        details["packages"] = packages
        details["cyberjack_candidate"] = apt_candidate("cyberjack")
        cyberjack_installed = any(item["package"] == "cyberjack" and item["installed"] for item in packages)
        pcscd_installed = any(item["package"] == "pcscd" and item["installed"] for item in packages)
        if cyberjack_installed and pcscd_installed:
            return check_result(
                "linux_driver_stack",
                "Linux cyberJack driver stack",
                "passed",
                "info",
                "cyberJack and PC/SC packages are installed.",
                details,
            )
        if details["cyberjack_candidate"]:
            return check_result(
                "linux_driver_stack",
                "Linux cyberJack driver stack",
                "manual_review",
                "manual",
                "cyberJack package is available but not confirmed as installed.",
                details,
            )
        return check_result(
            "linux_driver_stack",
            "Linux cyberJack driver stack",
            "manual_review",
            "manual",
            "cyberJack package is not confirmed in the Debian/Ubuntu package database.",
            details,
        )

    if command_exists("rpm"):
        package_names = ["cyberjack", "pcsc-lite", "pcsc-tools", "ccid"]
        packages = []
        for package in package_names:
            code, stdout, _stderr = run_command(["rpm", "-q", package], timeout=4.0)
            packages.append({"package": package, "installed": code == 0, "version": stdout if code == 0 else None})
        details["packages"] = packages
        if any(item["package"] == "cyberjack" and item["installed"] for item in packages):
            return check_result(
                "linux_driver_stack",
                "Linux cyberJack driver stack",
                "passed",
                "info",
                "cyberJack RPM package is installed.",
                details,
            )
        return check_result(
            "linux_driver_stack",
            "Linux cyberJack driver stack",
            "manual_review",
            "manual",
            "cyberJack RPM package is not confirmed as installed.",
            details,
        )

    return check_result(
        "linux_driver_stack",
        "Linux cyberJack driver stack",
        "manual_review",
        "manual",
        "No supported Linux package database command was found.",
        details,
    )


def probe_pcsc_service() -> dict[str, Any]:
    system = platform.system().lower()
    if system == "windows":
        code, stdout, stderr = run_command(["sc.exe", "query", "SCardSvr"])
        if code is None:
            return check_result(
                "pcsc_service",
                "PC/SC service",
                "unknown",
                "manual",
                "PC/SC service state could not be queried.",
                {"error": stderr},
            )
        combined = f"{stdout}\n{stderr}".upper()
        if "RUNNING" in combined:
            return check_result(
                "pcsc_service",
                "PC/SC service",
                "passed",
                "info",
                "Windows Smart Card service is running.",
            )
        if "STOPPED" in combined:
            return check_result(
                "pcsc_service",
                "PC/SC service",
                "failed",
                "manual",
                "Windows Smart Card service is installed but not running.",
            )
        return check_result(
            "pcsc_service",
            "PC/SC service",
            "manual_review",
            "manual",
            "Windows Smart Card service state is inconclusive.",
            {"sc_exit_code": code},
        )

    if system == "linux":
        code, stdout, _stderr = run_command(["systemctl", "is-active", "pcscd"])
        if code == 0 and stdout.strip() == "active":
            return check_result(
                "pcsc_service",
                "PC/SC service",
                "passed",
                "info",
                "pcscd service is active.",
            )
        return check_result(
            "pcsc_service",
            "PC/SC service",
            "manual_review",
            "manual",
            "pcscd service could not be confirmed as active.",
            {"systemctl_exit_code": code, "systemctl_state": stdout},
        )

    if system == "darwin":
        code, stdout, _stderr = run_command(["pgrep", "-x", "pcscd"])
        if code == 0 and stdout:
            return check_result(
                "pcsc_service",
                "PC/SC service",
                "passed",
                "info",
                "pcscd process is running.",
            )
        return check_result(
            "pcsc_service",
            "PC/SC service",
            "manual_review",
            "manual",
            "pcscd process could not be confirmed.",
        )

    return check_result(
        "pcsc_service",
        "PC/SC service",
        "unknown",
        "manual",
        "PC/SC probe is not implemented for this operating system.",
    )


def parse_json_list(raw_json: str) -> list[dict[str, Any]]:
    if not raw_json:
        return []
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def parse_pnputil_connected_readers(raw: str) -> list[dict[str, Any]]:
    readers: list[dict[str, Any]] = []
    current: dict[str, str] = {}
    label_map = {
        "instanz-id": "instance_id",
        "instance id": "instance_id",
        "gerätebeschreibung": "description",
        "device description": "description",
        "klassenname": "class_name",
        "class name": "class_name",
        "herstellername": "manufacturer",
        "manufacturer name": "manufacturer",
        "status": "status",
        "treibername": "driver_name",
        "driver name": "driver_name",
    }

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        label, value = stripped.split(":", 1)
        key = label_map.get(label.strip().lower())
        if not key:
            continue
        if key == "instance_id" and current:
            readers.append(current)
            current = {}
        current[key] = value.strip()
    if current:
        readers.append(current)

    normalized = []
    for item in readers:
        text = " ".join(str(value) for value in item.values())
        normalized.append(
            {
                "description": item.get("description"),
                "manufacturer": item.get("manufacturer"),
                "status": item.get("status"),
                "driver_name": item.get("driver_name"),
                "fingerprint_hash": hash_identifier(item.get("instance_id") or text),
                "reiner_sct_match": bool(WINDOWS_READER_PATTERNS.search(text)),
                "smartcard_reader_match": bool(WINDOWS_SMARTCARD_PATTERNS.search(text)),
            }
        )
    return normalized


def probe_windows_readers_via_pnputil() -> dict[str, Any] | None:
    if not (command_exists("pnputil.exe") or command_exists("pnputil")):
        return None
    code, stdout, stderr = run_command(
        ["pnputil.exe", "/enum-devices", "/connected", "/class", "SmartCardReader"],
        timeout=8.0,
    )
    if code != 0:
        return check_result(
            "reader_detection",
            "Card-reader detection",
            "manual_review",
            "manual",
            "PnP smart-card reader detection did not complete successfully.",
            {"exit_code": code, "error": safe_error(stderr)},
        )

    readers = parse_pnputil_connected_readers(stdout)
    reiner_readers = [reader for reader in readers if reader["reiner_sct_match"]]
    if reiner_readers:
        return check_result(
            "reader_detection",
            "Card-reader detection",
            "passed",
            "info",
            "A connected REINER SCT/cyberJack smart-card reader is visible through PnP.",
            {"readers": reiner_readers},
        )
    if readers:
        return check_result(
            "reader_detection",
            "Card-reader detection",
            "manual_review",
            "manual",
            "Smart-card reader hardware is visible, but no connected REINER SCT/cyberJack reader was confirmed.",
            {"readers": readers},
        )
    return check_result(
        "reader_detection",
        "Card-reader detection",
        "manual_review",
        "manual",
        "No connected SmartCardReader device was reported by PnP.",
    )


def probe_windows_readers() -> dict[str, Any]:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance -ClassName Win32_PnPEntity | "
            "Where-Object { $_.Name -match 'REINER|cyberJack|Smart Card|SCT' } | "
            "Select-Object @{Name='FriendlyName';Expression={$_.Name}},Status,"
            "@{Name='InstanceId';Expression={$_.DeviceID}} | ConvertTo-Json -Compress"
        ),
    ]
    code, stdout, stderr = run_command(command, timeout=8.0)
    if code is None:
        return check_result(
            "reader_detection",
            "Card-reader detection",
            "unknown",
            "manual",
            "Reader detection command is unavailable.",
            {"error": stderr},
        )
    if code != 0:
        fallback = probe_windows_readers_via_pnputil()
        if fallback is not None:
            fallback["details"]["cim_error"] = {"exit_code": code, "error": safe_error(stderr)}
            return fallback
        return check_result(
            "reader_detection",
            "Card-reader detection",
            "manual_review",
            "manual",
            "Reader detection command did not complete successfully.",
            {"exit_code": code, "error": safe_error(stderr)},
        )

    readers = []
    for item in parse_json_list(stdout):
        friendly_name = str(item.get("FriendlyName") or "")
        status = str(item.get("Status") or "")
        instance_id = str(item.get("InstanceId") or "")
        if not friendly_name:
            continue
        readers.append(
            {
                "friendly_name": friendly_name,
                "status": status,
                "fingerprint_hash": hash_identifier(instance_id or friendly_name),
            }
        )

    if readers:
        reiner_readers = [
            reader
            for reader in readers
            if WINDOWS_READER_PATTERNS.search(" ".join(str(value) for value in reader.values()))
        ]
        if not reiner_readers:
            fallback = probe_windows_readers_via_pnputil()
            if fallback is not None:
                return fallback
        return check_result(
            "reader_detection",
            "Card-reader detection",
            "passed",
            "info",
            "At least one relevant local card-reader device was detected.",
            {"readers": readers},
        )

    return check_result(
        "reader_detection",
        "Card-reader detection",
        "manual_review",
        "manual",
        "No relevant cyberJack, REINER SCT or smart-card reader was detected.",
    )


def probe_linux_readers() -> dict[str, Any]:
    detected: list[dict[str, Any]] = []

    if command_exists("lsusb"):
        code, stdout, stderr = run_command(["lsusb"], timeout=4.0)
        if code == 0:
            for line in stdout.splitlines():
                if LINUX_READER_PATTERNS.search(line):
                    detected.append(
                        {
                            "source": "lsusb",
                            "fingerprint_hash": hash_identifier(line),
                            "description": re.sub(r"\s+", " ", line).strip()[:160],
                        }
                    )
        elif stderr:
            return check_result(
                "reader_detection",
                "Card-reader detection",
                "manual_review",
                "manual",
                "USB reader detection command did not complete successfully.",
                {"exit_code": code, "error": safe_error(stderr)},
            )

    if command_exists("pcsc_scan"):
        code, stdout, stderr = run_command(["pcsc_scan", "-n"], timeout=5.0)
        if code in {0, 1} and stdout:
            for line in stdout.splitlines():
                if LINUX_READER_PATTERNS.search(line):
                    detected.append(
                        {
                            "source": "pcsc_scan",
                            "fingerprint_hash": hash_identifier(line),
                            "description": re.sub(r"\s+", " ", line).strip()[:160],
                        }
                    )
        elif stderr and not detected:
            return check_result(
                "reader_detection",
                "Card-reader detection",
                "manual_review",
                "manual",
                "PC/SC reader scan did not complete successfully.",
                {"exit_code": code, "error": safe_error(stderr)},
            )

    if detected:
        return check_result(
            "reader_detection",
            "Card-reader detection",
            "passed",
            "info",
            "At least one relevant Linux USB/PCSC card-reader signal was detected.",
            {"readers": detected},
        )

    return check_result(
        "reader_detection",
        "Card-reader detection",
        "manual_review",
        "manual",
        "No cyberJack, REINER SCT or smart-card reader was detected through Linux USB/PCSC probes.",
        {"lsusb_available": command_exists("lsusb"), "pcsc_scan_available": command_exists("pcsc_scan")},
    )


def probe_reader_detection() -> dict[str, Any]:
    system = platform.system().lower()
    if system == "windows":
        return probe_windows_readers()
    if system == "linux":
        return probe_linux_readers()
    return check_result(
        "reader_detection",
        "Card-reader detection",
        "manual_review",
        "manual",
        "Automatic reader detection is currently implemented for Windows only.",
    )


def probe_xnp_local_interface() -> dict[str, Any]:
    open_ports: list[int] = []
    for port in XNP_PORTS:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                open_ports.append(port)
        except OSError:
            continue

    if open_ports:
        return check_result(
            "xnp_local_interface",
            "XNP localhost interface",
            "passed",
            "info",
            "One or more XNP localhost ports are reachable. No API key was read or used.",
            {"host": "127.0.0.1", "open_ports": open_ports, "api_key_observed": False},
        )

    return check_result(
        "xnp_local_interface",
        "XNP localhost interface",
        "manual_review",
        "manual",
        "No XNP localhost port in the expected range is reachable.",
        {
            "host": "127.0.0.1",
            "port_range": [min(XNP_PORTS), max(XNP_PORTS)],
            "api_key_observed": False,
        },
    )


def probe_ausweisapp_status() -> dict[str, Any]:
    try:
        with urlopen(AUSWEISAPP_STATUS_URL, timeout=1.0) as response:
            status_code = int(response.status)
            raw = response.read(4096).decode("utf-8", errors="replace")
    except URLError as exc:
        return check_result(
            "ausweisapp_status",
            "AusweisApp status",
            "manual_review",
            "manual",
            "AusweisApp status endpoint is not reachable.",
            {"endpoint": AUSWEISAPP_STATUS_URL, "error": str(exc.reason)},
        )
    except OSError as exc:
        return check_result(
            "ausweisapp_status",
            "AusweisApp status",
            "manual_review",
            "manual",
            "AusweisApp status endpoint could not be queried.",
            {"endpoint": AUSWEISAPP_STATUS_URL, "error": str(exc)},
        )

    parsed: dict[str, Any] = {}
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            for key in ["VersionInfo", "Status", "Reader"]:
                if key in payload:
                    parsed[key] = payload[key]
    except json.JSONDecodeError:
        parsed["raw_status_prefix"] = raw[:80]

    return check_result(
        "ausweisapp_status",
        "AusweisApp status",
        "passed" if status_code == 200 else "manual_review",
        "info" if status_code == 200 else "manual",
        "AusweisApp status endpoint answered without exposing identity attributes.",
        {"endpoint": AUSWEISAPP_STATUS_URL, "http_status": status_code, "status": parsed},
    )


def list_process_names() -> list[str]:
    if platform.system().lower() == "windows":
        code, stdout, _stderr = run_command(["tasklist", "/fo", "csv", "/nh"], timeout=6.0)
        if code != 0 or not stdout:
            return []
        names: list[str] = []
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            first = stripped.split(",", 1)[0].strip().strip('"')
            if first:
                names.append(first)
        return names

    code, stdout, _stderr = run_command(["ps", "-axo", "comm="], timeout=6.0)
    if code != 0 or not stdout:
        return []
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def probe_named_process(check_id: str, title: str, needles: list[str]) -> dict[str, Any]:
    names = list_process_names()
    matches = sorted(
        {
            name
            for name in names
            for needle in needles
            if needle.lower() in name.lower()
        }
    )
    if matches:
        return check_result(
            check_id,
            title,
            "passed",
            "info",
            f"{title} process appears to be running.",
            {"matched_processes": matches},
        )
    return check_result(
        check_id,
        title,
        "manual_review",
        "manual",
        f"{title} process was not detected automatically.",
    )


def manual_attestation_check(
    check_id: str,
    title: str,
    value: str,
    yes_message: str,
    no_message: str,
    unknown_message: str,
    blocker_if_no: bool = True,
) -> dict[str, Any]:
    normalized = normalize_attestation(value)
    if normalized == "yes":
        return check_result(check_id, title, "passed", "info", yes_message, {"attested": "yes"})
    if normalized == "no":
        return check_result(
            check_id,
            title,
            "failed",
            "blocker" if blocker_if_no else "manual",
            no_message,
            {"attested": "no"},
        )
    return check_result(
        check_id,
        title,
        "manual_review",
        "manual",
        unknown_message,
        {"attested": "unknown"},
    )


def evaluate_overall_status(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == "failed" and check["severity"] == "blocker" for check in checks):
        return "blocked"
    if any(check["status"] in {"failed", "manual_review", "unknown"} for check in checks):
        return "manual_review"
    return "ready"


def build_evidence(args: argparse.Namespace) -> dict[str, Any]:
    checks = [
        manual_attestation_check(
            "bnotk_card_present",
            "BNotK chip/signature card",
            args.manual_card_present,
            "Operator attests that the BNotK chip/signature card is available.",
            "BNotK chip/signature card is missing.",
            "BNotK chip/signature card availability needs manual confirmation.",
        ),
        manual_attestation_check(
            "rfid_disabled",
            "RFID disabled for BNotK chip-card workflow",
            args.manual_rfid_off,
            "Operator attests that RFID is disabled or not used for this BNotK chip-card workflow.",
            "RFID is not disabled for a BNotK chip-card workflow.",
            "RFID-off status needs manual confirmation.",
        ),
    ]
    if platform.system().lower() == "linux":
        checks.append(probe_linux_driver_stack())
    if platform.system().lower() == "windows":
        checks.append(probe_windows_driver_stack())
        checks.append(probe_windows_morris_stack())
    checks.extend(
        [
            probe_pcsc_service(),
            probe_reader_detection(),
            probe_named_process(
                "sak_or_xnp_card_path",
                "BNotK SAK lite or XNP card path",
                ["xnp", "sak", "bnotk"],
            ),
            probe_named_process(
                "secureframework",
                "secureFramework",
                ["secureframework", "secure framework"],
            ),
            probe_xnp_local_interface(),
            probe_ausweisapp_status(),
        ]
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "plugin": PLUGIN_NAME,
        "evidence_id": f"CJ-{uuid.uuid4()}",
        "generated_at": utc_now(),
        "overall_status": evaluate_overall_status(checks),
        "manual_attestations": {
            "bnotk_card_present": normalize_attestation(args.manual_card_present),
            "rfid_disabled_for_bnotk_chip_workflow": normalize_attestation(args.manual_rfid_off),
        },
        "system": {
            "os": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
        },
        "policy": {
            "pin_captured": False,
            "card_data_captured": False,
            "xnp_api_key_captured": False,
            "external_network_calls": False,
            "localhost_only": True,
        },
        "checks": checks,
        "next_required_action": next_required_action(checks),
    }


def next_required_action(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == "failed" and check["severity"] == "blocker" for check in checks):
        return "Resolve blocker before XNP login testing."
    if any(check["status"] in {"manual_review", "unknown", "failed"} for check in checks):
        return "Complete manual review and rerun readiness check before using downstream XNP workflows."
    return "Proceed to noc-bnotk-xnp readiness testing with human approval for any PIN or login step."


def write_output(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local readiness check for the NoC cyberJack/RFID card gate."
    )
    parser.add_argument(
        "--manual-card-present",
        default="unknown",
        choices=["yes", "no", "unknown"],
        help="Manual attestation that the BNotK chip/signature card is available.",
    )
    parser.add_argument(
        "--manual-rfid-off",
        default="unknown",
        choices=["yes", "no", "unknown"],
        help="Manual attestation that RFID is disabled or not used for the BNotK chip-card workflow.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON evidence output path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON evidence to stdout.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code unless the overall status is ready.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    evidence = build_evidence(args)

    if args.output:
        write_output(args.output, evidence)

    if args.json:
        print(json.dumps(evidence, indent=2, ensure_ascii=True))
    else:
        print(f"{PLUGIN_NAME}: {evidence['overall_status']}")
        print(evidence["next_required_action"])

    if args.strict and evidence["overall_status"] != "ready":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
