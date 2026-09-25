"""Build an offline, reviewable Issue #748 Windows onedir candidate.

The command uses installed, pinned local tools only. It neither installs tools
nor authenticates, contacts a provider, publishes, or enables a real read.
"""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import asdict
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = "workflows/contracts/m365-current-state-read-driver-resources.contract.json"
SOURCE = "src/nac_bff/current_state_read_driver.py"
SCHEMA = "nac.m365-current-state-read-driver-candidate/v0.2"
PREPARATION_SCHEMA = "nac.m365-current-state-read-driver-preparation/v0.1"
LICENSE_SCHEMA = "nac.m365-current-state-read-driver-license-inventory/v0.1"
LICENSE_CATALOG_SCHEMA = "nac.m365-current-state-read-driver-license-catalog/v0.1"
LICENSE_CATALOG = "workflows/contracts/m365-current-state-read-driver-license-catalog.json"
PYINSTALLER_VERSION = "6.22.3"
SYFT_VERSION = "1.52.0"
PYTHON_VERSION = "3.13.4"
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_COMPONENT = re.compile(r"[A-Za-z0-9._-]{1,120}\Z")
_ARTIFACTS = (
    "source.tar", "cyclonedx.json", "spdx.json", "LICENSE", "NOTICE",
    "license-inventory.json", "license-catalog.json", "preparation.json",
)
_BUNDLE_FIELDS = (
    "path", "sha256", "size", "volume_serial", "file_id",
    "owner_sid_sha256", "dacl_sha256", "security_descriptor_sha256",
    "path_sha256",
)


