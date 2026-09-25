"""Offline source-contract gate for the Issue #748 read-driver release.

This gate never authenticates or reads a Microsoft provider. A later release
candidate must additionally pass artifact and native Windows bundle checks.
"""

from __future__ import annotations

import hashlib
import argparse
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile
from urllib.parse import urlsplit

from nac_bff.current_state_read_driver import ReadDriverBlocked, verify_bundle_files
from nac_bff.current_state_read_driver_sbom import (
    SbomMappingError, parse_syft_sboms, require_inventory_file_attribution,
)


ROOT = Path(__file__).resolve().parents[2]
RESOURCE_PATH = ROOT / "workflows/contracts/m365-current-state-read-driver-resources.contract.json"
RELEASE_PATH = ROOT / "workflows/verification-contracts/m365-current-state-read-driver.verification.json"
HISTORICAL_PATH = ROOT / "workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml"

_EXPECTED_RESOURCES = {
    "teams_tab_metadata": (
        "https://graph.microsoft.com", "v1.0",
        "/v1.0/teams/{team_id}/channels/{channel_id}/tabs/{tab_id}",
        ("team_id", "channel_id", "tab_id"), {},
        ("contract_matches", "version_binding"),
    ),
    "sharepoint_app_catalog": (
        "https://{catalog_host}", "sharepoint-rest-v1",
        "/_api/web/tenantappcatalog/AvailableApps/GetById('{product_id}')",
        ("catalog_host", "product_id"), {},
        ("package_version", "package_digest", "api_permission_match"),
    ),
    "entra_api_permission": (
        "https://graph.microsoft.com", "v1.0",
        "/v1.0/servicePrincipals/{service_principal_id}/oauth2PermissionGrants",
        ("service_principal_id",), {},
        ("tenant_match", "audience_match", "scope_match", "preauthorization_match"),
    ),
    "azure_function_metadata": (
        "https://management.azure.com", "2024-04-01",
        "/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Web/sites/{function_name}",
        ("subscription_id", "resource_group", "function_name"),
        {"api-version": "2024-04-01"},
        ("deployment_class", "configuration_digest"),
    ),
    "azure_function_request_log": (
        "https://api.applicationinsights.io", "v1",
        "/v1/apps/{app_id}/query", ("app_id",),
        {"query_template_id": "issue748-requests-correlation-window-v1"},
        ("request_observed", "http_class", "request_correlation_binding_sha256"),
    ),
    "sharepoint_access_decision": (
        "https://graph.microsoft.com", "v1.0",
        "/v1.0/sites/{site_id}/lists/{list_id}/items/{item_id}",
        ("site_id", "list_id", "item_id"), {}, ("evidence_matches",),
    ),
}
_RESOURCE_FIELDS = {
    "method", "origin_template", "api_version", "fixed_path_template",
    "allowed_placeholders", "allowed_query", "allowed_response_fields",
    "projection_proven", "maximum_reads_per_acquisition", "follow_redirects",
    "automatic_retries", "pagination", "request_body",
}
_REMOTE_CHECKS = {
    "Privacy and Secrets Guard / secret-scan",
    "Privacy and Secrets Guard / privacy-lint",
    "NaC Quality Gate / quality-gate",
    "NaC Windows Portability / windows-offline-cli",
}
_RESOURCE_TOP_FIELDS = {
    "schema_version", "contract_id", "leading_issue", "target_scope", "status",
    "maximum_microsoft_reads_per_full_acquisition", "acquisition_count",
    "placeholder_source", "free_url_or_query_input", "operations",
    "incomplete_projection_status", "unknown_operation_status",
}
_RELEASE_TOP_FIELDS = {
    "schema_version", "contract_id", "leading_issue", "delivery_mode", "risk_gate",
    "historical_contract", "historical_contract_sha256", "resource_contract",
    "specifications", "plans", "acceptance_ids", "states", "release_artifacts",
    "side_effects_allowed_offline", "forbidden_effect_counters", "required_remote_checks",
}
_RELEASE_ARTIFACTS = {
    "closed_bundle_file_manifest", "source_commit_and_tree",
    "source_archive_and_corresponding_source", "build_tool_and_pinned_dependencies",
    "binary_and_runtime_file_hashes", "cyclonedx_json", "spdx_json",
    "complete_bundle_file_attestation_separate_from_syft_package_discovery",
    "agpl_license_notice", "third_party_license_inventory",
    "reviewed_git_bound_license_catalog_and_source_hashes",
    "protected_preparation_record_before_release_record", "resource_manifest_digest",
}
_OFFLINE_EFFECTS = {
    "repository_change": True,
    "synthetic_test_files": True,
    "repository_external_release_candidate": False,
    "microsoft_provider_read": False,
    "real_run_gate_consume": False,
}
_CANDIDATE_ARTIFACTS = frozenset({
    "source.tar", "cyclonedx.json", "spdx.json", "LICENSE", "NOTICE",
    "license-inventory.json", "license-catalog.json", "preparation.json",
})
_CANDIDATE_FIELDS = frozenset({
    "schema_version", "status", "source_commit", "source_tree",
    "resource_contract_sha256", "entrypoint", "bundle_files", "artifacts",
    "build_tool", "byte_reproducibility_claim", "build_command",
    "build_inputs_sha256", "sbom_commands",
})
_LICENSE_COMPONENT_FIELDS = frozenset({
    "id", "name", "version", "license", "license_text_path",
    "license_text_sha256", "cyclonedx_ref", "spdx_id",
})
_LICENSE_FILE_FIELDS = frozenset({"path", "component_ids"})
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_COMPONENT = re.compile(r"[A-Za-z0-9._-]{1,120}\Z")
_CATALOG_SCHEMA = "nac.m365-current-state-read-driver-license-catalog/v0.1"


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _candidate_regular(path: Path) -> bool:
    info = path.stat(follow_symlinks=False)
    return stat.S_ISREG(info.st_mode) and not (
        info.st_file_attributes & 0x400 if hasattr(info, "st_file_attributes") else False
    ) and not path.is_symlink()


