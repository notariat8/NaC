from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKBENCH_ROOT = REPO_ROOT / "spfx" / "nac-bpmn-viewer" / "src" / "workbench"
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "generic-workbench.contract.json"
VERIFICATION = REPO_ROOT / "workflows" / "verification-contracts" / "generic-workbench.verification.json"
CONFORMANCE = REPO_ROOT / "workflows" / "fixtures" / "generic-workbench-conformance.json"
VISUAL_ROOT = REPO_ROOT / "assets" / "docs" / "generic-workbench"
VISUAL_MANIFEST = VISUAL_ROOT / "VIS-721-manifest.json"
EXPECTED_VISUAL_SOURCES = {
    ".github/workflows/quality-gate.yml",
    "scripts/quality_gate.py",
    "scripts/validate_generic_workbench_foundation.py",
    "spfx/nac-bpmn-viewer/package.json",
    "spfx/nac-bpmn-viewer/package-lock.json",
    "spfx/nac-bpmn-viewer/src/workbench/core/WorkbenchContracts.ts",
    "spfx/nac-bpmn-viewer/src/workbench/core/WorkbenchSelectors.ts",
    "spfx/nac-bpmn-viewer/src/workbench/core/parseWorkbenchSnapshot.ts",
    "spfx/nac-bpmn-viewer/src/workbench/nac/NacWorkbenchProjection.ts",
    "spfx/nac-bpmn-viewer/src/workbench/react/WorkbenchPanel.tsx",
    "spfx/nac-bpmn-viewer/src/workbench/react/WorkbenchPanel.styles.ts",
    "spfx/nac-bpmn-viewer/scripts/workbench-synthetic-snapshot.cjs",
    "spfx/nac-bpmn-viewer/scripts/generate-workbench-visual-fixture.cjs",
    "spfx/nac-bpmn-viewer/scripts/capture-workbench-visual-evidence.cjs",
    "workflows/contracts/generic-workbench.contract.json",
    "workflows/verification-contracts/generic-workbench.verification.json",
    "workflows/fixtures/generic-workbench-conformance.json",
}
EXPECTED_BUILD_ARTIFACTS = {
    "spfx/nac-bpmn-viewer/lib-commonjs/workbench/core/WorkbenchContracts.js",
    "spfx/nac-bpmn-viewer/lib-commonjs/workbench/core/WorkbenchSelectors.js",
    "spfx/nac-bpmn-viewer/lib-commonjs/workbench/core/parseWorkbenchSnapshot.js",
    "spfx/nac-bpmn-viewer/lib-commonjs/workbench/nac/NacWorkbenchProjection.js",
    "spfx/nac-bpmn-viewer/lib-commonjs/workbench/react/WorkbenchPanel.js",
    "spfx/nac-bpmn-viewer/lib-commonjs/workbench/react/WorkbenchPanel.styles.js",
}
REQUIRED_FILES = {
    "core/WorkbenchContracts.ts",
    "core/parseWorkbenchSnapshot.ts",
    "core/WorkbenchSelectors.ts",
    "nac/NacWorkbenchProjection.ts",
    "react/WorkbenchPanel.tsx",
    "react/WorkbenchPanel.styles.ts",
}
FORBIDDEN_RUNTIME_MARKERS = (
    "graph.microsoft.com",
    "@microsoft/microsoft-graph-client",
    "SPHttpClient",
    "AadHttpClient",
    "fetch(",
    "XMLHttpRequest",
    "WebSocket",
    "localStorage",
    "sessionStorage",
    "callbackUrl",
    "saveXML",
)