class BuildBlocked(RuntimeError):
    """A sanitized stable code; never include subprocess output or local data."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False)
        stream.write("\n")


def _safe_relative(value: object, *, prefix: str | None = None) -> str:
    if (
        not isinstance(value, str) or not value or len(value) > 240
        or "\\" in value or ":" in value or value.startswith("/")
        or any(ord(character) < 32 or character in '*?<>|"' for character in value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or any(part.endswith((" ", ".")) for part in value.split("/"))
        or any(part.split(".", 1)[0].upper() in {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{number}" for number in range(1, 10)),
            *(f"LPT{number}" for number in range(1, 10)),
        } for part in value.split("/"))
        or (prefix is not None and not value.startswith(prefix))
    ):
        raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
    return value


def validate_output_path(repo: Path, output: Path) -> Path:
    if not output.is_absolute() or not output.parent.is_dir():
        raise BuildBlocked("BLOCKED_OUTPUT_PATH_INVALID")
    repository = repo.resolve(strict=True)
    candidate = output.parent.resolve(strict=True) / output.name
    if candidate == repository or repository in candidate.parents:
        raise BuildBlocked("BLOCKED_OUTPUT_INSIDE_REPOSITORY")
    if candidate.exists() or candidate.is_symlink():
        raise BuildBlocked("BLOCKED_OUTPUT_ALREADY_EXISTS")
    if output.name in {"", ".", ".."} or output.name.endswith((" ", ".")):
        raise BuildBlocked("BLOCKED_OUTPUT_PATH_INVALID")
    return candidate


def _git_command(repo: Path, *arguments: str) -> str:
    executable = _trusted_git_executable()
    result = subprocess.run(
        [str(executable), "--no-optional-locks", "-c",
         f"safe.directory={repo.resolve()}", "-C", str(repo), *arguments],
        capture_output=True, text=True, check=False, timeout=30,
        stdin=subprocess.DEVNULL, env=_git_environment(),
    )
    if result.returncode:
        raise BuildBlocked("BLOCKED_LOCAL_GIT_UNAVAILABLE")
    return result.stdout


def _trusted_git_executable() -> Path:
    if os.name != "nt":
        raise BuildBlocked("BLOCKED_LOCAL_GIT_UNAVAILABLE")
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    candidates = (
        program_files / "Git" / "cmd" / "git.exe",
        program_files / "Git" / "bin" / "git.exe",
    )
    backend, _windows = require_windows_security()
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            backend.inspect_private_path(candidate, purpose="toolchain-executable")
            return candidate
        except (OSError, RuntimeError, ValueError):
            continue
    raise BuildBlocked("BLOCKED_LOCAL_GIT_UNAVAILABLE")


def _git_environment() -> dict[str, str]:
    environment = _offline_environment()
    environment.update({
        "GIT_ATTR_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1",
    })
    return environment


def validate_source_state(
    repo: Path, expected_head: str, expected_tree: str, *, git=None
) -> tuple[str, str]:
    """Require exact local commit/tree and no tracked or untracked changes."""
    if not _HEX40.fullmatch(expected_head) or not _HEX40.fullmatch(expected_tree):
        raise BuildBlocked("BLOCKED_SOURCE_BINDING_INVALID")
    call = git or (lambda *args: _git_command(repo, *args))
    try:
        top = Path(call("rev-parse", "--show-toplevel").strip()).resolve()
        head = call("rev-parse", "HEAD").strip()
        tree = call("rev-parse", "HEAD^{tree}").strip()
        if top != repo.resolve():
            raise BuildBlocked("BLOCKED_SOURCE_REPOSITORY_MISMATCH")
        if head != expected_head:
            raise BuildBlocked("BLOCKED_SOURCE_HEAD_MISMATCH")
        if tree != expected_tree:
            raise BuildBlocked("BLOCKED_SOURCE_TREE_MISMATCH")
        if call("status", "--porcelain=v1", "--untracked-files=all").strip():
            raise BuildBlocked("BLOCKED_SOURCE_NOT_CLEAN")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        raise BuildBlocked("BLOCKED_LOCAL_GIT_UNAVAILABLE") from None
    return head, tree


def require_windows_security():
    if os.name != "nt":
        raise BuildBlocked("BLOCKED_WINDOWS_SECURITY_BACKEND_UNAVAILABLE")
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from nac_bff.activation_security_backend import get_platform_security_backend
        from nac_bff import activation_security_windows

        backend = get_platform_security_backend()
        if not backend.capabilities().complete or not hasattr(
            backend, "validate_current_user_only_directory"
        ):
            raise BuildBlocked("BLOCKED_WINDOWS_SECURITY_BACKEND_UNAVAILABLE")
        return backend, activation_security_windows
    except (ImportError, AttributeError, RuntimeError, OSError):
        raise BuildBlocked("BLOCKED_WINDOWS_SECURITY_BACKEND_UNAVAILABLE") from None


def _seal_tree_current_user_only(root: Path, backend: object, windows: object) -> None:
    """Set DACL through no-follow handles after closed tree enumeration."""
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.GetSecurityDescriptorDacl.argtypes = (
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_int),
    )
    advapi.GetSecurityDescriptorDacl.restype = ctypes.c_int
    advapi.SetSecurityInfo.argtypes = (
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    )
    advapi.SetSecurityInfo.restype = ctypes.c_ulong
    convert = advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = (
        ctypes.c_wchar_p, ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_ulong),
    )
    convert.restype = ctypes.c_int
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = (ctypes.c_void_p,)
    kernel.LocalFree.restype = ctypes.c_void_p
    sid = windows._current_sid_string()
    paths = [root]
    pending = [root]
    try:
        root_info = root.lstat()
        if not stat.S_ISDIR(root_info.st_mode) or getattr(root_info, "st_file_attributes", 0) & 0x400:
            raise BuildBlocked("BLOCKED_CANDIDATE_REPARSE_POINT")
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    info = entry.stat(follow_symlinks=False)
                    if entry.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                        raise BuildBlocked("BLOCKED_CANDIDATE_REPARSE_POINT")
                    path = Path(entry.path)
                    if stat.S_ISDIR(info.st_mode):
                        pending.append(path)
                    elif not stat.S_ISREG(info.st_mode):
                        raise BuildBlocked("BLOCKED_CANDIDATE_NONREGULAR_PATH")
                    paths.append(path)
                    if len(paths) > 8192:
                        raise BuildBlocked("BLOCKED_CANDIDATE_TOO_LARGE")
        paths.sort(key=lambda path: (len(path.parts), str(path)))
        for path in paths:
            if path != root and root not in path.parents:
                raise BuildBlocked("BLOCKED_CANDIDATE_PATH_ESCAPE")
            is_directory = path.is_dir()
            if not is_directory and not path.is_file():
                raise BuildBlocked("BLOCKED_CANDIDATE_NONREGULAR_PATH")
            windows._validate_supported_local_path(path)
            inheritance = "OICI" if is_directory else ""
            sddl = f"O:{sid}D:P(A;{inheritance};GA;;;{sid})"
            descriptor = ctypes.c_void_p()
            length = ctypes.c_ulong()
            if not convert(sddl, 1, ctypes.byref(descriptor), ctypes.byref(length)):
                raise BuildBlocked("BLOCKED_CANDIDATE_ACL_SEAL_FAILED")
            try:
                present = ctypes.c_int()
                dacl = ctypes.c_void_p()
                defaulted = ctypes.c_int()
                if not advapi.GetSecurityDescriptorDacl(
                    descriptor, ctypes.byref(present), ctypes.byref(dacl),
                    ctypes.byref(defaulted),
                ) or not present.value or not dacl.value:
                    raise BuildBlocked("BLOCKED_CANDIDATE_ACL_SEAL_FAILED")
                handle = windows.kernel32.CreateFileW(
                    str(path), 0x00040000 | windows.READ_CONTROL | windows.FILE_READ_ATTRIBUTES,
                    windows.FILE_SHARE_READ | windows.FILE_SHARE_WRITE | windows.FILE_SHARE_DELETE,
                    None, windows.OPEN_EXISTING,
                    windows.FILE_FLAG_OPEN_REPARSE_POINT |
                    (windows.FILE_FLAG_BACKUP_SEMANTICS if is_directory else windows.FILE_ATTRIBUTE_NORMAL),
                    None,
                )
                if handle == windows.INVALID_HANDLE_VALUE:
                    raise BuildBlocked("BLOCKED_CANDIDATE_ACL_SEAL_FAILED")
                try:
                    information = windows.BY_HANDLE_FILE_INFORMATION()
                    if not windows.kernel32.GetFileInformationByHandle(
                        handle, ctypes.byref(information)
                    ) or information.dwFileAttributes & windows.FILE_ATTRIBUTE_REPARSE_POINT:
                        raise BuildBlocked("BLOCKED_CANDIDATE_REPARSE_POINT")
                    if bool(information.dwFileAttributes & windows.FILE_ATTRIBUTE_DIRECTORY) != is_directory:
                        raise BuildBlocked("BLOCKED_CANDIDATE_PATH_DRIFT")
                    if not is_directory and information.nNumberOfLinks != 1:
                        raise BuildBlocked("BLOCKED_CANDIDATE_HARDLINK")
                    windows._require_requested_path_binding(int(handle), path)
                    if advapi.SetSecurityInfo(handle, 1, 4, None, None, dacl, None):
                        raise BuildBlocked("BLOCKED_CANDIDATE_ACL_SEAL_FAILED")
                finally:
                    windows._close_handle(int(handle))
            finally:
                kernel.LocalFree(descriptor)
        for path in paths:
            if path.is_dir():
                backend.validate_current_user_only_directory(path)
            else:
                backend.inspect_private_path(
                    path, purpose="issue748-read-driver-bundle-current-user-only"
                )
    except BuildBlocked:
        raise
    except (OSError, AttributeError, RuntimeError, ValueError, TypeError):
        raise BuildBlocked("BLOCKED_CANDIDATE_ACL_SEAL_FAILED") from None


def _offline_environment() -> dict[str, str]:
    """Pass only ordinary local runtime variables, never provider credentials."""
    allowed = (
        "SystemRoot", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP",
        "USERPROFILE", "APPDATA", "LOCALAPPDATA", "ProgramFiles", "COMSPEC",
    )
    environment = {name: os.environ[name] for name in allowed if name in os.environ}
    environment.update({
        "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "SYFT_CHECK_FOR_APP_UPDATE": "false", "NO_PROXY": "*",
    })
    return environment


def _package_tree_digest(root: Path) -> str:
    if not root.is_absolute() or not root.is_dir():
        raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE")
    pending = [(root, "")]
    files: list[dict[str, object]] = []
    while pending:
        directory, prefix = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                if entry.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise BuildBlocked("BLOCKED_BUILD_TOOL_REPARSE_POINT")
                relative = f"{prefix}{entry.name}"
                if stat.S_ISDIR(info.st_mode):
                    pending.append((Path(entry.path), relative + "/"))
                elif stat.S_ISREG(info.st_mode):
                    files.append({
                        "path": relative, "size": info.st_size,
                        "sha256": _sha256(Path(entry.path)),
                    })
                else:
                    raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE")
                if len(files) > 20000:
                    raise BuildBlocked("BLOCKED_BUILD_TOOL_TOO_LARGE")
    if not files:
        raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE")
    return _canonical_digest(sorted(files, key=lambda item: str(item["path"])))


def _tool_versions(syft: str) -> dict[str, object]:
    if f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}" != PYTHON_VERSION:
        raise BuildBlocked("BLOCKED_PYTHON_VERSION_UNAVAILABLE")
    for distribution, expected in (
        ("pyinstaller", PYINSTALLER_VERSION),
    ):
        try:
            actual = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE") from None
        if actual != expected:
            raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE")
    if not syft or not Path(syft).is_absolute() or not Path(syft).is_file():
        raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE")
    backend, _windows = require_windows_security()
    try:
        syft_path = Path(syft).resolve(strict=True)
        python_path = Path(sys.executable).resolve(strict=True)
        spec = importlib.util.find_spec("PyInstaller")
        if spec is None or not spec.origin or not spec.submodule_search_locations:
            raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE")
        pyinstaller_root = Path(next(iter(spec.submodule_search_locations))).resolve(strict=True)
        pyinstaller_main = pyinstaller_root / "__main__.py"
        for path in (syft_path, python_path, pyinstaller_main):
            if not path.is_file():
                raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE")
            backend.inspect_private_path(path, purpose="toolchain-executable")
        identity = {
            "name": "PyInstaller", "version": PYINSTALLER_VERSION,
            "python_version": PYTHON_VERSION,
            "python": {"path": str(python_path), "sha256": _sha256(python_path)},
            "pyinstaller": {
                "module_path": str(pyinstaller_main),
                "module_sha256": _sha256(pyinstaller_main),
                "package_tree_sha256": _package_tree_digest(pyinstaller_root),
            },
            "syft": {"version": SYFT_VERSION, "path": str(syft_path),
                     "sha256": _sha256(syft_path)},
        }
    except (OSError, RuntimeError, ValueError):
        raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE") from None
    try:
        result = subprocess.run(
            [str(syft_path), "version"], capture_output=True, text=True, check=False,
            timeout=15, stdin=subprocess.DEVNULL,
            env=_offline_environment(),
        )
    except (OSError, subprocess.TimeoutExpired):
        raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE") from None
    if result.returncode or not re.search(rf"\b{re.escape(SYFT_VERSION)}\b", result.stdout):
        raise BuildBlocked("BLOCKED_PINNED_BUILD_TOOL_UNAVAILABLE")
    if (
        _sha256(python_path) != identity["python"]["sha256"]
        or _sha256(pyinstaller_main) != identity["pyinstaller"]["module_sha256"]
        or _package_tree_digest(pyinstaller_root)
        != identity["pyinstaller"]["package_tree_sha256"]
        or _sha256(syft_path) != identity["syft"]["sha256"]
    ):
        raise BuildBlocked("BLOCKED_BUILD_TOOL_DRIFT")
    return identity


def _run_offline(
    argv: list[str], *, code: str, cwd: Path,
) -> None:
    environment = _offline_environment()
    try:
        result = subprocess.run(
            argv, capture_output=True, check=False, timeout=600,
            stdin=subprocess.DEVNULL, env=environment, cwd=cwd,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise BuildBlocked(code) from None
    if result.returncode:
        raise BuildBlocked(code)


def _archive_head(repo: Path, destination: Path) -> None:
    try:
        executable = _trusted_git_executable()
        with destination.open("xb") as stream:
            result = subprocess.run(
                [str(executable), "--no-optional-locks", "-c",
                 f"safe.directory={repo.resolve()}", "-C", str(repo),
                 "archive", "--format=tar", "HEAD"],
                stdout=stream, stderr=subprocess.DEVNULL, check=False,
                timeout=120, stdin=subprocess.DEVNULL, env=_git_environment(),
            )
        if result.returncode or destination.stat().st_size == 0:
            raise BuildBlocked("BLOCKED_SOURCE_ARCHIVE_UNAVAILABLE")
        with tarfile.open(destination, "r:") as archive:
            names = set(archive.getnames())
            if not {SOURCE, RESOURCE, "LICENSE", "NOTICE",
                    "scripts/build_m365_current_state_read_driver.py"} <= names:
                raise BuildBlocked("BLOCKED_SOURCE_ARCHIVE_INCOMPLETE")
    except (OSError, tarfile.TarError, subprocess.TimeoutExpired):
        raise BuildBlocked("BLOCKED_SOURCE_ARCHIVE_UNAVAILABLE") from None


def _real_syft_mapping(cyclonedx: Path, spdx: Path, bundle_paths: set[str]):
    """Read Syft's actual package links; bundle coverage is a separate gate."""
    sys.path.insert(0, str(ROOT / "src"))
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from nac_bff.current_state_read_driver_sbom import (
        SbomMappingError, parse_syft_sboms,
    )
    try:
        return parse_syft_sboms(
            json.loads(cyclonedx.read_text(encoding="utf-8")),
            json.loads(spdx.read_text(encoding="utf-8")), bundle_paths,
        )
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, SbomMappingError):
        raise BuildBlocked("BLOCKED_SBOM_BUNDLE_MAPPING") from None