def _candidate_directory(path: Path) -> bool:
    info = path.stat(follow_symlinks=False)
    return stat.S_ISDIR(info.st_mode) and not (
        info.st_file_attributes & 0x400 if hasattr(info, "st_file_attributes") else False
    ) and not path.is_symlink()


def _license_path(value: object) -> bool:
    return (
        isinstance(value, str) and value != "" and len(value) <= 240
        and "\\" not in value and ":" not in value and not value.startswith("/")
        and all(part not in {"", ".", ".."} for part in value.split("/"))
        and (value == "LICENSE" or (
            len(value.split("/")) == 2 and value.startswith("licenses/")
            and all(char.isalnum() or char in "-_." for char in value.split("/")[1])
        ))
    )


def _candidate_bytes(root: Path, relative: str, backend: object) -> bytes:
    path = root.joinpath(*relative.split("/"))
    if not _candidate_regular(path):
        raise ValueError("candidate file is not regular")
    snapshot = backend.inspect_private_path(
        path, purpose="issue748-read-driver-bundle-current-user-only"
    )
    if snapshot.reparse_point is not False:
        raise ValueError("candidate file is a reparse point")
    content = path.read_bytes()
    if snapshot.sha256 != _digest(content):
        raise ValueError("candidate file changed")
    return content


def _tool_tree_digest(root: Path) -> str:
    if not root.is_absolute() or not _candidate_directory(root):
        raise ValueError("tool directory unavailable")
    pending = [(root, "")]
    files: list[dict[str, object]] = []
    while pending:
        directory, prefix = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                relative = prefix + entry.name
                path = Path(entry.path)
                if _candidate_directory(path):
                    pending.append((path, relative + "/"))
                elif _candidate_regular(path):
                    files.append({"path": relative, "size": path.stat().st_size,
                                  "sha256": _digest(path.read_bytes())})
                else:
                    raise ValueError("tool directory changed")
                if len(files) > 20000:
                    raise ValueError("tool directory too large")
    if not files:
        raise ValueError("tool directory empty")
    return _digest(json.dumps(sorted(files, key=lambda item: item["path"]),
                              sort_keys=True, separators=(",", ":")).encode())


def _validate_build_tool(tool: object, backend: object) -> bool:
    if (not isinstance(tool, dict) or set(tool) != {
        "name", "version", "python_version", "python", "pyinstaller", "syft",
    } or (tool["name"], tool["version"], tool["python_version"])
            != ("PyInstaller", "6.22.3", "3.13.4")):
        return False
    python, pyinstaller, syft = tool["python"], tool["pyinstaller"], tool["syft"]
    if (not isinstance(python, dict) or set(python) != {"path", "sha256"}
        or not isinstance(pyinstaller, dict)
        or set(pyinstaller) != {"module_path", "module_sha256", "package_tree_sha256"}
        or not isinstance(syft, dict) or set(syft) != {"version", "path", "sha256"}
        or syft["version"] != "1.52.0"):
        return False
    bindings = (
        (python["path"], python["sha256"]),
        (pyinstaller["module_path"], pyinstaller["module_sha256"]),
        (syft["path"], syft["sha256"]),
    )
    for name, digest in bindings:
        if (not isinstance(name, str) or not isinstance(digest, str)
            or _HEX64.fullmatch(digest) is None):
            return False
        path = Path(name)
        if not path.is_absolute() or not _candidate_regular(path):
            return False
        backend.inspect_private_path(path, purpose="toolchain-executable")
        if _digest(path.read_bytes()) != digest:
            return False
    tree_digest = pyinstaller["package_tree_sha256"]
    return (isinstance(tree_digest, str) and _HEX64.fullmatch(tree_digest) is not None
            and _tool_tree_digest(Path(pyinstaller["module_path"]).parent) == tree_digest)