def validate() -> list[str]:
    errors: list[str] = []
    for relative_path in sorted(REQUIRED_FILES):
        if not (WORKBENCH_ROOT / relative_path).is_file():
            errors.append(f"required workbench source missing: {relative_path}")

    sources = {
        path.relative_to(WORKBENCH_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in WORKBENCH_ROOT.rglob("*.ts*")
        if ".test." not in path.name
    }
    for relative_path, source in sources.items():
        for marker in FORBIDDEN_RUNTIME_MARKERS:
            if marker in source:
                errors.append(f"{relative_path}: forbidden browser runtime marker {marker}")
        imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", source)
        if relative_path.startswith("core/"):
            for imported in imports:
                if not imported.startswith("./"):
                    errors.append(f"{relative_path}: core import escapes core boundary: {imported}")
        elif relative_path.startswith("nac/"):
            for imported in imports:
                if not imported.startswith("../core/"):
                    errors.append(f"{relative_path}: NaC adapter import is not core-only: {imported}")
        elif relative_path.startswith("react/"):
            for imported in imports:
                if imported != "react" and imported != "react-dom/server" and not imported.startswith("../core/") and not imported.startswith("./"):
                    errors.append(f"{relative_path}: React import escapes UI/core boundary: {imported}")

    contract = _json(CONTRACT, errors)
    verification = _json(VERIFICATION, errors)
    conformance = _json(CONFORMANCE, errors)
    visual_manifest = _json(VISUAL_MANIFEST, errors)
    if contract:
        boundaries = contract.get("boundaries", {})
        if boundaries.get("mutating_capabilities") != "deny_only":
            errors.append("generic workbench contract must keep mutating capabilities deny-only")
        if boundaries.get("today_scope") != "currently_active_already_authorized_matter":
            errors.append("generic workbench Today scope must be the active authorized matter")
        if boundaries.get("maximum_projection_lease_seconds") != 300:
            errors.append("generic workbench projection lease must be 300 seconds")
        if boundaries.get("maximum_snapshot_bytes") != 128 * 1024:
            errors.append("generic workbench snapshot wire limit must be 128 KiB")
        if boundaries.get("maximum_text_utf16_code_units") != 256:
            errors.append("generic workbench text limit must be 256 UTF-16 code units")
        if boundaries.get("wire_serialization") != "compact_json_insertion_order_utf8":
            errors.append("generic workbench wire serialization must be exact compact JSON")
        if boundaries.get("browser_graph_access") is not False or boundaries.get("browser_mcp_access") is not False:
            errors.append("generic workbench browser Graph/MCP access must be false")
        required_binding = {"subject_id", "role", "workspace_id", "matter_id", "purpose"}
        if set(contract.get("access", {}).get("lease_binding_requires", [])) != required_binding:
            errors.append("generic workbench access lease binding is incomplete")
        redaction = contract.get("redaction", {})
        if redaction.get("required_status") != "verified" or redaction.get("content_binding") != "canonical_projection_sha256":
            errors.append("generic workbench redaction attestation is incomplete")
        if redaction.get("source_reference_format") != "opaque_identifier_only":
            errors.append("generic workbench evidence source references must be opaque identifiers")
    if verification:
        if verification.get("contract_id") != "verification.generic_workbench":
            errors.append("generic workbench verification contract ID is invalid")
        if verification.get("domain_contract_id") != "nac.generic_workbench":
            errors.append("generic workbench verification contract domain link is invalid")
        if verification.get("thresholds", {}).get("maximum_live_writes") != 0:
            errors.append("generic workbench verification contract must allow zero live writes")
    if conformance:
        limits = conformance.get("limits", {})
        if limits.get("maximum_snapshot_bytes") != 128 * 1024:
            errors.append("generic workbench conformance wire limit must be 128 KiB")
        if limits.get("maximum_text_utf16_code_units") != 256:
            errors.append("generic workbench conformance text limit must be 256 UTF-16 code units")
    if visual_manifest:
        _validate_visual_manifest(visual_manifest, errors)

    backend = (REPO_ROOT / "src" / "nac_bff" / "workbench_projection.py").read_text(encoding="utf-8")
    for prohibited in ("attention.append", "decisions.append"):
        if prohibited in backend:
            errors.append(f"BFF projection must not derive domain state: {prohibited}")
    if 'item["decision"] != "deny"' not in backend:
        errors.append("BFF projection must enforce deny-only capabilities")
    if 'serialize_workbench_projection(payload).encode("utf-8")' not in backend:
        errors.append("BFF projection wire limit must use the exact compact serializer")
    return errors


def _validate_visual_manifest(manifest: dict, errors: list[str]) -> None:
    if manifest.get("schemaVersion") != "nac.generic-workbench-visual-evidence/v1":
        errors.append("generic workbench visual evidence schema is invalid")
    if manifest.get("syntheticOnly") is not True or manifest.get("browserNetworkRequests") != 0:
        errors.append("generic workbench visual evidence must be synthetic and offline")
    expected_cases = {
        "VIS-721-01": ("VIS-721-01-desktop.png", 1440, 900),
        "VIS-721-02": ("VIS-721-02-mobile.png", 390, 844),
    }
    cases = manifest.get("cases")
    if not isinstance(cases, list) or {item.get("id") for item in cases if isinstance(item, dict)} != set(expected_cases):
        errors.append("generic workbench visual evidence cases are incomplete")
        return
    for item in cases:
        case_id = item.get("id")
        file_name, width, height = expected_cases[case_id]
        if (item.get("file"), item.get("width"), item.get("height")) != (file_name, width, height):
            errors.append(f"{case_id}: visual evidence viewport or filename drift")
        _verify_digest(VISUAL_ROOT / file_name, item.get("sha256"), errors)
    sources = manifest.get("sources")
    if (
        not isinstance(sources, list)
        or len(sources) != len(EXPECTED_VISUAL_SOURCES)
        or _manifest_paths(sources) != EXPECTED_VISUAL_SOURCES
    ):
        errors.append("generic workbench visual source manifest is incomplete")
    else:
        _verify_manifest_entries(sources, errors, require_present=True)
    artifacts = manifest.get("buildArtifacts")
    if (
        not isinstance(artifacts, list)
        or len(artifacts) != len(EXPECTED_BUILD_ARTIFACTS)
        or _manifest_paths(artifacts) != EXPECTED_BUILD_ARTIFACTS
    ):
        errors.append("generic workbench visual build artifact manifest is incomplete")
    else:
        artifact_paths = [REPO_ROOT / item["relativePath"] for item in artifacts]
        present = [path.is_file() and not path.is_symlink() for path in artifact_paths]
        require_build_evidence = os.environ.get("NAC_REQUIRE_WORKBENCH_BUILD_EVIDENCE") == "1"
        if any(present) and not all(present):
            errors.append("generic workbench compiled evidence is only partially present")
        _verify_manifest_entries(
            artifacts,
            errors,
            require_present=require_build_evidence or any(present),
        )
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        errors.append("generic workbench visual runtime provenance is missing")
    else:
        if not re.fullmatch(r"v22\.[0-9]+\.[0-9]+", str(runtime.get("nodeVersion", ""))):
            errors.append("generic workbench visual Node runtime is not pinned to Node 22")
        if not str(runtime.get("npmUserAgent", "")).startswith("npm/"):
            errors.append("generic workbench visual npm runtime provenance is missing")
        expected_tools = {"playwrightVersion": "1.55.0", "typescriptVersion": "5.8.3", "heftVersion": "1.2.17"}
        for field, expected in expected_tools.items():
            if runtime.get(field) != expected:
                errors.append(f"generic workbench visual runtime drift: {field}")


def _manifest_paths(items: list[object]) -> set[str]:
    return {
        item["relativePath"]
        for item in items
        if isinstance(item, dict) and isinstance(item.get("relativePath"), str)
    }


def _verify_manifest_entries(
    items: list[object], errors: list[str], *, require_present: bool
) -> None:
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("relativePath"), str):
            errors.append("generic workbench visual manifest entry is invalid")
            continue
        digest = item.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            errors.append("generic workbench visual manifest digest is invalid")
            continue
        path = REPO_ROOT / item["relativePath"]
        if path.is_file():
            _verify_digest(path, digest, errors)
        elif require_present:
            errors.append(f"visual evidence file missing: {path.relative_to(REPO_ROOT)}")


def _verify_digest(path: Path, expected: object, errors: list[str]) -> None:
    if path.is_symlink() or not path.is_file():
        errors.append(f"visual evidence file missing: {path.relative_to(REPO_ROOT)}")
        return
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected != actual:
        errors.append(f"visual evidence digest drift: {path.relative_to(REPO_ROOT)}")


def _json(path: Path, errors: list[str]) -> dict:
    if not path.is_file():
        errors.append(f"required JSON file missing: {path.relative_to(REPO_ROOT)}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path.relative_to(REPO_ROOT)}: {exc}")
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: generic workbench boundaries, short lease and deny-only capabilities are enforced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
