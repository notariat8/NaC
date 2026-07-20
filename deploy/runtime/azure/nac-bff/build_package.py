from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile


HOST_ROOT = Path(__file__).resolve().parent
REPO_ROOT = HOST_ROOT.parents[3]
SRC_ROOT = REPO_ROOT / "src"
DEFAULT_OUTPUT = HOST_ROOT / "dist/nac-bff-function.zip"

_HOST_FILES = ("function_app.py", "host.json", "requirements.txt")
_SOURCE_PACKAGES = ("nac_bff", "nac_m365_graph")
_SOURCE_MODULES = ("nac_mvp_test_environment.py",)
_ASSET_FILES = {
    "bpmn/immobilienkaufvertrag.bpmn": REPO_ROOT
    / "bpmn/immobilienkaufvertrag.bpmn",
}
_EXPECTED_ASSET_SHA256 = {
    "bpmn/immobilienkaufvertrag.bpmn": (
        "02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0"
    ),
}
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_LOCKED_IMPORTS = {
    "azure.functions": "azure-functions",
    "azure.identity": "azure-identity",
    "cryptography": "cryptography",
    "fastapi": "fastapi",
    "starlette": "starlette",
}
_FORBIDDEN_REACHABLE_AUTH_MARKERS = (
    "ClientSecretCredential",
    "CertificateCredential",
    "DefaultAzureCredential",
    "M365_CLIENT_SECRET",
    "M365_CLIENT_CERTIFICATE",
)


def _source_files() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for name in _HOST_FILES:
        path = HOST_ROOT / name
        files[name] = path.read_bytes()

    for package_name in _SOURCE_PACKAGES:
        package_root = SRC_ROOT / package_name
        for path in sorted(package_root.rglob("*.py")):
            relative_path = path.relative_to(SRC_ROOT).as_posix()
            files[relative_path] = path.read_bytes()

    for name in _SOURCE_MODULES:
        path = SRC_ROOT / name
        files[name] = path.read_bytes()
    for package_path, source_path in sorted(_ASSET_FILES.items()):
        content = source_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != _EXPECTED_ASSET_SHA256[package_path]:
            raise ValueError(f"canonical package asset hash is invalid: {package_path}")
        files[package_path] = content
    return files