def _reviewed_catalog_matches(
    catalog: object, inventory: dict, bundle_paths: set[str], source_tree: str,
    reviewed_preparation: dict[str, object],
) -> bool:
    """Reject self-attested inventory claims absent from the bound source tree."""
    if (not isinstance(catalog, dict)
        or set(catalog) != {"schema_version", "status", "reviewed_preparation", "components", "files"}
        or catalog["schema_version"] != _CATALOG_SCHEMA
        or catalog["status"] != "APPROVED"
        or not isinstance(catalog["components"], list)
        or not catalog["components"]
        or not isinstance(catalog["files"], list)
        or not catalog["files"]
        or _HEX40.fullmatch(source_tree) is None
        or not isinstance(catalog["reviewed_preparation"], dict)
        or catalog["reviewed_preparation"] != reviewed_preparation):
        return False
    components = {}
    for item in catalog["components"]:
        if (not isinstance(item, dict) or set(item) != {
            "id", "name", "version", "license", "license_text_path",
            "license_text_sha256", "source_uri", "source_sha256",
        } or not isinstance(item["id"], str)
            or _SAFE_COMPONENT.fullmatch(item["id"]) is None
            or item["id"] in components
            or not _license_path(item["license_text_path"])
            or not isinstance(item["license_text_sha256"], str)
            or _HEX64.fullmatch(item["license_text_sha256"]) is None
            or item["license_text_sha256"] == "0" * 64
            or any(not isinstance(item[key], str) or not item[key]
                   or len(item[key]) > 160 or any(ord(char) < 32 for char in item[key])
                   for key in ("name", "version", "license"))):
            return False
        if item["id"] == "nac":
            if (item["source_uri"] != "git:HEAD"
                or item["source_sha256"] != "BOUND_SOURCE_TREE"
                or item["license"] != "AGPL-3.0-or-later"
                or item["license_text_path"] != "LICENSE"):
                return False
        else:
            uri, digest = item["source_uri"], item["source_sha256"]
            if not isinstance(uri, str) or len(uri) > 240:
                return False
            parsed = urlsplit(uri)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment
                or not isinstance(digest, str) or _HEX64.fullmatch(digest) is None
                or digest == "0" * 64
                or item["license"].upper() in {
                    "NOASSERTION", "UNKNOWN", "PENDING", "TBD", "NONE", "N/A",
                }):
                return False
        components[item["id"]] = item
    if set(components) != {item["id"] for item in inventory["components"]}:
        return False
    for item in inventory["components"]:
        if any(item[key] != components[item["id"]][key] for key in (
            "name", "version", "license", "license_text_path", "license_text_sha256",
        )):
            return False
    catalog_files = {}
    for item in catalog["files"]:
        if (not isinstance(item, dict) or set(item) != {"path", "component_ids"}
            or not isinstance(item["path"], str) or item["path"] in catalog_files
            or not isinstance(item["component_ids"], list)
            or not item["component_ids"]
            or any(not isinstance(name, str) or name not in components
                   for name in item["component_ids"])
            or len(item["component_ids"]) != len(set(item["component_ids"]))):
            return False
        catalog_files[item["path"]] = set(item["component_ids"])
    if set(catalog_files) != bundle_paths:
        return False
    return catalog_files == {
        item["path"]: set(item["component_ids"]) for item in inventory["files"]
    }


