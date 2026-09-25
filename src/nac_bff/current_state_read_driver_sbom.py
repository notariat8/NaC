"""Reconcile Syft 1.52.0 package locations in a Windows directory bundle.

This module maps discovered packages only.  A caller must attest every bundle
file separately; an uncovered file is never assigned a synthetic package.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


class SbomMappingError(ValueError):
    """The generated SBOMs cannot be reconciled with the bundle manifest."""


@dataclass(frozen=True)
class SbomMapping:
    packages: tuple[dict[str, Any], ...]
    file_packages: dict[str, tuple[str, ...]]
    uncovered_files: tuple[str, ...]


def require_inventory_file_attribution(
    files: list[dict], components_by_id: dict[str, dict], mapping: SbomMapping,
) -> None:
    """Require exact discovered links and an explicit manual owner for gaps."""
    observed: set[str] = set()
    for item in files:
        path = item["path"]
        if path in observed or path not in mapping.file_packages:
            raise SbomMappingError("missing or duplicate attributed file")
        observed.add(path)
        components = [components_by_id[identifier] for identifier in item["component_ids"]]
        discovered = {component["spdx_id"] for component in components
                      if component["spdx_id"] is not None}
        if discovered != set(mapping.file_packages[path]):
            raise SbomMappingError("package-to-file attribution mismatch")
        if not discovered and not any(component["spdx_id"] is None
                                      for component in components):
            raise SbomMappingError("uncovered file has no explicit manual owner")
    if observed != set(mapping.file_packages):
        raise SbomMappingError("incomplete file attribution")


_LOCATION_PROPERTY = re.compile(r"syft:location:(\d+):path\Z")
_SYFT_REF = re.compile(r"[0-9a-f]{16}\Z")
_BAD_WINDOWS_CHARS = set('<>:"|?*')


def _location(value: object, *, syft_root_marker: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > 240:
        raise SbomMappingError("invalid SBOM file location")
    # Syft on Windows emits one leading backslash relative to the scan root.
    # Two leading slashes are UNC and a slash is an absolute POSIX path.
    if value.startswith(("\\\\", "//")):
        raise SbomMappingError("absolute SBOM file location")
    if syft_root_marker and value.startswith("\\"):
        value = value[1:]
    elif value.startswith("./") or value.startswith(".\\"):
        value = value[2:]
    if value.startswith(("\\", "/")):
        raise SbomMappingError("absolute SBOM file location")
    value = value.replace("\\", "/")
    parts = value.split("/")
    if (
        any(part in ("", ".", "..") for part in parts)
        or any(char in _BAD_WINDOWS_CHARS or ord(char) < 32 for char in value)
        or any(part.endswith((".", " ")) for part in parts)
    ):
        raise SbomMappingError("unsafe SBOM file location")
    return value


def _bundle_paths(value: object) -> set[str]:
    if not isinstance(value, (set, frozenset, list, tuple)) or not value:
        raise SbomMappingError("empty or invalid bundle manifest")
    result: set[str] = set()
    folded: set[str] = set()
    for path in value:
        normalized = _location(path)
        if path != normalized or normalized in result or normalized.casefold() in folded:
            raise SbomMappingError("ambiguous bundle file path")
        result.add(normalized)
        folded.add(normalized.casefold())
    return result


def _component_locations(component: dict, bundle_paths: set[str]) -> set[str]:
    properties = component.get("properties")
    if not isinstance(properties, list):
        raise SbomMappingError("component has no Syft locations")
    indexes: set[int] = set()
    locations: set[str] = set()
    for prop in properties:
        if not isinstance(prop, dict):
            raise SbomMappingError("invalid CycloneDX property")
        name = prop.get("name")
        if not isinstance(name, str):
            raise SbomMappingError("invalid CycloneDX property name")
        match = _LOCATION_PROPERTY.fullmatch(name)
        if match is None:
            continue
        index = int(match.group(1))
        if index in indexes:
            raise SbomMappingError("duplicate Syft location index")
        indexes.add(index)
        location = _location(prop.get("value"), syft_root_marker=True)
        if location not in bundle_paths or location in locations:
            raise SbomMappingError("component location outside or ambiguous in bundle")
        locations.add(location)
    if not locations or indexes != set(range(len(indexes))):
        raise SbomMappingError("component has incomplete Syft locations")
    # Older producer evidence, when present, must not contradict the properties.
    evidence = component.get("evidence")
    if isinstance(evidence, dict) and "occurrences" in evidence:
        occurrences = evidence["occurrences"]
        if not isinstance(occurrences, list):
            raise SbomMappingError("invalid CycloneDX occurrences")
        observed = {
            _location(item.get("location"), syft_root_marker=True)
            for item in occurrences if isinstance(item, dict)
        }
        if len(observed) != len(occurrences) or observed != locations:
            raise SbomMappingError("conflicting CycloneDX locations")
    return locations


def parse_syft_sboms(
    cyclonedx: object, spdx: object, bundle_paths: object,
) -> SbomMapping:
    """Return exact discovered package/file links and explicit uncovered files.

    CycloneDX ``bom-ref`` is the Syft artifact ID, which must be the final
    suffix of one SPDX package ID.  SPDX's document-root package is excluded.
    The two formats must agree on each discovered package's exact file set.
    """
    paths = _bundle_paths(bundle_paths)
    if not isinstance(cyclonedx, dict) or cyclonedx.get("bomFormat") != "CycloneDX":
        raise SbomMappingError("invalid CycloneDX document")
    if not isinstance(spdx, dict) or spdx.get("spdxVersion") != "SPDX-2.3":
        raise SbomMappingError("invalid SPDX document")
    components = cyclonedx.get("components")
    packages = spdx.get("packages")
    files = spdx.get("files")
    relationships = spdx.get("relationships")
    if (not isinstance(components, list) or not components
        or not isinstance(packages, list) or not packages
        or not isinstance(files, list) or not isinstance(relationships, list)):
        raise SbomMappingError("incomplete Syft SBOM")

    cdx_by_ref: dict[str, tuple[str, str, set[str]]] = {}
    for component in components:
        if not isinstance(component, dict):
            raise SbomMappingError("invalid CycloneDX component")
        ref, name, version = (
            component.get("bom-ref"), component.get("name"), component.get("version", ""))
        if (not isinstance(ref, str) or _SYFT_REF.fullmatch(ref) is None
            or ref in cdx_by_ref or not isinstance(name, str) or not name
            or not isinstance(version, str)):
            raise SbomMappingError("invalid or duplicate CycloneDX package identity")
        cdx_by_ref[ref] = (name, version, _component_locations(component, paths))

    spdx_by_id: dict[str, tuple[str, str]] = {}
    roots: set[str] = set()
    for package in packages:
        if not isinstance(package, dict):
            raise SbomMappingError("invalid SPDX package")
        identifier, name, version = (
            package.get("SPDXID"), package.get("name"), package.get("versionInfo", ""))
        if (not isinstance(identifier, str) or not identifier
            or identifier in spdx_by_id or not isinstance(name, str) or not name
            or not isinstance(version, str)):
            raise SbomMappingError("invalid or duplicate SPDX package identity")
        spdx_by_id[identifier] = (name, version)
        if identifier.startswith("SPDXRef-DocumentRoot-Directory-"):
            roots.add(identifier)
        elif not identifier.startswith("SPDXRef-Package-"):
            raise SbomMappingError("unexpected SPDX package")
    if len(roots) != 1:
        raise SbomMappingError("missing or ambiguous SPDX document root")

    ref_to_id: dict[str, str] = {}
    for ref, (name, version, _) in cdx_by_ref.items():
        matches = [identifier for identifier in spdx_by_id
                   if identifier not in roots and identifier.endswith("-" + ref)]
        if len(matches) != 1 or spdx_by_id[matches[0]] != (name, version):
            raise SbomMappingError("unmatched or conflicting package identity")
        ref_to_id[ref] = matches[0]
    if set(ref_to_id.values()) != set(spdx_by_id) - roots:
        raise SbomMappingError("unpaired SPDX package")

    file_by_id: dict[str, str] = {}
    file_paths: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise SbomMappingError("invalid SPDX file")
        identifier = item.get("SPDXID")
        location = _location(item.get("fileName"), syft_root_marker=True)
        if (not isinstance(identifier, str) or not identifier.startswith("SPDXRef-File-")
            or identifier in file_by_id or location not in paths or location in file_paths):
            raise SbomMappingError("invalid, duplicate or out-of-bundle SPDX file")
        file_by_id[identifier] = location
        file_paths.add(location)

    locations_by_package = {identifier: set() for identifier in ref_to_id.values()}
    root_members: set[str] = set()
    relation_pairs: set[tuple[str, str]] = set()
    for relation in relationships:
        if not isinstance(relation, dict):
            raise SbomMappingError("invalid SPDX relationship")
        left, right, kind = (relation.get("spdxElementId"),
                             relation.get("relatedSpdxElement"),
                             relation.get("relationshipType"))
        if not all(isinstance(item, str) and item for item in (left, right, kind)):
            raise SbomMappingError("invalid SPDX relationship")
        if kind == "CONTAINS" and left in roots:
            if right not in locations_by_package or right in root_members:
                raise SbomMappingError("invalid or duplicate document-root containment")
            root_members.add(right)
            continue
        if kind in ("OTHER", "CONTAINS") and left in locations_by_package:
            package_id, file_id = left, right
        elif kind == "CONTAINED_BY" and right in locations_by_package:
            package_id, file_id = right, left
        elif kind in ("OTHER", "CONTAINS", "CONTAINED_BY") and (
            left in spdx_by_id or right in spdx_by_id
            or left in file_by_id or right in file_by_id
        ):
            raise SbomMappingError("unresolved SPDX package-file relationship")
        else:
            continue
        if package_id in roots or file_id not in file_by_id:
            raise SbomMappingError("invalid SPDX package-file relationship")
        pair = (package_id, file_id)
        if pair in relation_pairs:
            raise SbomMappingError("duplicate SPDX package-file relationship")
        relation_pairs.add(pair)
        locations_by_package[package_id].add(file_by_id[file_id])
    if root_members != set(locations_by_package):
        raise SbomMappingError("missing document-root package containment")

    records: list[dict[str, Any]] = []
    file_packages: dict[str, list[str]] = {path: [] for path in paths}
    for ref in sorted(cdx_by_ref):
        name, version, cdx_locations = cdx_by_ref[ref]
        identifier = ref_to_id[ref]
        if not locations_by_package[identifier] or locations_by_package[identifier] != cdx_locations:
            raise SbomMappingError("conflicting or missing package file locations")
        records.append({
            "cyclonedx_ref": ref, "spdx_id": identifier, "name": name,
            "version": version, "paths": tuple(sorted(cdx_locations)),
        })
        for path in cdx_locations:
            file_packages[path].append(identifier)
    mapped = {path: tuple(sorted(file_packages[path])) for path in sorted(paths)}
    return SbomMapping(
        packages=tuple(records), file_packages=mapped,
        uncovered_files=tuple(path for path, ids in mapped.items() if not ids),
    )