def _manifest(files: dict[str, bytes]) -> bytes:
    document = {
        "formatVersion": 2,
        "pythonRuntime": "3.12",
        "deployment": {
            "technology": "oneDeploy",
            "remoteBuildRequired": True,
            "remoteBuildFlag": "--build-remote true",
            "sourcePackage": True,
        },
        "dependencyLock": {
            "path": "requirements.txt",
            "sha256": hashlib.sha256(files["requirements.txt"]).hexdigest(),
        },
        "files": [
            {
                "path": path,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            for path, content in sorted(files.items())
        ],
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_entry(package: zipfile.ZipFile, path: str, content: bytes) -> None:
    info = zipfile.ZipInfo(path, date_time=_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    package.writestr(info, content, compresslevel=9)


def build_package_bytes() -> bytes:
    files = _source_files()
    files["package-manifest.json"] = _manifest(files)

    target = io.BytesIO()
    with zipfile.ZipFile(target, mode="w") as package:
        for path, content in sorted(files.items()):
            _write_entry(package, path, content)
    return target.getvalue()


def build_package(output: Path) -> Path:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(build_package_bytes())
    return output


def validate_package(package_bytes: bytes) -> list[str]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(package_bytes), mode="r") as package:
            infos = package.infolist()
            names = [info.filename for info in infos]
            if names != sorted(names) or len(names) != len(set(names)):
                errors.append("package entries must be unique and sorted")
            for info in infos:
                mode = (info.external_attr >> 16) & 0o177777
                if (
                    info.date_time != _ZIP_TIMESTAMP
                    or info.compress_type != zipfile.ZIP_DEFLATED
                    or info.create_system != 3
                    or mode != 0o100644
                    or info.extra
                    or info.comment
                ):
                    errors.append(f"non-deterministic ZIP metadata: {info.filename}")
            files = {name: package.read(name) for name in names}
    except (OSError, ValueError, zipfile.BadZipFile):
        return ["package is not a readable ZIP archive"]

    _validate_manifest(files, errors)
    _validate_assets(files, errors)
    locked = _locked_distributions(files.get("requirements.txt", b""), errors)
    _validate_python_import_closure(files, locked, errors)
    return errors


def _validate_assets(files: dict[str, bytes], errors: list[str]) -> None:
    for path, expected_hash in sorted(_EXPECTED_ASSET_SHA256.items()):
        content = files.get(path)
        if content is None or hashlib.sha256(content).hexdigest() != expected_hash:
            errors.append(f"canonical package asset is missing or invalid: {path}")


def _validate_manifest(files: dict[str, bytes], errors: list[str]) -> None:
    try:
        manifest = json.loads(files["package-manifest.json"].decode("utf-8"))
    except (KeyError, UnicodeError, json.JSONDecodeError):
        errors.append("package manifest is missing or invalid")
        return
    payload_files = {
        path: content
        for path, content in files.items()
        if path != "package-manifest.json"
    }
    expected_entries = [
        {"path": path, "sha256": hashlib.sha256(content).hexdigest()}
        for path, content in sorted(payload_files.items())
    ]
    expected_lock_hash = hashlib.sha256(
        payload_files.get("requirements.txt", b"")
    ).hexdigest()
    if manifest.get("formatVersion") != 2 or manifest.get("pythonRuntime") != "3.12":
        errors.append("package manifest format or Python runtime is invalid")
    if manifest.get("deployment") != {
        "technology": "oneDeploy",
        "remoteBuildRequired": True,
        "remoteBuildFlag": "--build-remote true",
        "sourcePackage": True,
    }:
        errors.append("source package must require Flex OneDeploy remote build")
    if manifest.get("files") != expected_entries:
        errors.append("package manifest does not exactly bind every payload file")
    if manifest.get("dependencyLock") != {
        "path": "requirements.txt",
        "sha256": expected_lock_hash,
    }:
        errors.append("package manifest does not bind the dependency lock")


def _locked_distributions(content: bytes, errors: list[str]) -> set[str]:
    try:
        text = content.decode("utf-8")
    except UnicodeError:
        errors.append("dependency lock is not UTF-8")
        return set()
    logical_lines: list[str] = []
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        current = f"{current} {line}".strip()
        if current.endswith("\\"):
            current = current[:-1].rstrip()
            continue
        logical_lines.append(current)
        current = ""
    if current:
        logical_lines.append(current)

    locked: set[str] = set()
    requirement_pattern = re.compile(
        r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)(.*)$"
    )
    hash_pattern = re.compile(r"--hash=sha256:[0-9a-f]{64}")
    for line in logical_lines:
        match = requirement_pattern.fullmatch(line)
        if match is None or not hash_pattern.search(match.group(3)):
            errors.append("dependency lock contains an unpinned or unhashed entry")
            continue
        name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
        if name in locked:
            errors.append(f"dependency lock contains a duplicate distribution: {name}")
        locked.add(name)
    if not locked:
        errors.append("dependency lock is empty")
    return locked


def _validate_python_import_closure(
    files: dict[str, bytes],
    locked: set[str],
    errors: list[str],
) -> None:
    modules: dict[str, tuple[str, ast.AST, str]] = {}
    for path, content in sorted(files.items()):
        if not path.endswith(".py"):
            continue
        module = path[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[: -len(".__init__")]
        try:
            source = content.decode("utf-8")
            tree = ast.parse(source, filename=path)
            compile(source, path, "exec")
        except (UnicodeError, SyntaxError):
            errors.append(f"packaged Python source does not compile: {path}")
            continue
        modules[module] = (path, tree, source)

    if "function_app" not in modules:
        errors.append("function_app import root is missing")
        return

    first_party_roots = {name.split(".", 1)[0] for name in modules}
    pending = ["function_app"]
    visited: set[str] = set()

    def enqueue(name: str) -> None:
        if not name:
            return
        parts = name.split(".")
        for index in range(1, len(parts)):
            package_name = ".".join(parts[:index])
            if package_name in modules and package_name not in visited:
                pending.append(package_name)
        if name in modules:
            if name not in visited:
                pending.append(name)
            return
        if parts[0] in first_party_roots:
            errors.append(f"packaged first-party import is missing: {name}")
            return
        if parts[0] in sys.stdlib_module_names:
            return
        distribution = _distribution_for_import(name)
        if distribution is None or distribution not in locked:
            errors.append(f"external import is not represented in the lock: {name}")

    while pending:
        module = pending.pop()
        if module in visited or module not in modules:
            continue
        visited.add(module)
        path, tree, source = modules[module]
        if any(marker in source for marker in _FORBIDDEN_REACHABLE_AUTH_MARKERS):
            errors.append(
                f"reachable package module contains a forbidden credential path: {path}"
            )
        package = module if path.endswith("/__init__.py") else module.rpartition(".")[0]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    enqueue(alias.name)
            elif isinstance(node, ast.ImportFrom):
                imported = _resolve_import_from(package, node)
                enqueue(imported)
                for alias in node.names:
                    candidate = f"{imported}.{alias.name}" if imported else alias.name
                    if candidate in modules:
                        enqueue(candidate)


def _resolve_import_from(package: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    parts = package.split(".") if package else []
    keep = len(parts) - node.level + 1
    if keep < 0:
        return ""
    prefix = parts[:keep]
    if node.module:
        prefix.extend(node.module.split("."))
    return ".".join(prefix)


def _distribution_for_import(name: str) -> str | None:
    for prefix, distribution in sorted(
        _LOCKED_IMPORTS.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if name == prefix or name.startswith(prefix + "."):
            return distribution
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the deterministic NaC BFF Azure Function source package."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"ZIP path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()
    output = build_package(args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