def validate_license_inventory(
    inventory: object, bundle_paths: set[str], cdx_refs: set[str],
    spdx_refs: set[str], *, text_hashes: dict[str, str],
) -> None:
    if not isinstance(inventory, dict) or set(inventory) != {"schema_version", "components", "files"}:
        raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
    if inventory["schema_version"] != LICENSE_SCHEMA:
        raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
    components = inventory["components"]
    files = inventory["files"]
    if not isinstance(components, list) or not components or not isinstance(files, list) or not files:
        raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INCOMPLETE")
    known: set[str] = set()
    inventoried_cdx_refs: set[str] = set()
    inventoried_spdx_refs: set[str] = set()
    for component in components:
        if not isinstance(component, dict) or set(component) != {
            "id", "name", "version", "license", "license_text_path",
            "license_text_sha256", "cyclonedx_ref", "spdx_id",
        }:
            raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
        identifier = component["id"]
        if not isinstance(identifier, str) or not _SAFE_COMPONENT.fullmatch(identifier) or identifier in known:
            raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
        known.add(identifier)
        if any(not isinstance(component[key], str) or not component[key]
               or len(component[key]) > 160 or any(ord(char) < 32 for char in component[key])
               for key in ("name", "version", "license")):
            raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
        text_path = _safe_relative(component["license_text_path"])
        if text_path != "LICENSE" and not (
            text_path.startswith("licenses/") and len(text_path.split("/")) == 2
        ):
            raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
        if (not isinstance(component["license_text_sha256"], str)
                or not _HEX64.fullmatch(component["license_text_sha256"])
                or text_hashes.get(text_path) != component["license_text_sha256"]):
            raise BuildBlocked("BLOCKED_LICENSE_TEXT_MISMATCH")
        cdx_ref, spdx_id = component["cyclonedx_ref"], component["spdx_id"]
        if (cdx_ref is None) != (spdx_id is None):
            raise BuildBlocked("BLOCKED_LICENSE_SBOM_REFERENCE")
        if cdx_ref is not None:
            if (not isinstance(cdx_ref, str) or not isinstance(spdx_id, str)
                    or cdx_ref not in cdx_refs or spdx_id not in spdx_refs
                    or cdx_ref in inventoried_cdx_refs
                    or spdx_id in inventoried_spdx_refs):
                raise BuildBlocked("BLOCKED_LICENSE_SBOM_REFERENCE")
            inventoried_cdx_refs.add(cdx_ref)
            inventoried_spdx_refs.add(spdx_id)
    if inventoried_cdx_refs != cdx_refs or inventoried_spdx_refs != spdx_refs:
        raise BuildBlocked("BLOCKED_LICENSE_SBOM_REFERENCE")
    observed: set[str] = set()
    used: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "component_ids"}:
            raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
        name = _safe_relative(item["path"])
        identifiers = item["component_ids"]
        if (name in observed or not isinstance(identifiers, list) or not identifiers
                or any(not isinstance(identifier, str) or identifier not in known
                       for identifier in identifiers)
                or len(identifiers) != len(set(identifiers))):
            raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
        observed.add(name)
        used.update(identifiers)
    if observed != bundle_paths or used != known:
        raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INCOMPLETE")
    if not any(
        component["id"] == "nac"
        and component["license"] == "AGPL-3.0-or-later"
        and component["license_text_path"] == "LICENSE"
        for component in components
    ):
        raise BuildBlocked("BLOCKED_NAC_LICENSE_BINDING")