def validate_candidate_release(
    candidate_root: Path, backend: object, *, source_commit: str,
    source_tree: str, source_archive: bytes,
) -> list[str]:
    """Validate actual external candidate files; never confer live-read authority."""
    blocked = ["DRIVER_RELEASE_BINDING"]
    try:
        if (
            not isinstance(candidate_root, Path) or not candidate_root.is_absolute()
            or candidate_root == ROOT or ROOT in candidate_root.parents
            or _HEX40.fullmatch(source_commit) is None
            or _HEX40.fullmatch(source_tree) is None
            or not isinstance(source_archive, bytes) or not source_archive
            or not _candidate_directory(candidate_root)
            or not _candidate_directory(candidate_root / "bundle")
        ):
            return blocked
        backend.validate_current_user_only_directory(candidate_root)
        backend.validate_current_user_only_directory(candidate_root / "bundle")
        root_names = {entry.name for entry in os.scandir(candidate_root)}
        if root_names not in (
            _CANDIDATE_ARTIFACTS | {"release.json", "bundle"},
            _CANDIDATE_ARTIFACTS | {"release.json", "bundle", "licenses"},
        ):
            return blocked
        release = json.loads(_candidate_bytes(candidate_root, "release.json", backend))
        if not isinstance(release, dict) or frozenset(release) != _CANDIDATE_FIELDS:
            return blocked
        if (
            release["schema_version"] != "nac.m365-current-state-read-driver-candidate/v0.2"
            or release["status"] != "CANDIDATE_BUILT"
            or release["source_commit"] != source_commit
            or release["source_tree"] != source_tree
            or release["entrypoint"] != "reader.exe"
            or release["byte_reproducibility_claim"] is not False
            or release["resource_contract_sha256"] != _digest(RESOURCE_PATH.read_bytes())
            or not _validate_build_tool(release["build_tool"], backend)
            or release["build_command"] != [
                release["build_tool"]["python"]["path"], "-m", "PyInstaller",
                "--onedir", "--name", "reader", "--distpath",
                str(candidate_root / "bundle-stage"), "--workpath",
                str(candidate_root / "work"), "--specpath",
                str(candidate_root / "work"), "--paths", str(ROOT / "src"),
                str(ROOT / "src/nac_bff/current_state_read_driver.py"),
            ]
            or release["sbom_commands"] != {
                "cyclonedx": [
                    release["build_tool"]["syft"]["path"],
                    f"dir:{candidate_root / 'bundle'}", "-o",
                    f"cyclonedx-json={candidate_root / 'cyclonedx.json'}",
                ],
                "spdx": [
                    release["build_tool"]["syft"]["path"],
                    f"dir:{candidate_root / 'bundle'}", "-o",
                    f"spdx-json={candidate_root / 'spdx.json'}",
                ],
            }
            or not isinstance(release["artifacts"], dict)
            or set(release["artifacts"]) != _CANDIDATE_ARTIFACTS
        ):
            return blocked
        artifacts: dict[str, bytes] = {}
        for name in _CANDIDATE_ARTIFACTS:
            claimed = release["artifacts"][name]
            if not isinstance(claimed, str) or _HEX64.fullmatch(claimed) is None:
                return blocked
            content = _candidate_bytes(candidate_root, name, backend)
            if _digest(content) != claimed or not content:
                return blocked
            artifacts[name] = content
        if artifacts["source.tar"] != source_archive:
            return blocked
        with tarfile.open(fileobj=io.BytesIO(source_archive), mode="r:") as archive:
            selected = (
                "LICENSE", "NOTICE", "src/nac_bff/current_state_read_driver.py",
                "workflows/contracts/m365-current-state-read-driver-license-catalog.json",
            )
            members = archive.getmembers()
            source_files = {}
            for name in selected:
                matching = [member for member in members if member.name == name]
                if len(matching) != 1 or not matching[0].isfile():
                    return blocked
                stream = archive.extractfile(matching[0])
                if stream is None:
                    return blocked
                source_files[name] = stream.read()
            if (
                artifacts["LICENSE"] != source_files["LICENSE"]
                or not artifacts["NOTICE"].startswith(source_files["NOTICE"])
                or not source_files["src/nac_bff/current_state_read_driver.py"]
                or artifacts["license-catalog.json"] != source_files[
                    "workflows/contracts/m365-current-state-read-driver-license-catalog.json"
                ]
            ):
                return blocked
        inputs = {
            "source_archive_sha256": release["artifacts"]["source.tar"],
            "resource_contract_sha256": release["resource_contract_sha256"],
            "build_tool": release["build_tool"],
        }
        if release["build_inputs_sha256"] != _digest(json.dumps(
            inputs, sort_keys=True, separators=(",", ":")
        ).encode()):
            return blocked
        if not isinstance(release["bundle_files"], list):
            return blocked
        entry_sha = verify_bundle_files(
            candidate_root / "bundle", release["bundle_files"], backend
        )
        if entry_sha != next(
            item["sha256"] for item in release["bundle_files"]
            if item["path"] == "reader.exe"
        ):
            return blocked
        cyclonedx = json.loads(artifacts["cyclonedx.json"])
        spdx = json.loads(artifacts["spdx.json"])
        inventory = json.loads(artifacts["license-inventory.json"])
        catalog = json.loads(artifacts["license-catalog.json"])
        preparation = json.loads(artifacts["preparation.json"])
        if (not isinstance(preparation, dict) or set(preparation) != {
            "schema_version", "status", "source_commit", "source_tree",
            "build_tool", "build_command", "sbom_commands", "artifacts", "bundle_files",
        } or preparation["schema_version"]
            != "nac.m365-current-state-read-driver-preparation/v0.1"
            or preparation["status"] != "AWAITING_INDEPENDENT_LICENSE_EVIDENCE"
            or preparation["source_commit"] != source_commit
            or preparation["source_tree"] != source_tree
            or preparation["build_tool"] != release["build_tool"]
            or preparation["build_command"] != release["build_command"]
            or preparation["sbom_commands"] != release["sbom_commands"]
            or not isinstance(preparation["artifacts"], dict)
            or set(preparation["artifacts"]) != {
                "source.tar", "cyclonedx.json", "spdx.json", "LICENSE", "NOTICE",
            }
            or any(preparation["artifacts"][name] != release["artifacts"][name]
                   for name in ("source.tar", "cyclonedx.json", "spdx.json", "LICENSE"))
            or preparation["artifacts"]["NOTICE"] != _digest(source_files["NOTICE"])
            or not isinstance(preparation["bundle_files"], list)
            or preparation["bundle_files"] != [
                {"path": item["path"], "sha256": item["sha256"]}
                for item in sorted(release["bundle_files"], key=lambda entry: entry["path"])
            ]):
            return blocked
        if (
            not isinstance(cyclonedx, dict) or cyclonedx.get("bomFormat") != "CycloneDX"
            or not isinstance(cyclonedx.get("components"), list)
            or not isinstance(spdx, dict) or spdx.get("spdxVersion") != "SPDX-2.3"
            or not isinstance(spdx.get("packages"), list)
            or not isinstance(inventory, dict)
            or set(inventory) != {"schema_version", "components", "files"}
            or inventory["schema_version"]
            != "nac.m365-current-state-read-driver-license-inventory/v0.1"
            or not isinstance(inventory["components"], list)
            or not inventory["components"]
            or not isinstance(inventory["files"], list)
            or not inventory["files"]
        ):
            return blocked
        bundle_paths = {item["path"] for item in release["bundle_files"]}
        sbom_bindings = parse_syft_sboms(cyclonedx, spdx, bundle_paths)
        cdx_refs = {item["cyclonedx_ref"] for item in sbom_bindings.packages}
        spdx_ids = {item["spdx_id"] for item in sbom_bindings.packages}
        components = inventory["components"]
        if any(not isinstance(item, dict) or set(item) != _LICENSE_COMPONENT_FIELDS
               for item in components):
            return blocked
        ids = [item["id"] for item in components]
        if any(not isinstance(item, str) or _SAFE_COMPONENT.fullmatch(item) is None
               for item in ids) or len(set(ids)) != len(ids):
            return blocked
        if (
            {item["cyclonedx_ref"] for item in components if item["cyclonedx_ref"] is not None}
            != cdx_refs
            or {item["spdx_id"] for item in components if item["spdx_id"] is not None}
            != spdx_ids
        ):
            return blocked
        if not any(
            item["id"] == "nac" and item["license"] == "AGPL-3.0-or-later"
            and item["license_text_path"] == "LICENSE" for item in components
        ):
            return blocked
        license_paths = set()
        used_cdx_refs: set[str] = set()
        used_spdx_ids: set[str] = set()
        for item in components:
            path = item["license_text_path"]
            if (
                not _license_path(path)
                or not isinstance(item["license_text_sha256"], str)
                or _HEX64.fullmatch(item["license_text_sha256"]) is None
                or ((item["cyclonedx_ref"] is None) != (item["spdx_id"] is None))
                or (item["cyclonedx_ref"] is not None and (
                    not isinstance(item["cyclonedx_ref"], str)
                    or not isinstance(item["spdx_id"], str)
                    or item["cyclonedx_ref"] not in cdx_refs
                    or item["spdx_id"] not in spdx_ids))
                or any(not isinstance(item[field], str) or not item[field]
                       for field in ("name", "version", "license"))
                or any(len(item[field]) > 160 or any(ord(char) < 32 for char in item[field])
                       for field in ("name", "version", "license"))
                or (item["cyclonedx_ref"] is not None and (
                    item["cyclonedx_ref"] in used_cdx_refs
                    or item["spdx_id"] in used_spdx_ids))
            ):
                return blocked
            if _digest(_candidate_bytes(candidate_root, path, backend)) != item["license_text_sha256"]:
                return blocked
            license_paths.add(path)
            if item["cyclonedx_ref"] is not None:
                used_cdx_refs.add(item["cyclonedx_ref"])
                used_spdx_ids.add(item["spdx_id"])
        if "licenses" in root_names:
            licenses_dir = candidate_root / "licenses"
            if not _candidate_directory(licenses_dir):
                return blocked
            backend.validate_current_user_only_directory(licenses_dir)
            actual_licenses = {"licenses/" + entry.name for entry in os.scandir(licenses_dir)}
            if actual_licenses != license_paths - {"LICENSE"}:
                return blocked
        elif license_paths != {"LICENSE"}:
            return blocked
        files = inventory["files"]
        if any(not isinstance(item, dict) or set(item) != _LICENSE_FILE_FIELDS
               for item in files):
            return blocked
        paths = [item["path"] for item in files]
        if (
            len(paths) != len(set(paths))
            or set(paths) != {item["path"] for item in release["bundle_files"]}
            or any(
                not isinstance(item["component_ids"], list)
                or not item["component_ids"]
                or any(not isinstance(component_id, str) or component_id not in ids
                       for component_id in item["component_ids"])
                or len(item["component_ids"]) != len(set(item["component_ids"]))
                for item in files
            )
            or {
                component_id for item in files for component_id in item["component_ids"]
            } != set(ids)
        ):
            return blocked
        components_by_id = {item["id"]: item for item in components}
        packages_by_id = {item["spdx_id"]: item for item in sbom_bindings.packages}
        for component in components:
            package_id = component["spdx_id"]
            if package_id is not None:
                package = packages_by_id.get(package_id)
                if (package is None or component["cyclonedx_ref"] != package["cyclonedx_ref"]
                        or component["name"] != package["name"]
                        or component["version"] != package["version"]):
                    return blocked
        require_inventory_file_attribution(files, components_by_id, sbom_bindings)
        if not _reviewed_catalog_matches(
            catalog, inventory, bundle_paths, source_tree,
            {
                "driver_source_sha256": _digest(source_files[
                    "src/nac_bff/current_state_read_driver.py"
                ]),
                "resource_contract_sha256": release["resource_contract_sha256"],
                "build_tool": release["build_tool"],
                "bundle_files": preparation["bundle_files"],
                "cyclonedx_sha256": release["artifacts"]["cyclonedx.json"],
                "spdx_sha256": release["artifacts"]["spdx.json"],
                "notice_sha256": preparation["artifacts"]["NOTICE"],
            },
        ):
            return blocked
        expected_notice = source_files["NOTICE"]
        third_party = [item for item in components if item["id"] != "nac"]
        if third_party:
            suffix = "\nThird-party runtime components in this candidate:\n"
            for item in sorted(third_party, key=lambda entry: entry["id"]):
                suffix += (
                    f"{item['name']} {item['version']} — "
                    f"{item['license']} ({item['license_text_path']})\n"
                )
            expected_notice += suffix.encode("utf-8")
        if artifacts["NOTICE"] != expected_notice:
            return blocked
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration,
            tarfile.TarError, EOFError, ReadDriverBlocked, SbomMappingError):
        return blocked
    return []


