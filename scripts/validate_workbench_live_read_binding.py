from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "workflows/contracts/workbench-live-read-binding.contract.json"
VERIFICATION_PATH = ROOT / "workflows/verification-contracts/workbench-live-read-binding.verification.json"
FIXTURE_PATH = ROOT / "workflows/fixtures/workbench-live-read-canonicalization.json"
GENERIC_CONTRACT_PATH = ROOT / "workflows/contracts/generic-workbench.contract.json"
SERVER_PATH = ROOT / "src/nac_bff/workbench_endpoint.py"
FASTAPI_PATH = ROOT / "src/nac_bff/fastapi_adapter.py"
CLIENT_PATH = ROOT / "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.ts"
HOST_PATH = ROOT / "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.tsx"
WEBPART_PATH = ROOT / "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts"
CI_PATH = ROOT / ".github/workflows/quality-gate.yml"
PACKAGE_PATH = ROOT / "spfx/nac-bpmn-viewer/package.json"
VISUAL_ROOT = ROOT / "assets/docs/workbench-live-read-binding"
VISUAL_MANIFEST_PATH = VISUAL_ROOT / "VIS-725-manifest.json"

EXPECTED_SOURCE_BINDINGS = {
    "host": "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.tsx",
    "styles": "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.styles.ts",
    "client": "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.ts",
    "webPart": "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts",
    "parser": "spfx/nac-bpmn-viewer/src/workbench/core/parseWorkbenchSnapshot.ts",
    "projection": "spfx/nac-bpmn-viewer/src/workbench/nac/NacWorkbenchProjection.ts",
    "contract": "workflows/contracts/workbench-live-read-binding.contract.json",
}
EXPECTED_VISUAL_HARNESS = {
    "scripts/validate_workbench_live_read_binding.py",
    "spfx/nac-bpmn-viewer/package.json",
    "spfx/nac-bpmn-viewer/package-lock.json",
    "spfx/nac-bpmn-viewer/scripts/workbench-live-read-synthetic-snapshot.cjs",
    "spfx/nac-bpmn-viewer/scripts/generate-workbench-live-read-visual-fixture.cjs",
    "spfx/nac-bpmn-viewer/scripts/capture-workbench-live-read-visual-evidence.cjs",
    "workflows/verification-contracts/workbench-live-read-binding.verification.json",
}
EXPECTED_BUILD_ARTIFACTS = {
    "spfx/nac-bpmn-viewer/lib-commonjs/webparts/nacBpmnViewer/components/NacWorkbenchHost.js",
    "spfx/nac-bpmn-viewer/lib-commonjs/webparts/nacBpmnViewer/components/NacWorkbenchHost.styles.js",
    "spfx/nac-bpmn-viewer/lib-commonjs/workbench/core/parseWorkbenchSnapshot.js",
    "spfx/nac-bpmn-viewer/lib-commonjs/workbench/nac/NacWorkbenchProjection.js",
    "spfx/nac-bpmn-viewer/lib-commonjs/workbench/react/WorkbenchPanel.js",
    "spfx/nac-bpmn-viewer/lib-commonjs/workbench/react/WorkbenchPanel.styles.js",
}
EXPECTED_VISUAL_CASES = {
    "VIS-725-01": {
        "state": "ready",
        "layout": "desktop",
        "file": "VIS-725-01-desktop-ready.png",
        "viewport": {"width": 1440, "height": 900},
    },
    "VIS-725-02": {
        "state": "ready",
        "layout": "narrow-spfx-column",
        "file": "VIS-725-02-narrow-spfx-ready.png",
        "viewport": {"width": 720, "height": 980},
    },
    "VIS-725-03": {
        "state": "ready",
        "layout": "mobile",
        "file": "VIS-725-03-mobile-ready.png",
        "viewport": {"width": 390, "height": 844},
    },
    "VIS-725-04": {
        "state": "loading",
        "layout": "state",
        "file": "VIS-725-04-loading.png",
        "viewport": {"width": 720, "height": 420},
    },
    "VIS-725-05": {
        "state": "deny",
        "layout": "state",
        "file": "VIS-725-05-deny.png",
        "viewport": {"width": 720, "height": 420},
    },
    "VIS-725-06": {
        "state": "unavailable",
        "layout": "state",
        "file": "VIS-725-06-unavailable.png",
        "viewport": {"width": 720, "height": 420},
    },
}

TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
WORKSPACE_ID = "notary_team_01"
MATTER_ID = "NAC-SYN-MATTER-001"
PURPOSE = "view_synthetic_matter_workspace"
ROUTE = "/v1/workspaces/{workspace_id}/matters/{matter_id}/workbench-snapshot"


def validate() -> list[str]:
    errors: list[str] = []
    contract = _object(CONTRACT_PATH, errors)
    verification = _object(VERIFICATION_PATH, errors)
    fixture = _object(FIXTURE_PATH, errors)
    generic = _object(GENERIC_CONTRACT_PATH, errors)
    visual_manifest = _object(VISUAL_MANIFEST_PATH, errors)

    if contract:
        if contract.get("contract_id") != "nac.workbench_live_read_binding":
            errors.append("live binding contract ID is invalid")
        if contract.get("acceptance_ids") != [f"AC-{index}" for index in range(1, 9)]:
            errors.append("live binding acceptance IDs do not match Issue #725")
        endpoint = contract.get("endpoint", {})
        if endpoint.get("method") != "GET" or endpoint.get("path") != ROUTE:
            errors.append("live binding endpoint is not the fixed GET route")
        allowlist = contract.get("synthetic_allowlist", {})
        expected_allowlist = {
            "tenant_id": TENANT_ID,
            "workspace_id": WORKSPACE_ID,
            "matter_id": MATTER_ID,
            "purpose": PURPOSE,
            "enforcement": "before_access_and_data_ports",
        }
        if allowlist != expected_allowlist:
            errors.append("synthetic pre-port allowlist is incomplete")
        access = contract.get("access", {})
        if access.get("maximum_lease_seconds") != 300:
            errors.append("access lease must be bounded to 300 seconds")
        if access.get("synthetic_deputy_reason_exact") != (
            "Synthetische Urlaubsvertretung"
        ):
            errors.append("synthetic deputy reason allowlist is not exact")
        deny = access.get("deny_behavior", {})
        if deny.get("status") != 403 or deny.get("body") != {
            "status": 403,
            "error": {"code": "ACCESS_DENIED"},
        }:
            errors.append("access denial envelope is not exact")
        auth = access.get("authentication_failure", {})
        if auth.get("status") != 401 or auth.get("body") != {
            "status": 401,
            "error": {"code": "AUTHENTICATION_REQUIRED"},
        }:
            errors.append("authentication failure envelope is not exact")
        rejection_mapping = access.get("rejection_mapping", {})
        if rejection_mapping.get(
            "missing_invalid_wrong_scope_or_wrong_tenant_token"
        ) != "authentication_failure":
            errors.append("token tenant/scope failures must map to authentication failure")
        delivery = contract.get("delivery", {})
        if delivery != {
            "tenant_deployment_performed": False,
            "tenant_deployment_target": WORKSPACE_ID,
            "deployment_requires_reviewed_main": True,
            "deployment_requires_owner_apply": True,
        }:
            errors.append("tenant deployment boundary is not exact")
        response = contract.get("response", {})
        if response.get("cache_control") != "no-store" or response.get("maximum_wire_bytes") != 131072:
            errors.append("response no-store or wire limit is invalid")
        content_hash = response.get("content_hash", {})
        if content_hash.get("normative_fixture") != FIXTURE_PATH.relative_to(ROOT).as_posix():
            errors.append("canonicalization fixture is not contract-bound")
        visual = contract.get("visual_evidence", {})
        if visual.get("schema_version") != "nac.workbench-live-read-host-visual-evidence/v1":
            errors.append("live host visual evidence schema is not contract-bound")
        if visual.get("isolation") != "separate_from_generic_workbench_visual_evidence":
            errors.append("live host visual evidence must remain separate from generic evidence")
        if visual.get("data") != "synthetic_only" or visual.get("browser_network_requests") != 0:
            errors.append("live host visual evidence must be synthetic and offline")
        if visual.get("manifest") != VISUAL_MANIFEST_PATH.relative_to(ROOT).as_posix():
            errors.append("live host visual manifest path is invalid")
        if visual.get("capture_command") != (
            "cd spfx/nac-bpmn-viewer && npm run workbench:live:capture"
        ):
            errors.append("live host visual capture command is invalid")
        if visual.get("required_source_sha256_bindings") != list(EXPECTED_SOURCE_BINDINGS):
            errors.append("live host source hash bindings are incomplete")
        contract_cases = visual.get("required_cases")
        expected_contract_cases = [
            {"id": case_id, **{key: value for key, value in expected.items() if key != "file"}}
            for case_id, expected in EXPECTED_VISUAL_CASES.items()
        ]
        if contract_cases != expected_contract_cases:
            errors.append("live host visual cases are not exactly contract-bound")

    if fixture:
        content = fixture.get("content")
        if not isinstance(content, dict):
            errors.append("canonicalization fixture content is invalid")
        else:
            canonical = json.dumps(
                content,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            if fixture.get("canonical_utf8_json") != canonical:
                errors.append("canonicalization golden JSON drifted")
            digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if fixture.get("sha256") != digest:
                errors.append("canonicalization golden SHA-256 drifted")
            if _contains_number(content):
                errors.append("canonicalization fixture content must not contain numbers")

    if verification:
        if verification.get("contract_id") != "verification.workbench_live_read_binding":
            errors.append("live binding verification contract ID is invalid")
        if verification.get("domain_contract_id") != "nac.workbench_live_read_binding":
            errors.append("live binding verification domain link is invalid")
        if verification.get("acceptance_ids") != [f"AC-{index}" for index in range(1, 9)]:
            errors.append("verification acceptance IDs do not match Issue #725")
        thresholds = verification.get("thresholds", {})
        if thresholds.get("maximum_live_writes") != 0:
            errors.append("live read verification must allow zero live writes")
        if thresholds.get("maximum_tenant_deployments") != 0:
            errors.append("live read verification must allow zero tenant deployments")
        if thresholds.get("maximum_snapshot_bytes") != 131072:
            errors.append("verification snapshot limit is invalid")
        if thresholds.get("minimum_visual_viewports") != 3:
            errors.append("live host verification must cover three responsive viewports")
        if thresholds.get("minimum_live_host_visual_cases") != 6:
            errors.append("live host verification must require six visual cases")
        if thresholds.get("minimum_live_host_runtime_states") != 4:
            errors.append("live host verification must cover four runtime states")
        checks = verification.get("checks", [])
        for required_check in (
            "cd spfx/nac-bpmn-viewer && npm run workbench:capture",
            "cd spfx/nac-bpmn-viewer && npm run workbench:live:capture",
            "python3 scripts/validate_workbench_live_read_binding.py",
        ):
            if required_check not in checks:
                errors.append(f"live binding verification check missing: {required_check}")

    if generic:
        hosts = generic.get("hosts", {})
        if hosts.get("live_webpart_binding") is not True:
            errors.append("generic workbench contract does not mark the reviewed live host binding")
        if "spfx_teams" not in hosts.get("current", []):
            errors.append("SPFx/Teams is not registered as a current Workbench host")

    if visual_manifest:
        _validate_visual_manifest(visual_manifest, errors)

    _source_markers(
        SERVER_PATH,
        (
            "ALLOWED_WORKSPACE_ID",
            "ALLOWED_MATTER_ID",
            "ALLOWED_PURPOSE",
            "build_workbench_projection",
            "redaction",
        ),
        errors,
    )
    _source_markers(
        FASTAPI_PATH,
        ("workbench-snapshot", "Cache-Control", "no-store"),
        errors,
    )
    _source_markers(
        CLIENT_PATH,
        ("workbench-snapshot", "131072", "parseNacWorkbenchProjectionJson"),
        errors,
    )
    _source_markers(
        HOST_PATH,
        ("WorkbenchPanel", "generation", "AbortController"),
        errors,
    )
    _source_markers(
        WEBPART_PATH,
        ("NacWorkbenchHost", "loadNacWorkbenchSnapshot", "loadNacBffWorkspace"),
        errors,
    )
    _source_markers(
        CI_PATH,
        (
            '"src/nac_bff/**/*.py"',
            '"src/nac_cli/**/*.py"',
            '"src/nac_m365_graph/**/*.py"',
            '"assets/docs/**"',
            "pip install -e . fastapi==0.116.1 httpx==0.28.1",
            "npx --no-install playwright install --with-deps chromium",
            "npm run workbench:capture",
            "npm run workbench:live:capture",
            "git diff --exit-code -- assets/docs/workbench-live-read-binding",
            "workbench-live-host-compiled",
            "NacWorkbenchHost.js",
            "NacWorkbenchHost.styles.js",
        ),
        errors,
    )
    _source_markers(
        PACKAGE_PATH,
        (
            '"workbench:capture"',
            '"workbench:live:fixture"',
            '"workbench:live:capture"',
        ),
        errors,
    )
    return errors


def _validate_visual_manifest(manifest: dict, errors: list[str]) -> None:
    if manifest.get("schemaVersion") != "nac.workbench-live-read-host-visual-evidence/v1":
        errors.append("live host visual evidence schema is invalid")
    if manifest.get("syntheticOnly") is not True or manifest.get("browserNetworkRequests") != 0:
        errors.append("live host visual evidence must be synthetic and offline")
    if manifest.get("fixtureClock") != "2026-08-01T09:01:00Z":
        errors.append("live host visual fixture clock is not deterministic")

    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != len(EXPECTED_VISUAL_CASES):
        errors.append("live host visual evidence cases are incomplete")
    else:
        case_ids = {
            item.get("id") for item in cases if isinstance(item, dict)
        }
        if case_ids != set(EXPECTED_VISUAL_CASES):
            errors.append("live host visual evidence case IDs are incomplete")
        else:
            for item in cases:
                _validate_visual_case(item, errors)

    bindings = manifest.get("sourceBindings")
    if not isinstance(bindings, dict) or set(bindings) != set(EXPECTED_SOURCE_BINDINGS):
        errors.append("live host visual source bindings are incomplete")
    else:
        for name, expected_path in EXPECTED_SOURCE_BINDINGS.items():
            _verify_named_binding(name, bindings.get(name), expected_path, errors)

    harness = manifest.get("visualHarness")
    if not isinstance(harness, list) or _manifest_paths(harness) != EXPECTED_VISUAL_HARNESS:
        errors.append("live host visual harness bindings are incomplete")
    else:
        _verify_manifest_entries(harness, errors, require_present=True)

    artifacts = manifest.get("buildArtifacts")
    if not isinstance(artifacts, list) or _manifest_paths(artifacts) != EXPECTED_BUILD_ARTIFACTS:
        errors.append("live host visual build bindings are incomplete")
    else:
        artifact_paths = [ROOT / item["relativePath"] for item in artifacts]
        present = [path.is_file() and not path.is_symlink() for path in artifact_paths]
        require_build = os.environ.get("NAC_REQUIRE_WORKBENCH_LIVE_BUILD_EVIDENCE") == "1"
        if any(present) and not all(present):
            errors.append("live host compiled visual evidence is only partially present")
        _verify_manifest_entries(
            artifacts,
            errors,
            require_present=require_build or any(present),
        )

    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        errors.append("live host visual runtime provenance is missing")
    else:
        if not re.fullmatch(r"v22\.[0-9]+\.[0-9]+", str(runtime.get("nodeVersion", ""))):
            errors.append("live host visual Node runtime is not pinned to Node 22")
        if not str(runtime.get("npmUserAgent", "")).startswith("npm/"):
            errors.append("live host visual npm runtime provenance is missing")
        expected_tools = {
            "playwrightVersion": "1.55.0",
            "webpackVersion": "5.105.4",
            "typescriptVersion": "5.8.3",
            "heftVersion": "1.2.17",
        }
        for field, expected in expected_tools.items():
            if runtime.get(field) != expected:
                errors.append(f"live host visual runtime drift: {field}")


def _validate_visual_case(item: object, errors: list[str]) -> None:
    if not isinstance(item, dict) or item.get("id") not in EXPECTED_VISUAL_CASES:
        errors.append("live host visual evidence case is invalid")
        return
    case_id = item["id"]
    expected = EXPECTED_VISUAL_CASES[case_id]
    for field in ("state", "layout", "file", "viewport"):
        if item.get(field) != expected[field]:
            errors.append(f"{case_id}: live host visual {field} drift")
    digest = item.get("sha256")
    file_name = item.get("file")
    if not isinstance(file_name, str):
        errors.append(f"{case_id}: live host visual filename is invalid")
        return
    image_path = VISUAL_ROOT / file_name
    _verify_digest(image_path, digest, errors)
    dimensions = _png_dimensions(image_path, errors)
    if dimensions is not None:
        width, height = dimensions
        if item.get("imageWidth") != width or item.get("imageHeight") != height:
            errors.append(f"{case_id}: live host PNG dimensions are not manifest-bound")
        viewport = expected["viewport"]
        if width <= 0 or height <= 0 or width > viewport["width"]:
            errors.append(f"{case_id}: live host PNG dimensions exceed the viewport width")


def _verify_named_binding(
    name: str, item: object, expected_path: str, errors: list[str]
) -> None:
    if not isinstance(item, dict) or item.get("relativePath") != expected_path:
        errors.append(f"live host visual source binding is invalid: {name}")
        return
    _verify_manifest_entries([item], errors, require_present=True)


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
            errors.append("live host visual manifest entry is invalid")
            continue
        digest = item.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            errors.append("live host visual manifest digest is invalid")
            continue
        path = ROOT / item["relativePath"]
        if path.is_file() and not path.is_symlink():
            _verify_digest(path, digest, errors)
        elif require_present:
            errors.append(f"live host visual evidence file missing: {path.relative_to(ROOT)}")


def _verify_digest(path: Path, expected: object, errors: list[str]) -> None:
    if path.is_symlink() or not path.is_file():
        errors.append(f"live host visual evidence file missing: {path.relative_to(ROOT)}")
        return
    if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
        errors.append(f"live host visual digest is invalid: {path.relative_to(ROOT)}")
        return
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected != actual:
        errors.append(f"live host visual digest drift: {path.relative_to(ROOT)}")


def _png_dimensions(path: Path, errors: list[str]) -> tuple[int, int] | None:
    if path.is_symlink() or not path.is_file():
        return None
    data = path.read_bytes()[:24]
    if (
        len(data) != 24
        or data[:8] != b"\x89PNG\r\n\x1a\n"
        or data[12:16] != b"IHDR"
    ):
        errors.append(f"live host visual screenshot is not a PNG: {path.relative_to(ROOT)}")
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _contains_number(value: object) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, list):
        return any(_contains_number(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_number(item) for item in value.values())
    return True


def _source_markers(path: Path, markers: tuple[str, ...], errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"required live binding source missing: {path.relative_to(ROOT)}")
        return
    source = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in source:
            errors.append(f"{path.relative_to(ROOT)}: required marker missing: {marker}")


def _object(path: Path, errors: list[str]) -> dict:
    if not path.is_file():
        errors.append(f"required file missing: {path.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"JSON root must be an object: {path.relative_to(ROOT)}")
        return {}
    return value


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: Workbench live read binding, canonicalization and host boundary are enforced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
