"""Closed, offline-reviewable Issue #748 read-driver core.

There is deliberately no Microsoft transport in this module. The production
factory blocks before invoking credentials or a network client until a
separately reviewed, technically enforceable no-refresh capability exists.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any


class ReadDriverBlocked(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_OPAQUE = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")
_VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){1,3}\Z")
_FIELDS = {
    "client_observation_receipt": frozenset(
        {"ui_state", "spfx_subject_available", "client_receipt_sha256"}
    ),
    "teams_tab_metadata": frozenset({"contract_matches", "version_binding"}),
    "sharepoint_app_catalog": frozenset(
        {"package_version", "package_digest", "api_permission_match"}
    ),
    "entra_api_permission": frozenset(
        {"tenant_match", "audience_match", "scope_match", "preauthorization_match"}
    ),
    "azure_function_metadata": frozenset(
        {"deployment_class", "configuration_digest"}
    ),
    "azure_function_request_log": frozenset(
        {"request_observed", "http_class", "request_correlation_binding_sha256"}
    ),
    "sharepoint_access_decision": frozenset({"evidence_matches"}),
}
_BUNDLE_FIELDS = frozenset({
    "path", "sha256", "size", "volume_serial", "file_id",
    "owner_sid_sha256", "dacl_sha256", "security_descriptor_sha256",
    "path_sha256",
})


def _bundle_paths(root: Path) -> tuple[set[str], set[str]]:
    """Enumerate without following links or Windows reparse-point directories."""
    files: set[str] = set()
    directories: set[str] = set()
    pending = [(root, "")]
    while pending:
        directory, prefix = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                relative = f"{prefix}{entry.name}"
                attributes = entry.stat(follow_symlinks=False)
                if (
                    entry.is_symlink()
                    or getattr(attributes, "st_file_attributes", 0) & 0x400
                ):
                    raise ReadDriverBlocked("BLOCKED_DRIVER_RELEASE_BINDING")
                if stat.S_ISDIR(attributes.st_mode):
                    directories.add(relative)
                    pending.append((Path(entry.path), relative + "/"))
                elif stat.S_ISREG(attributes.st_mode):
                    # Link count is checked by the handle-bound security backend;
                    # os.stat may report zero in restricted Windows contexts.
                    files.add(relative)
                else:
                    raise ReadDriverBlocked("BLOCKED_DRIVER_RELEASE_BINDING")
                if len(files) + len(directories) > 4096:
                    raise ReadDriverBlocked("BLOCKED_DRIVER_RELEASE_BINDING")
    return files, directories


def verify_bundle_files(
    bundle_root: Path, file_manifest: object, backend: object,
    *, entrypoint: str = "reader.exe",
) -> str:
    """Bind every local Windows runtime file before any one-shot gate consume.

    Manifest file identities are local installation evidence, not portable
    identities for a copied bundle. The backend must enforce the stricter
    current-user-only DACL purpose as well as handle-bound hash and link checks.
    """
    blocked = "BLOCKED_DRIVER_RELEASE_BINDING"
    if not isinstance(bundle_root, Path) or not bundle_root.is_absolute():
        raise ReadDriverBlocked(blocked)
    if not isinstance(file_manifest, list) or not file_manifest or len(file_manifest) > 4096:
        raise ReadDriverBlocked(blocked)
    expected: dict[str, Mapping[str, Any]] = {}
    for item in file_manifest:
        if not isinstance(item, Mapping) or frozenset(item) != _BUNDLE_FIELDS:
            raise ReadDriverBlocked(blocked)
        name = item["path"]
        if (
            not isinstance(name, str) or not name or len(name) > 240
            or "\\" in name or ":" in name or name.startswith("/")
            or any(part in {"", ".", ".."} for part in name.split("/"))
            or PurePosixPath(name).is_absolute()
            or name.casefold() in (path.casefold() for path in expected)
        ):
            raise ReadDriverBlocked(blocked)
        if not _hex(item["sha256"]) or any(
            not _hex(item[field]) for field in (
                "owner_sid_sha256", "dacl_sha256",
                "security_descriptor_sha256", "path_sha256",
            )
        ) or any(
            type(item[field]) is not int or item[field] < 0
            for field in ("size", "volume_serial", "file_id")
        ):
            raise ReadDriverBlocked(blocked)
        expected[name] = item
    if entrypoint not in expected:
        raise ReadDriverBlocked(blocked)
    expected_directories = {
        "/".join(parts[:index])
        for name in expected
        for parts in [name.split("/")]
        for index in range(1, len(parts))
    }
    try:
        operator = backend.current_operator_binding()
        files, directories = _bundle_paths(bundle_root)
        if files != set(expected) or directories != expected_directories:
            raise ReadDriverBlocked(blocked)
        backend.validate_current_user_only_directory(bundle_root)
        for name in sorted(directories):
            backend.validate_current_user_only_directory(
                bundle_root.joinpath(*name.split("/"))
            )
        for name, item in expected.items():
            snapshot = backend.inspect_private_path(
                bundle_root.joinpath(*name.split("/")),
                purpose="issue748-read-driver-bundle-current-user-only",
            )
            if (
                snapshot.reparse_point is not False
                or snapshot.owner_sid_sha256 != operator.sid_sha256
                or any(getattr(snapshot, field) != item[field] for field in _BUNDLE_FIELDS - {"path"})
            ):
                raise ReadDriverBlocked(blocked)
        if _bundle_paths(bundle_root) != (files, directories):
            raise ReadDriverBlocked(blocked)
    except (AttributeError, OSError, RuntimeError, ValueError, TypeError):
        raise ReadDriverBlocked(blocked) from None
    return str(expected[entrypoint]["sha256"])


def _hex(value: object) -> bool:
    return isinstance(value, str) and _HEX64.fullmatch(value) is not None


def _boolean(value: object) -> bool:
    return type(value) is bool


def validate_redacted_projection(
    operation: str, data: Mapping[str, Any]
) -> dict[str, Any]:
    """Accept only neutral fields and closed scalar values, never raw payloads."""
    expected = _FIELDS.get(operation)
    if expected is None:
        raise ReadDriverBlocked("BLOCKED_RESOURCE_NOT_ALLOWLISTED")
    if not isinstance(data, Mapping) or frozenset(data) != expected:
        raise ReadDriverBlocked("BLOCKED_RESPONSE_REDACTION")
    valid = False
    if operation == "client_observation_receipt":
        valid = (
            data["ui_state"] == "no_access"
            and _boolean(data["spfx_subject_available"])
            and _hex(data["client_receipt_sha256"])
        )
    elif operation == "teams_tab_metadata":
        valid = (
            _boolean(data["contract_matches"])
            and isinstance(data["version_binding"], str)
            and _SAFE_OPAQUE.fullmatch(data["version_binding"]) is not None
        )
    elif operation == "sharepoint_app_catalog":
        valid = (
            isinstance(data["package_version"], str)
            and _VERSION.fullmatch(data["package_version"]) is not None
            and _hex(data["package_digest"])
            and _boolean(data["api_permission_match"])
        )
    elif operation == "entra_api_permission":
        valid = all(_boolean(value) for value in data.values())
    elif operation == "azure_function_metadata":
        valid = (
            isinstance(data["deployment_class"], str)
            and
            data["deployment_class"] in {"deployed", "not_deployed"}
            and _hex(data["configuration_digest"])
        )
    elif operation == "azure_function_request_log":
        valid = (
            _boolean(data["request_observed"])
            and isinstance(data["http_class"], str)
            and data["http_class"] in {"none", "401", "403"}
            and _hex(data["request_correlation_binding_sha256"])
            and (
                (data["request_observed"] is False and data["http_class"] == "none")
                or (data["request_observed"] is True and data["http_class"] in {"401", "403"})
            )
        )
    elif operation == "sharepoint_access_decision":
        valid = _boolean(data["evidence_matches"])
    if not valid:
        raise ReadDriverBlocked("BLOCKED_RESPONSE_REDACTION")
    return dict(data)


def create_production_microsoft_port(
    *, credential_provider: Callable[[], object], transport_provider: Callable[[], object]
) -> object:
    """No provider/credential construction while no-refresh is unproven."""
    del credential_provider, transport_provider
    raise ReadDriverBlocked("BLOCKED_NO_REFRESH_CAPABILITY")


__all__ = [
    "ReadDriverBlocked",
    "create_production_microsoft_port",
    "validate_redacted_projection",
    "verify_bundle_files",
]


def main() -> int:
    """The offline bundle has no usable Microsoft authentication capability."""
    print("STATUS: BLOCKED_NO_REFRESH_CAPABILITY")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