def _bound_git_bytes(*arguments: str) -> bytes:
    if os.name != "nt":
        raise OSError("Windows bound Git required")
    from nac_bff.activation_security_backend import get_platform_security_backend

    backend = get_platform_security_backend()
    if not backend.capabilities().complete:
        raise OSError("Windows security backend unavailable")
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    candidates = (
        program_files / "Git" / "cmd" / "git.exe",
        program_files / "Git" / "bin" / "git.exe",
    )
    executable = None
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            backend.inspect_private_path(candidate, purpose="toolchain-executable")
        except (OSError, RuntimeError, ValueError):
            continue
        executable = candidate
        break
    if executable is None:
        raise OSError("bound Git unavailable")
    environment = {
        key: value for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull, "GIT_ATTR_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0", "GIT_LFS_SKIP_SMUDGE": "1",
    })
    result = subprocess.run(
        [str(executable), "--no-optional-locks", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
         *arguments],
        stdin=subprocess.DEVNULL, capture_output=True, check=False,
        timeout=120, env=environment,
    )
    if result.returncode:
        raise OSError("bound Git read failed")
    return result.stdout


def validate_candidate_at_current_head(candidate_root: Path) -> list[str]:
    try:
        if os.name != "nt":
            return ["WINDOWS_SECURITY_BACKEND_REQUIRED"]
        from nac_bff.activation_security_backend import get_platform_security_backend

        backend = get_platform_security_backend()
        if not backend.capabilities().complete:
            return ["WINDOWS_SECURITY_BACKEND_REQUIRED"]
        commit = _bound_git_bytes("rev-parse", "HEAD").decode("ascii").strip()
        tree = _bound_git_bytes("rev-parse", "HEAD^{tree}").decode("ascii").strip()
        archive = _bound_git_bytes("archive", "--format=tar", "HEAD")
        return validate_candidate_release(
            candidate_root, backend, source_commit=commit,
            source_tree=tree, source_archive=archive,
        )
    except (OSError, UnicodeError, subprocess.TimeoutExpired, RuntimeError, ValueError):
        return ["DRIVER_RELEASE_BINDING"]