def validate_inventory_bundle_mapping(
    inventory: dict, bindings: object,
) -> None:
    """Reject an inventory that assigns a real SBOM component to a wrong file."""
    if not hasattr(bindings, "file_packages") or not hasattr(bindings, "packages"):
        raise BuildBlocked("BLOCKED_LICENSE_SBOM_FILE_MISMATCH")
    components = {item["id"]: item for item in inventory["components"]}
    records = {item["spdx_id"]: item for item in bindings.packages}
    from nac_bff.current_state_read_driver_sbom import (
        SbomMappingError, require_inventory_file_attribution,
    )
    try:
        require_inventory_file_attribution(inventory["files"], components, bindings)
    except (SbomMappingError, KeyError, TypeError):
        raise BuildBlocked("BLOCKED_LICENSE_SBOM_FILE_MISMATCH") from None
    for item in inventory["components"]:
        spdx_id = item["spdx_id"]
        if spdx_id is None:
            continue
        record = records.get(spdx_id)
        if (record is None or item["cyclonedx_ref"] != record["cyclonedx_ref"]
                or item["name"] != record["name"]
                or item["version"] != record["version"]):
            raise BuildBlocked("BLOCKED_LICENSE_SBOM_REFERENCE")


def validate_reviewed_license_catalog(
    catalog: object, inventory: object, bundle_paths: set[str], *, expected_tree: str,
    reviewed_preparation: dict[str, object] | None = None,
) -> None:
    """Bind operator evidence to a separately versioned, reviewable source catalog.

    A hash of operator-supplied text is not evidence of its claimed license.  The
    catalog is part of the bound Git tree and must explicitly approve every
    component, source digest, and runtime-file attribution before release.
    """
    blocked = "BLOCKED_LICENSE_PROVENANCE"
    if (
        not isinstance(catalog, dict)
        or set(catalog) != {"schema_version", "status", "reviewed_preparation", "components", "files"}
        or catalog["schema_version"] != LICENSE_CATALOG_SCHEMA
        or catalog["status"] != "APPROVED"
        or not isinstance(catalog["components"], list)
        or not catalog["components"]
        or not isinstance(catalog["files"], list)
        or not catalog["files"]
        or not isinstance(inventory, dict)
        or inventory.get("schema_version") != LICENSE_SCHEMA
        or not isinstance(inventory.get("components"), list)
        or not isinstance(inventory.get("files"), list)
        or not isinstance(expected_tree, str)
        or _HEX40.fullmatch(expected_tree) is None
        or not isinstance(catalog["reviewed_preparation"], dict)
        or catalog["reviewed_preparation"] != reviewed_preparation
    ):
        raise BuildBlocked(blocked)
    catalog_components = {}
    for item in catalog["components"]:
        if not isinstance(item, dict) or set(item) != {
            "id", "name", "version", "license", "license_text_path",
            "license_text_sha256", "source_uri", "source_sha256",
        }:
            raise BuildBlocked(blocked)
        identifier = item["id"]
        if not isinstance(identifier, str) or _SAFE_COMPONENT.fullmatch(identifier) is None:
            raise BuildBlocked(blocked)
        if identifier in catalog_components:
            raise BuildBlocked(blocked)
        for field in ("name", "version", "license"):
            value = item[field]
            if (not isinstance(value, str) or not value or len(value) > 160
                    or any(ord(character) < 32 for character in value)):
                raise BuildBlocked(blocked)
        try:
            text_path = _safe_relative(item["license_text_path"])
        except BuildBlocked:
            raise BuildBlocked(blocked) from None
        if text_path != "LICENSE" and not (
            text_path.startswith("licenses/") and len(text_path.split("/")) == 2
        ):
            raise BuildBlocked(blocked)
        if (not isinstance(item["license_text_sha256"], str)
                or _HEX64.fullmatch(item["license_text_sha256"]) is None
                or item["license_text_sha256"] == "0" * 64):
            raise BuildBlocked(blocked)
        if identifier == "nac":
            if (item["source_uri"] != "git:HEAD"
                    or item["source_sha256"] != "BOUND_SOURCE_TREE"
                    or item["license"] != "AGPL-3.0-or-later"
                    or text_path != "LICENSE"):
                raise BuildBlocked(blocked)
        else:
            uri = item["source_uri"]
            digest = item["source_sha256"]
            if not isinstance(uri, str) or len(uri) > 240:
                raise BuildBlocked(blocked)
            parsed = urlsplit(uri)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                    or parsed.password or parsed.query or parsed.fragment
                    or not isinstance(digest, str) or _HEX64.fullmatch(digest) is None
                     or digest == "0" * 64
                     or item["license"].upper() in {
                         "NOASSERTION", "UNKNOWN", "PENDING", "TBD", "NONE", "N/A",
                     }):
                raise BuildBlocked(blocked)
        catalog_components[identifier] = item
    inventory_components = {}
    for item in inventory["components"]:
        if not isinstance(item, dict) or set(item) != {
            "id", "name", "version", "license", "license_text_path",
            "license_text_sha256", "cyclonedx_ref", "spdx_id",
        }:
            raise BuildBlocked(blocked)
        identifier = item["id"]
        if identifier in inventory_components or identifier not in catalog_components:
            raise BuildBlocked(blocked)
        if any(item[field] != catalog_components[identifier][field]
               for field in (
                   "name", "version", "license", "license_text_path",
                   "license_text_sha256",
               )):
            raise BuildBlocked(blocked)
        inventory_components[identifier] = item
    if set(inventory_components) != set(catalog_components):
        raise BuildBlocked(blocked)
    expected_files = {}
    for item in catalog["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "component_ids"}:
            raise BuildBlocked(blocked)
        try:
            path = _safe_relative(item["path"])
        except BuildBlocked:
            raise BuildBlocked(blocked) from None
        identifiers = item["component_ids"]
        if (path in expected_files or not isinstance(identifiers, list)
                or not identifiers or any(not isinstance(identifier, str)
                                       for identifier in identifiers)
                or len(identifiers) != len(set(identifiers))
                or any(not isinstance(identifier, str)
                       or identifier not in catalog_components
                       for identifier in identifiers)):
            raise BuildBlocked(blocked)
        expected_files[path] = set(identifiers)
    if set(expected_files) != bundle_paths:
        raise BuildBlocked(blocked)
    observed_files = {}
    for item in inventory["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "component_ids"}:
            raise BuildBlocked(blocked)
        path, identifiers = item["path"], item["component_ids"]
        if (not isinstance(path, str) or path in observed_files
                or not isinstance(identifiers, list)
                or any(not isinstance(identifier, str) for identifier in identifiers)
                or len(identifiers) != len(set(identifiers))):
            raise BuildBlocked(blocked)
        observed_files[path] = set(identifiers)
    if observed_files != expected_files:
        raise BuildBlocked(blocked)


def _bundle_paths(bundle: Path) -> set[str]:
    sys.path.insert(0, str(ROOT / "src"))
    from nac_bff.current_state_read_driver import _bundle_paths as enumerate_bundle
    files, directories = enumerate_bundle(bundle)
    if "reader.exe" not in files or len(files) > 4096:
        raise BuildBlocked("BLOCKED_BUNDLE_INCOMPLETE")
    for directory in directories:
        _safe_relative(directory)
    return files


def _remove_build_temp(candidate: Path, target: Path) -> None:
    """Remove only known generated scratch children beneath this candidate."""
    root = candidate.resolve(strict=True)
    resolved = target.resolve(strict=True)
    if resolved.parent != root or resolved.name not in {"work", "bundle-stage"}:
        raise BuildBlocked("BLOCKED_BUILD_TEMP_SCOPE")
    shutil.rmtree(resolved)


def prepare_candidate(
    *, repo: Path, output: Path, expected_head: str, expected_tree: str,
    syft: str,
) -> Path:
    require_candidate_contract_gate(repo, phase="prepare")
    backend, windows = require_windows_security()
    if repo.resolve() != ROOT.resolve():
        raise BuildBlocked("BLOCKED_SOURCE_REPOSITORY_MISMATCH")
    candidate = validate_output_path(repo, output)
    validate_source_state(repo, expected_head, expected_tree)
    tool = _tool_versions(syft)
    source_code = (repo / SOURCE).read_text(encoding="utf-8")
    if 'if __name__ == "__main__"' not in source_code:
        raise BuildBlocked("BLOCKED_DRIVER_ENTRYPOINT_UNAVAILABLE")
    # The output path is exclusively new. A failed run leaves an incomplete
    # candidate without release.json; it is never overwritten automatically.
    candidate.mkdir(mode=0o700)
    _seal_tree_current_user_only(candidate, backend, windows)
    archive = candidate / "source.tar"
    _archive_head(repo, archive)
    bundle_stage = candidate / "bundle-stage"
    work = candidate / "work"
    build_command = [
        tool["python"]["path"], "-m", "PyInstaller", "--onedir", "--name", "reader",
        "--distpath", str(bundle_stage), "--workpath", str(work),
        "--specpath", str(work), "--paths", str(repo / "src"),
        str(repo / SOURCE),
    ]
    _run_offline(build_command, code="BLOCKED_PYINSTALLER_BUILD_FAILED", cwd=candidate)
    built = bundle_stage / "reader"
    if not built.is_dir() or not (built / "reader.exe").is_file():
        raise BuildBlocked("BLOCKED_BUNDLE_INCOMPLETE")
    built.rename(candidate / "bundle")
    _remove_build_temp(candidate, bundle_stage)
    _remove_build_temp(candidate, work)
    sbom_commands = {
        "cyclonedx": [
            tool["syft"]["path"], f"dir:{candidate / 'bundle'}", "-o",
            f"cyclonedx-json={candidate / 'cyclonedx.json'}",
        ],
        "spdx": [
            tool["syft"]["path"], f"dir:{candidate / 'bundle'}", "-o",
            f"spdx-json={candidate / 'spdx.json'}",
        ],
    }
    _run_offline(
        sbom_commands["cyclonedx"],
        code="BLOCKED_CYCLONEDX_GENERATION_FAILED", cwd=candidate,
    )
    _run_offline(
        sbom_commands["spdx"], code="BLOCKED_SPDX_GENERATION_FAILED",
        cwd=candidate,
    )
    for name in ("LICENSE", "NOTICE"):
        shutil.copyfile(repo / name, candidate / name)
    paths = _bundle_paths(candidate / "bundle")
    preparation = {
        "schema_version": PREPARATION_SCHEMA,
        "status": "AWAITING_INDEPENDENT_LICENSE_EVIDENCE",
        "source_commit": expected_head,
        "source_tree": expected_tree,
        "build_tool": tool,
        "build_command": build_command,
        "sbom_commands": sbom_commands,
        "artifacts": {
            name: _sha256(candidate / name)
            for name in ("source.tar", "cyclonedx.json", "spdx.json", "LICENSE", "NOTICE")
        },
        "bundle_files": [
            {"path": name, "sha256": _sha256(candidate / "bundle" / Path(name))}
            for name in sorted(paths)
        ],
    }
    _write_json(candidate / "preparation.json", preparation)
    _seal_tree_current_user_only(candidate, backend, windows)
    validate_source_state(repo, expected_head, expected_tree)
    return candidate


def _reviewed_catalog(repo: Path) -> dict:
    try:
        catalog = json.loads((repo / LICENSE_CATALOG).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise BuildBlocked("BLOCKED_LICENSE_PROVENANCE") from None
    if not isinstance(catalog, dict) or catalog.get("status") != "APPROVED":
        raise BuildBlocked("BLOCKED_LICENSE_PROVENANCE")
    return catalog


def require_candidate_contract_gate(repo: Path, *, phase: str = "release") -> None:
    """Keep offline preparation separate from release-candidate finalization."""
    try:
        contract = json.loads((repo / "workflows/verification-contracts"
                               / "m365-current-state-read-driver.verification.json")
                              .read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise BuildBlocked("BLOCKED_RELEASE_CANDIDATE_NOT_AUTHORIZED") from None
    permission = {
        "prepare": "repository_external_preparation_candidate",
        "release": "repository_external_release_candidate",
    }.get(phase)
    if (permission is None or not isinstance(contract, dict)
            or not isinstance(contract.get("side_effects_allowed_offline"), dict)
            or contract["side_effects_allowed_offline"].get(permission) is not True):
        raise BuildBlocked("BLOCKED_RELEASE_CANDIDATE_NOT_AUTHORIZED")


def finalize_candidate(
    *, repo: Path, candidate: Path, expected_head: str, expected_tree: str,
    license_evidence: Path, syft: str,
) -> Path:
    require_candidate_contract_gate(repo)
    backend, windows = require_windows_security()
    if repo.resolve() != ROOT.resolve() or not candidate.is_absolute():
        raise BuildBlocked("BLOCKED_SOURCE_REPOSITORY_MISMATCH")
    if candidate.is_symlink():
        raise BuildBlocked("BLOCKED_CANDIDATE_ACL_SEAL_FAILED")
    candidate = candidate.resolve(strict=True)
    if repo.resolve() == candidate or repo.resolve() in candidate.parents:
        raise BuildBlocked("BLOCKED_OUTPUT_INSIDE_REPOSITORY")
    validate_source_state(repo, expected_head, expected_tree)
    catalog = _reviewed_catalog(repo)
    if (not license_evidence.is_absolute() or not license_evidence.is_dir()
            or license_evidence.is_symlink()):
        raise BuildBlocked("BLOCKED_LICENSE_EVIDENCE_UNAVAILABLE")
    backend.validate_current_user_only_directory(license_evidence)
    if any(part.is_symlink() for part in (candidate, candidate / "bundle")):
        raise BuildBlocked("BLOCKED_CANDIDATE_ACL_SEAL_FAILED")
    backend.validate_current_user_only_directory(candidate)
    backend.validate_current_user_only_directory(candidate / "bundle")
    prepared_names = {entry.name for entry in os.scandir(candidate)}
    if prepared_names != {
        "bundle", "source.tar", "cyclonedx.json", "spdx.json",
        "LICENSE", "NOTICE", "preparation.json",
    }:
        raise BuildBlocked("BLOCKED_PREPARATION_DRIFT")
    try:
        preparation = json.loads((candidate / "preparation.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise BuildBlocked("BLOCKED_PREPARATION_DRIFT") from None
    tool = _tool_versions(syft)
    bundle_stage, work = candidate / "bundle-stage", candidate / "work"
    build_command = [
        tool["python"]["path"], "-m", "PyInstaller", "--onedir", "--name", "reader",
        "--distpath", str(bundle_stage), "--workpath", str(work),
        "--specpath", str(work), "--paths", str(repo / "src"), str(repo / SOURCE),
    ]
    sbom_commands = {
        "cyclonedx": [tool["syft"]["path"], f"dir:{candidate / 'bundle'}", "-o",
                      f"cyclonedx-json={candidate / 'cyclonedx.json'}"],
        "spdx": [tool["syft"]["path"], f"dir:{candidate / 'bundle'}", "-o",
                 f"spdx-json={candidate / 'spdx.json'}"],
    }
    paths = _bundle_paths(candidate / "bundle")
    expected_preparation = {
        "schema_version": PREPARATION_SCHEMA,
        "status": "AWAITING_INDEPENDENT_LICENSE_EVIDENCE",
        "source_commit": expected_head,
        "source_tree": expected_tree,
        "build_tool": tool,
        "build_command": build_command,
        "sbom_commands": sbom_commands,
        "artifacts": {
            name: _sha256(candidate / name)
            for name in ("source.tar", "cyclonedx.json", "spdx.json", "LICENSE", "NOTICE")
        },
        "bundle_files": [
            {"path": name, "sha256": _sha256(candidate / "bundle" / Path(name))}
            for name in sorted(paths)
        ],
    }
    if preparation != expected_preparation:
        raise BuildBlocked("BLOCKED_PREPARATION_DRIFT")
    try:
        with tarfile.open(candidate / "source.tar", "r:") as archive:
            selected = archive.getmember(LICENSE_CATALOG)
            if not selected.isfile():
                raise BuildBlocked("BLOCKED_PREPARATION_DRIFT")
            source = archive.extractfile(selected)
            if source is None or source.read() != (repo / LICENSE_CATALOG).read_bytes():
                raise BuildBlocked("BLOCKED_PREPARATION_DRIFT")
    except (OSError, KeyError, tarfile.TarError):
        raise BuildBlocked("BLOCKED_PREPARATION_DRIFT") from None
    evidence_inventory = license_evidence / "license-inventory.json"
    if not evidence_inventory.is_file() or evidence_inventory.is_symlink():
        raise BuildBlocked("BLOCKED_LICENSE_EVIDENCE_UNAVAILABLE")
    backend.inspect_private_path(
        evidence_inventory, purpose="issue748-read-driver-bundle-current-user-only",
    )
    try:
        inventory = json.loads(evidence_inventory.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise BuildBlocked("BLOCKED_LICENSE_EVIDENCE_UNAVAILABLE") from None
    text_hashes = {"LICENSE": _sha256(candidate / "LICENSE")}
    if isinstance(inventory, dict) and isinstance(inventory.get("components"), list):
        for component in inventory["components"]:
            if not isinstance(component, dict):
                raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
            relative = _safe_relative(component.get("license_text_path"))
            if relative == "LICENSE":
                continue
            if not relative.startswith("licenses/") or len(relative.split("/")) != 2:
                raise BuildBlocked("BLOCKED_LICENSE_INVENTORY_INVALID")
            source = license_evidence.joinpath(*relative.split("/"))
            if (source.is_symlink() or not source.is_file()
                    or license_evidence.resolve() not in source.resolve().parents
                    or any(parent.is_symlink() for parent in source.parents
                           if parent == license_evidence or license_evidence in parent.parents)):
                raise BuildBlocked("BLOCKED_LICENSE_TEXT_MISMATCH")
            backend.validate_current_user_only_directory(source.parent)
            backend.inspect_private_path(
                source, purpose="issue748-read-driver-bundle-current-user-only",
            )
            destination = candidate.joinpath(*relative.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            text_hashes[relative] = _sha256(destination)
    paths = _bundle_paths(candidate / "bundle")
    sbom_file_bindings = _real_syft_mapping(
        candidate / "cyclonedx.json", candidate / "spdx.json", paths,
    )
    cdx_refs = {item["cyclonedx_ref"] for item in sbom_file_bindings.packages}
    spdx_refs = {item["spdx_id"] for item in sbom_file_bindings.packages}
    validate_license_inventory(inventory, paths, cdx_refs, spdx_refs, text_hashes=text_hashes)
    validate_inventory_bundle_mapping(inventory, sbom_file_bindings)
    validate_reviewed_license_catalog(
        catalog, inventory, paths, expected_tree=expected_tree,
        reviewed_preparation={
            "driver_source_sha256": _sha256(repo / SOURCE),
            "resource_contract_sha256": _sha256(repo / RESOURCE),
            "build_tool": tool,
            "bundle_files": expected_preparation["bundle_files"],
            "cyclonedx_sha256": expected_preparation["artifacts"]["cyclonedx.json"],
            "spdx_sha256": expected_preparation["artifacts"]["spdx.json"],
            "notice_sha256": expected_preparation["artifacts"]["NOTICE"],
        },
    )
    shutil.copyfile(repo / LICENSE_CATALOG, candidate / "license-catalog.json")
    third_party = [component for component in inventory["components"]
                   if component["id"] != "nac"]
    if third_party:
        with (candidate / "NOTICE").open("a", encoding="utf-8", newline="\n") as notice:
            notice.write("\nThird-party runtime components in this candidate:\n")
            for component in sorted(third_party, key=lambda item: item["id"]):
                notice.write(
                    f"{component['name']} {component['version']} — "
                    f"{component['license']} ({component['license_text_path']})\n"
                )
    _write_json(candidate / "license-inventory.json", inventory)
    _seal_tree_current_user_only(candidate, backend, windows)
    snapshots = []
    for relative in sorted(paths):
        path = candidate / "bundle" / Path(relative)
        snapshot = backend.inspect_private_path(
            path, purpose="issue748-read-driver-bundle-current-user-only"
        )
        values = asdict(snapshot)
        if values.pop("reparse_point") is not False:
            raise BuildBlocked("BLOCKED_BUNDLE_ATTESTATION_FAILED")
        snapshots.append({"path": relative, **{name: values[name] for name in _BUNDLE_FIELDS if name != "path"}})
    from nac_bff.current_state_read_driver import verify_bundle_files
    verify_bundle_files(candidate / "bundle", snapshots, backend)
    resource_sha = _sha256(repo / RESOURCE)
    artifacts = {name: _sha256(candidate / name) for name in _ARTIFACTS}
    input_binding = {
        "source_archive_sha256": artifacts["source.tar"],
        "resource_contract_sha256": resource_sha,
        "build_tool": tool,
    }
    validate_source_state(repo, expected_head, expected_tree)
    if _tool_versions(syft) != tool:
        raise BuildBlocked("BLOCKED_BUILD_TOOL_DRIFT")
    release = {
        "schema_version": SCHEMA, "status": "CANDIDATE_BUILT",
        "source_commit": expected_head, "source_tree": expected_tree,
        "resource_contract_sha256": resource_sha,
        "entrypoint": "reader.exe", "bundle_files": snapshots,
        "artifacts": artifacts, "build_tool": tool,
        "build_command": build_command,
        "sbom_commands": sbom_commands,
        "build_inputs_sha256": _canonical_digest(input_binding),
        "byte_reproducibility_claim": False,
    }
    pending = candidate / "release.pending"
    _write_json(pending, release)
    _seal_tree_current_user_only(candidate, backend, windows)
    pending.rename(candidate / "release.json")
    try:
        backend.inspect_private_path(
            candidate / "release.json",
            purpose="issue748-read-driver-bundle-current-user-only",
        )
        backend.validate_current_user_only_directory(candidate)
    except (OSError, AttributeError, RuntimeError, ValueError, TypeError):
        (candidate / "release.json").unlink(missing_ok=True)
        raise BuildBlocked("BLOCKED_CANDIDATE_ACL_SEAL_FAILED") from None
    return candidate


def build_candidate(
    *, repo: Path, output: Path, expected_head: str, expected_tree: str,
    license_evidence: Path, syft: str,
) -> Path:
    require_candidate_contract_gate(repo)
    # Do not spend a full build or create an output when source review is still pending.
    _reviewed_catalog(repo)
    preparation = prepare_candidate(
        repo=repo, output=output, expected_head=expected_head,
        expected_tree=expected_tree, syft=syft,
    )
    return finalize_candidate(
        repo=repo, candidate=preparation, expected_head=expected_head,
        expected_tree=expected_tree, license_evidence=license_evidence, syft=syft,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("prepare", "finalize", "build"), default="build")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--license-evidence-dir", type=Path)
    parser.add_argument("--syft", default=shutil.which("syft") or "")
    args = parser.parse_args(argv)
    try:
        if args.mode == "prepare":
            if args.license_evidence_dir is not None:
                raise BuildBlocked("BLOCKED_PREPARATION_ARGUMENTS")
            result = prepare_candidate(
                repo=ROOT, output=args.output, expected_head=args.expected_head,
                expected_tree=args.expected_tree, syft=args.syft,
            )
        else:
            if args.license_evidence_dir is None:
                raise BuildBlocked("BLOCKED_LICENSE_EVIDENCE_UNAVAILABLE")
            arguments = {
                "repo": ROOT, "expected_head": args.expected_head,
                "expected_tree": args.expected_tree,
                "license_evidence": args.license_evidence_dir, "syft": args.syft,
            }
            result = (build_candidate(output=args.output, **arguments)
                      if args.mode == "build"
                      else finalize_candidate(candidate=args.output, **arguments))
    except (BuildBlocked, OSError, ValueError, TypeError) as error:
        code = error.code if isinstance(error, BuildBlocked) else "BLOCKED_CANDIDATE_BUILD_FAILED"
        print(f"STATUS: {code}")
        return 1
    print("STATUS: PREPARED_PENDING_EVIDENCE" if args.mode == "prepare"
          else "STATUS: CANDIDATE_BUILT")
    print(f"OUTPUT: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