def validate_resources(value: object) -> list[str]:
    """Reject widening or drift in the checked-in closed GET resource set."""
    if not isinstance(value, dict):
        return ["RESOURCE_CONTRACT_DRIFT"]
    if (
        set(value) != _RESOURCE_TOP_FIELDS
        or value.get("schema_version") != "nac.m365-current-state-read-driver-resources/v0.1"
        or value.get("contract_id") != "m365-current-state-read-driver-resources"
        or value.get("leading_issue") != "https://github.com/notariat8/NaC/issues/748"
        or value.get("status") != "OFFLINE_REVIEWABLE_ONLY"
        or value.get("target_scope") != "notary_team_01 / NaC Vorgangsansicht"
        or value.get("maximum_microsoft_reads_per_full_acquisition") != 6
        or value.get("acquisition_count") != 2
        or value.get("placeholder_source") != "protected_exact_target_bindings_only"
        or value.get("free_url_or_query_input") is not False
        or value.get("incomplete_projection_status") != "BLOCKED_RESOURCE_PROJECTION_INCOMPLETE"
        or value.get("unknown_operation_status") != "BLOCKED_RESOURCE_NOT_ALLOWLISTED"
    ):
        return ["RESOURCE_CONTRACT_DRIFT"]
    operations = value.get("operations")
    if not isinstance(operations, dict) or set(operations) != set(_EXPECTED_RESOURCES):
        return ["RESOURCE_CONTRACT_DRIFT"]
    for name, expected in _EXPECTED_RESOURCES.items():
        resource = operations[name]
        if not isinstance(resource, dict) or set(resource) != _RESOURCE_FIELDS:
            return ["RESOURCE_CONTRACT_DRIFT"]
        origin, version, path, placeholders, query, response = expected
        if (
            resource["method"] != "GET"
            or resource["origin_template"] != origin
            or resource["api_version"] != version
            or resource["fixed_path_template"] != path
            or resource["allowed_placeholders"] != list(placeholders)
            or resource["allowed_query"] != query
            or resource["allowed_response_fields"] != list(response)
            or resource["projection_proven"] is not False
            or resource["maximum_reads_per_acquisition"] != 1
            or resource["follow_redirects"] is not False
            or resource["automatic_retries"] != 0
            or resource["pagination"] is not False
            or resource["request_body"] is not False
            or set(re.findall(r"\{([a-z_]+)\}", origin + path)) != set(placeholders)
        ):
            return ["RESOURCE_CONTRACT_DRIFT"]
    return []


def validate_release_contract(value: object, historical_bytes: bytes) -> list[str]:
    """Bind the new release contract forward without rewriting #748 history."""
    if not isinstance(value, dict):
        return ["RELEASE_CONTRACT_DRIFT"]
    if value.get("historical_contract_sha256") != hashlib.sha256(historical_bytes).hexdigest():
        return ["HISTORICAL_CONTRACT_DRIFT"]
    states = value.get("states")
    if not isinstance(states, dict) or set(states) != {"OFFLINE_REVIEWABLE", "LIVE_CAPABLE"}:
        return ["RELEASE_CONTRACT_DRIFT"]
    offline, live = states["OFFLINE_REVIEWABLE"], states["LIVE_CAPABLE"]
    if not isinstance(offline, dict) or not isinstance(live, dict):
        return ["RELEASE_CONTRACT_DRIFT"]
    if live.get("enabled_by_this_contract") is not False:
        return ["LIVE_CAPABILITY_NOT_AUTHORIZED"]
    if (
        set(value) != _RELEASE_TOP_FIELDS
        or value.get("schema_version") != "nac.m365-current-state-read-driver-release/v0.1"
        or value.get("contract_id") != "m365-current-state-read-driver-release"
        or value.get("leading_issue") != "https://github.com/notariat8/NaC/issues/748"
        or value.get("delivery_mode") != "Protected PR"
        or value.get("risk_gate") != "Human Approval"
        or value.get("historical_contract") != HISTORICAL_PATH.relative_to(ROOT).as_posix()
        or value.get("resource_contract") != RESOURCE_PATH.relative_to(ROOT).as_posix()
        or value.get("specifications") != {
            language: f"docs/{language}/superpowers/specs/2026-09-23-m365-current-state-read-driver-design.md"
            for language in ("de", "en")
        }
        or value.get("plans") != {
            language: f"docs/{language}/superpowers/plans/2026-09-23-m365-current-state-read-driver.md"
            for language in ("de", "en")
        }
        or not isinstance(value.get("acceptance_ids"), list)
        or any(not isinstance(item, str) for item in value["acceptance_ids"])
        or set(value["acceptance_ids"]) != {f"AC-748-RD-{number:02d}" for number in range(1, 9)}
        or len(value["acceptance_ids"]) != 8
        or not isinstance(value.get("required_remote_checks"), list)
        or any(not isinstance(item, str) for item in value["required_remote_checks"])
        or set(value["required_remote_checks"]) != _REMOTE_CHECKS
        or len(value["required_remote_checks"]) != len(_REMOTE_CHECKS)
        or not isinstance(value.get("release_artifacts"), list)
        or any(not isinstance(item, str) for item in value["release_artifacts"])
        or set(value["release_artifacts"]) != _RELEASE_ARTIFACTS
        or len(value["release_artifacts"]) != len(_RELEASE_ARTIFACTS)
        or value.get("side_effects_allowed_offline") != _OFFLINE_EFFECTS
        or set(offline) != {
            "provider_access", "login_allowed", "real_run_allowed",
            "requires_source_binary_bundle_sbom_license_binding",
            "requires_local_and_remote_checks",
        }
        or offline.get("provider_access") is not False
        or offline.get("login_allowed") is not False
        or offline.get("real_run_allowed") is not False
        or offline.get("requires_source_binary_bundle_sbom_license_binding") is not True
        or offline.get("requires_local_and_remote_checks") is not True
        or set(live) != {
            "enabled_by_this_contract", "requires_no_refresh_proof",
            "requires_complete_resource_projection",
            "requires_every_historical_issue748_gate",
            "requires_separate_driver_release_approval",
            "requires_separate_real_read_approval",
            "requires_reauthorization_before_factory_and_every_read",
        }
        or live.get("requires_no_refresh_proof") is not True
        or live.get("requires_complete_resource_projection") is not True
        or live.get("requires_every_historical_issue748_gate") is not True
        or live.get("requires_separate_driver_release_approval") is not True
        or live.get("requires_separate_real_read_approval") is not True
        or live.get("requires_reauthorization_before_factory_and_every_read") is not True
    ):
        return ["RELEASE_CONTRACT_DRIFT"]
    counters = value.get("forbidden_effect_counters")
    if not isinstance(counters, dict) or set(counters) != {
        "login", "device_code", "token_refresh", "credential_import",
        "credential_export", "credential_write", "redirect_follow", "retry",
        "tenant_write", "provider_write", "deployment", "issue_739_release",
        "issue_632_live_run",
    } or any(
        type(counters.get(name)) is not int or counters[name] != 0 for name in (
            "login", "device_code", "token_refresh", "credential_import",
            "credential_export", "credential_write", "redirect_follow", "retry",
            "tenant_write", "provider_write", "deployment", "issue_739_release",
            "issue_632_live_run",
        )
    ):
        return ["RELEASE_CONTRACT_DRIFT"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Issue #748 read-driver evidence gate")
    parser.add_argument("--candidate", type=Path)
    arguments = parser.parse_args()
    try:
        resources = json.loads(RESOURCE_PATH.read_text(encoding="utf-8"))
        release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
        historical = HISTORICAL_PATH.read_bytes()
    except (OSError, ValueError):
        print("STATUS: BLOCKED_RELEASE_CONTRACT_UNAVAILABLE")
        return 1
    errors = validate_resources(resources) + validate_release_contract(release, historical)
    if not errors and arguments.candidate is not None:
        errors += validate_candidate_at_current_head(arguments.candidate)
    if errors:
        print("STATUS: BLOCKED " + ",".join(sorted(set(errors))))
        return 1
    if arguments.candidate is None:
        print("STATUS: SOURCE_CONTRACT_PASSED")
        print("OK: Issue #748 read-driver source contracts are closed; LIVE_CAPABLE is not enabled.")
    else:
        print("STATUS: CANDIDATE_VALIDATED")
        print("OK: Offline candidate files are bound to current HEAD; LIVE_CAPABLE is not enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
