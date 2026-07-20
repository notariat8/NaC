from __future__ import annotations

import hashlib
import json
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from notary_kg.business_case_inventory import build_business_case_inventory
from notary_kg.business_case_type_runtime import BusinessCaseTypeCatalog


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
FOUNDATION_PATH = Path(
    "deploy/m365/teams-sharepoint/nac-business-case-type-foundation.notary-team-01.json"
)
SOURCE_SCHEMA_PATH = Path("deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json")
CATALOG_VERSION = "fcf1c7ba1a35980f5f1d371381ae5c218cd3ce94372f2c1df821f2ad40d2fab0"
WORKSPACE_ID = "notary_team_01"
REGISTRY_NAME = "Vorgangsartenregister"
AKTEN_NAME = "Akten"
LEGACY_COLUMN_NAME = "Vorgangstyp"
ADDITIVE_COLUMN_NAME = "VorgangstypId"
REGISTRY_FIELDS = (
    "Title",
    "BusinessCaseTypeId",
    "LifecycleStatus",
    "Selectable",
    "CatalogVersion",
)
MAX_COLLECTION_PAGES = 20


class BusinessCaseTypeFoundationGraphPort(Protocol):
    def get(self, path: str) -> dict[str, Any]: ...

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class FoundationValidation:
    status: str
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FoundationApplyRequest:
    workspace_id: str
    expected_plan_sha256: str
    approval_reference: str
    reason: str
    owner_approved: bool
    execute_live_foundation: bool


@dataclass(frozen=True, slots=True)
class _FoundationState:
    registry_list_id: str | None
    akten_column_present: bool
    missing_rows: tuple[dict[str, Any], ...]


class _SafetyStop(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def load_business_case_type_live_foundation(repo_root: Path) -> dict[str, Any]:
    path = repo_root / FOUNDATION_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("foundation manifest must be an object")
    return payload


def validate_business_case_type_live_foundation(
    repo_root: Path, manifest: dict[str, Any] | None = None
) -> FoundationValidation:
    errors: list[str] = []
    try:
        manifest = manifest or load_business_case_type_live_foundation(repo_root)
    except (OSError, json.JSONDecodeError, ValueError):
        return FoundationValidation("FAILED", ("foundation manifest is unavailable or invalid",))

    expected_scalars = {
        "schema_version": "nac.business-case-type-live-foundation/v0.1",
        "contract_id": "m365.business_case_type_live_foundation",
        "leading_issue": "https://github.com/notariat8/NaC/issues/678",
        "mode": "notary_team_01_additive_graph_rest_v1_0",
    }
    for key, expected in expected_scalars.items():
        if manifest.get(key) != expected:
            errors.append(f"foundation {key} mismatch")

    target = _object(manifest.get("target"))
    if target.get("workspace_id") != WORKSPACE_ID:
        errors.append("foundation must target exactly notary_team_01")
    provisioned_path = target.get("provisioned_state")
    if not isinstance(provisioned_path, str) or not provisioned_path:
        errors.append("foundation provisioned state binding is missing")
    else:
        try:
            provisioned = json.loads((repo_root / provisioned_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append("bound provisioned state is unavailable or invalid")
        else:
            workspaces = [
                item
                for item in provisioned.get("workspaces", [])
                if isinstance(item, dict) and item.get("id") == WORKSPACE_ID
            ]
            if len(workspaces) != 1:
                errors.append("provisioned state must resolve notary_team_01 exactly once")
            else:
                workspace = workspaces[0]
                expected_target = {
                    "team_display_name": workspace.get("team_display_name"),
                    "site_id": workspace.get("site_id"),
                    "site_url": workspace.get("site_url"),
                    "akten_list_id": _object(workspace.get("lists")).get(AKTEN_NAME, {}).get("id"),
                }
                for key, expected in expected_target.items():
                    if not isinstance(expected, str) or target.get(key) != expected:
                        errors.append(f"foundation target {key} does not match provisioned state")

    graph = _object(manifest.get("graph"))
    if graph != {
        "base_url": GRAPH_BASE_URL,
        "api_version": "v1.0",
        "rest_only": True,
        "graph_sdk_allowed": False,
        "legacy_sharepoint_api_allowed": False,
        "allowed_methods": ["GET", "POST"],
        "forbidden_methods": ["PATCH", "DELETE"],
        "application_permission": "Sites.FullControl.All",
        "provisioner_binding": {
            "application_display_name": "NaC M365 Provisioning",
            "source_contract": "workflows/contracts/m365-azure-bff-live-activation.contract.json",
            "existing_permission_required": True,
            "permission_change_required": False,
            "permission_mutation_allowed": False,
            "credential_or_consent_change_allowed": False,
        },
    }:
        errors.append("foundation Graph REST v1.0 additive boundary mismatch")

    schema = _object(manifest.get("schema"))
    registry_list = _object(schema.get("registry_list"))
    columns = registry_list.get("columns")
    if registry_list.get("display_name") != REGISTRY_NAME or registry_list.get("template") != "genericList":
        errors.append("foundation registry list shape mismatch")
    if registry_list.get("title_field_role") != "Label":
        errors.append("foundation must bind the built-in Title field as Label")
    if not isinstance(columns, list) or [item.get("name") for item in columns if isinstance(item, dict)] != [
        "BusinessCaseTypeId",
        "LifecycleStatus",
        "Selectable",
        "CatalogVersion",
    ]:
        errors.append("foundation registry must define exactly four ordered custom columns")
    elif not all(_column_definition_is_bounded(item) for item in columns):
        errors.append("foundation registry column definition is not bounded")

    additive = _object(schema.get("akten_additive_column"))
    if additive.get("name") != ADDITIVE_COLUMN_NAME or not _column_definition_is_bounded(additive):
        errors.append("foundation Akten.VorgangstypId column mismatch")
    legacy = _object(schema.get("legacy_akten_column"))
    if legacy.get("name") != LEGACY_COLUMN_NAME or legacy.get("mutation_allowed") is not False:
        errors.append("foundation must keep legacy Akten.Vorgangstyp immutable")
    errors.extend(_validate_legacy_source(repo_root, legacy))

    registry = _object(manifest.get("registry"))
    rows = registry.get("rows")
    if registry.get("catalog_version") != CATALOG_VERSION:
        errors.append("foundation catalog version mismatch")
    if registry.get("canonical_row_count") != 20 or registry.get("alias_row_count") != 0:
        errors.append("foundation must contain exactly 20 canonical rows and zero aliases")
    if not isinstance(rows, list) or len(rows) != 20:
        errors.append("foundation registry row count mismatch")
    else:
        errors.extend(_validate_registry_rows_against_repo(repo_root, rows))

    boundary = _object(manifest.get("apply_boundary"))
    for key in ("owner_gate_required", "plan_hash_required", "additive_only"):
        if boundary.get(key) is not True:
            errors.append(f"foundation apply boundary must require {key}")
    for key in (
        "migration_allowed",
        "deletes_allowed",
        "rollback_allowed",
        "other_workspaces_allowed",
        "live_execution_in_issue_678_allowed",
        "raw_graph_payload_evidence_allowed",
        "tokens_or_auth_headers_in_evidence_allowed",
    ):
        if boundary.get(key) is not False:
            errors.append(f"foundation apply boundary must keep {key} false")
    return FoundationValidation("PASSED" if not errors else "FAILED", tuple(errors))


def build_business_case_type_live_foundation_plan(
    repo_root: Path, *, workspace_id: str = WORKSPACE_ID
) -> dict[str, Any]:
    manifest = load_business_case_type_live_foundation(repo_root)
    validation = validate_business_case_type_live_foundation(repo_root, manifest)
    if workspace_id != WORKSPACE_ID:
        return _blocked_plan("WORKSPACE_SCOPE_MISMATCH")
    if validation.errors:
        return {
            "schema_version": "nac.business-case-type-live-foundation-plan/v0.1",
            "status": "FAILED",
            "error_code": "FOUNDATION_CONTRACT_DRIFT",
            "errors": list(validation.errors),
            "summary": _plan_summary(0),
        }

    registry = manifest["registry"]
    steps = [
        {
            "sequence": 1,
            "operation": "preflight_workspace_and_schema",
            "method": "GET",
            "path_templates": [
                "/sites/{bound-site-id}",
                "/sites/{bound-site-id}/lists",
                "/sites/{bound-site-id}/lists/{bound-akten-list-id}/columns",
            ],
            "stops_before_write_on_mismatch": True,
        },
        {
            "sequence": 2,
            "operation": "create_registry_list_if_absent",
            "method": "POST",
            "path_template": "/sites/{bound-site-id}/lists",
            "maximum_mutations": 1,
        },
        {
            "sequence": 3,
            "operation": "create_akten_vorgangstyp_id_if_absent",
            "method": "POST",
            "path_template": "/sites/{bound-site-id}/lists/{bound-akten-list-id}/columns",
            "maximum_mutations": 1,
        },
        {
            "sequence": 4,
            "operation": "create_missing_canonical_registry_rows",
            "method": "POST",
            "path_template": "/sites/{bound-site-id}/lists/{resolved-registry-list-id}/items",
            "maximum_mutations": 20,
            "canonical_row_count": 20,
        },
    ]
    binding = {
        "workspace_id": WORKSPACE_ID,
        "target_sha256": _sha256_json(manifest["target"]),
        "schema_sha256": _sha256_json(manifest["schema"]),
        "registry_sha256": _sha256_json(registry),
        "graph_sha256": _sha256_json(manifest["graph"]),
        "catalog_version": CATALOG_VERSION,
    }
    plan_core = {
        "schema_version": "nac.business-case-type-live-foundation-plan/v0.1",
        "contract_id": "m365.business_case_type_live_foundation_plan",
        "leading_issue": "https://github.com/notariat8/NaC/issues/678",
        "status": "PASSED",
        "mode": "offline_additive_plan",
        "binding": binding,
        "summary": _plan_summary(22),
        "steps": steps,
        "guardrails": {
            "workspace_id_exact": WORKSPACE_ID,
            "graph_base_url": GRAPH_BASE_URL,
            "allowed_methods": ["GET", "POST"],
            "legacy_vorgangstyp_mutation_allowed": False,
            "migration_allowed": False,
            "delete_allowed": False,
            "rollback_allowed": False,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "live_execution_composed": False,
        },
    }
    plan_sha256 = _sha256_json(plan_core)
    return {
        **plan_core,
        "plan_sha256": plan_sha256,
        "owner_gate": {
            "required_before_runner": True,
            "plan_sha256_required": plan_sha256,
            "approval_text": (
                "Freigabe: BusinessCaseType Live Foundation additiv in notary_team_01 "
                f"mit plan_sha256={plan_sha256}; Graph REST v1.0; keine Migration, Deletes oder Rollbacks."
            ),
        },
    }


def build_business_case_type_live_foundation_apply_boundary(
    repo_root: Path, request: FoundationApplyRequest
) -> dict[str, Any]:
    plan = build_business_case_type_live_foundation_plan(
        repo_root, workspace_id=request.workspace_id
    )
    reasons: list[str] = []
    if request.workspace_id != WORKSPACE_ID:
        reasons.append("WORKSPACE_SCOPE_MISMATCH")
    if plan.get("status") != "PASSED":
        reasons.append("FOUNDATION_PLAN_NOT_PASSED")
    if request.expected_plan_sha256 != plan.get("plan_sha256"):
        reasons.append("PLAN_HASH_MISMATCH")
    if request.owner_approved is not True:
        reasons.append("OWNER_GATE_CLOSED")
    if request.execute_live_foundation is not True:
        reasons.append("EXECUTION_GATE_CLOSED")
    if not request.approval_reference:
        reasons.append("APPROVAL_REFERENCE_MISSING")
    if not request.reason:
        reasons.append("REASON_MISSING")
    ready = not reasons
    return {
        "schema_version": "nac.business-case-type-live-foundation-apply-boundary/v0.1",
        "status": "READY_FOR_INJECTED_RUNNER" if ready else "BLOCKED",
        "error_codes": reasons,
        "plan_sha256": plan.get("plan_sha256", ""),
        "approval_reference_sha256": _sha256_text(request.approval_reference),
        "reason_sha256": _sha256_text(request.reason),
        "summary": {
            "owner_gate_satisfied": ready,
            "workspace_id_exact": request.workspace_id == WORKSPACE_ID,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "live_execution_composed": False,
            "injected_runner_required": True,
        },
    }


def run_business_case_type_live_foundation(
    client: BusinessCaseTypeFoundationGraphPort,
    repo_root: Path,
    request: FoundationApplyRequest,
) -> dict[str, Any]:
    boundary = build_business_case_type_live_foundation_apply_boundary(repo_root, request)
    metrics = {"reads": 0, "mutations": 0}
    operations: list[str] = []
    if boundary["status"] != "READY_FOR_INJECTED_RUNNER":
        return _runner_result(boundary, metrics, operations, "BLOCKED", boundary["error_codes"][0])

    manifest = load_business_case_type_live_foundation(repo_root)
    try:
        state = _inspect_foundation_state(client, manifest, metrics)
    except _SafetyStop as exc:
        return _runner_result(boundary, metrics, operations, "BLOCKED", exc.code)
    except Exception:
        return _runner_result(boundary, metrics, operations, "FAILED", "GRAPH_READ_FAILED")

    target = manifest["target"]
    site_segment = _segment(target["site_id"])
    try:
        if state.registry_list_id is None:
            registry = manifest["schema"]["registry_list"]
            _post(
                client,
                f"/sites/{site_segment}/lists",
                {
                    "displayName": registry["display_name"],
                    "description": registry["description"],
                    "columns": registry["columns"],
                    "list": {"template": registry["template"]},
                },
                metrics,
            )
            operations.append("create_registry_list")
            state = _inspect_foundation_state(client, manifest, metrics)
            if state.registry_list_id is None:
                raise _SafetyStop("REGISTRY_CREATE_READBACK_FAILED")

        if not state.akten_column_present:
            akten_id = _segment(target["akten_list_id"])
            _post(
                client,
                f"/sites/{site_segment}/lists/{akten_id}/columns",
                manifest["schema"]["akten_additive_column"],
                metrics,
            )
            operations.append("create_akten_vorgangstyp_id")
            state = _inspect_foundation_state(client, manifest, metrics)
            if not state.akten_column_present:
                raise _SafetyStop("AKTEN_COLUMN_CREATE_READBACK_FAILED")

        for row in state.missing_rows:
            registry_id = _segment(state.registry_list_id or "")
            _post(
                client,
                f"/sites/{site_segment}/lists/{registry_id}/items",
                {"fields": row},
                metrics,
            )
            operations.append("create_registry_row")
            readback = _inspect_foundation_state(client, manifest, metrics)
            if row["BusinessCaseTypeId"] in {
                item["BusinessCaseTypeId"] for item in readback.missing_rows
            }:
                raise _SafetyStop("REGISTRY_ROW_CREATE_READBACK_FAILED")
            state = readback
    except _SafetyStop as exc:
        return _runner_result(boundary, metrics, operations, "FAILED", exc.code)
    except Exception:
        return _runner_result(boundary, metrics, operations, "FAILED", "GRAPH_MUTATION_FAILED")

    try:
        final_state = _inspect_foundation_state(client, manifest, metrics)
    except Exception:
        return _runner_result(boundary, metrics, operations, "FAILED", "FINAL_READBACK_FAILED")
    if (
        final_state.registry_list_id is None
        or not final_state.akten_column_present
        or final_state.missing_rows
    ):
        return _runner_result(boundary, metrics, operations, "FAILED", "FINAL_READBACK_INCOMPLETE")
    return _runner_result(boundary, metrics, operations, "PASSED", None)


def format_business_case_type_live_foundation_plan(payload: dict[str, Any]) -> str:
    lines = [
        f"STATUS: {payload.get('status', 'FAILED')}",
        f"Workspace: {WORKSPACE_ID}",
        f"Plan SHA-256: {payload.get('plan_sha256', '')}",
        f"Maximale additive Mutationen: {payload.get('summary', {}).get('maximum_mutation_count', 0)}",
        "Graph REST: v1.0 GET/POST only",
        "Legacy Akten.Vorgangstyp: unverändert",
    ]
    return "\n".join(lines) + "\n"


def _inspect_foundation_state(
    client: BusinessCaseTypeFoundationGraphPort,
    manifest: dict[str, Any],
    metrics: dict[str, int],
) -> _FoundationState:
    target = manifest["target"]
    site_segment = _segment(target["site_id"])
    site = _get_object(
        client,
        f"/sites/{site_segment}?$select=id,displayName,webUrl",
        metrics,
    )
    if (
        site.get("id") != target["site_id"]
        or site.get("displayName") != target["team_display_name"]
        or site.get("webUrl") != target["site_url"]
    ):
        raise _SafetyStop("WORKSPACE_BINDING_DRIFT")

    lists_path = f"/sites/{site_segment}/lists?$select=id,displayName,list&$top=200"
    lists = _get_collection(client, lists_path, metrics)
    akten_matches = [item for item in lists if item.get("displayName") == AKTEN_NAME]
    if len(akten_matches) != 1 or akten_matches[0].get("id") != target["akten_list_id"]:
        raise _SafetyStop("AKTEN_LIST_BINDING_DRIFT")
    registry_matches = [item for item in lists if item.get("displayName") == REGISTRY_NAME]
    if len(registry_matches) > 1:
        raise _SafetyStop("REGISTRY_LIST_DUPLICATE")
    if registry_matches and _object(registry_matches[0].get("list")).get("template") != "genericList":
        raise _SafetyStop("REGISTRY_LIST_SCHEMA_DRIFT")

    akten_id = _segment(target["akten_list_id"])
    akten_columns = _get_collection(
        client,
        f"/sites/{site_segment}/lists/{akten_id}/columns?$top=200",
        metrics,
    )
    legacy_matches = [item for item in akten_columns if item.get("name") == LEGACY_COLUMN_NAME]
    if len(legacy_matches) != 1 or not _legacy_column_matches(
        legacy_matches[0], manifest["schema"]["legacy_akten_column"]
    ):
        raise _SafetyStop("LEGACY_VORGANGSTYP_SCHEMA_DRIFT")
    additive_matches = [item for item in akten_columns if item.get("name") == ADDITIVE_COLUMN_NAME]
    if len(additive_matches) > 1:
        raise _SafetyStop("AKTEN_VORGANGSTYP_ID_DUPLICATE")
    if additive_matches and not _column_matches(
        additive_matches[0], manifest["schema"]["akten_additive_column"]
    ):
        raise _SafetyStop("AKTEN_VORGANGSTYP_ID_SCHEMA_DRIFT")

    if not registry_matches:
        return _FoundationState(None, bool(additive_matches), tuple(manifest["registry"]["rows"]))
    registry_id = registry_matches[0].get("id")
    if not isinstance(registry_id, str) or not registry_id:
        raise _SafetyStop("REGISTRY_LIST_ID_INVALID")
    registry_segment = _segment(registry_id)
    registry_columns = _get_collection(
        client,
        f"/sites/{site_segment}/lists/{registry_segment}/columns?$top=200",
        metrics,
    )
    title_matches = [item for item in registry_columns if item.get("name") == "Title"]
    if len(title_matches) != 1 or not isinstance(title_matches[0].get("text"), dict):
        raise _SafetyStop("REGISTRY_TITLE_SCHEMA_DRIFT")
    for expected in manifest["schema"]["registry_list"]["columns"]:
        matches = [
            item for item in registry_columns if item.get("name") == expected["name"]
        ]
        if len(matches) != 1 or not _column_matches(matches[0], expected):
            raise _SafetyStop("REGISTRY_COLUMN_SCHEMA_DRIFT")

    selected = ",".join(REGISTRY_FIELDS)
    items = _get_collection(
        client,
        (
            f"/sites/{site_segment}/lists/{registry_segment}/items?$select=id,eTag"
            f"&$expand=fields($select={selected})&$top=200"
        ),
        metrics,
    )
    expected_by_id = {
        row["BusinessCaseTypeId"]: row for row in manifest["registry"]["rows"]
    }
    seen: set[str] = set()
    for item in items:
        fields = item.get("fields")
        if not isinstance(fields, dict):
            raise _SafetyStop("REGISTRY_ROW_SCHEMA_DRIFT")
        identifier = fields.get("BusinessCaseTypeId")
        if not isinstance(identifier, str) or identifier in seen:
            raise _SafetyStop("REGISTRY_ROW_DUPLICATE_OR_INVALID")
        seen.add(identifier)
        expected = expected_by_id.get(identifier)
        if expected is None or any(fields.get(key) != expected[key] for key in REGISTRY_FIELDS):
            raise _SafetyStop("REGISTRY_ROW_SCHEMA_DRIFT")
    missing = tuple(row for row in manifest["registry"]["rows"] if row["BusinessCaseTypeId"] not in seen)
    return _FoundationState(registry_id, bool(additive_matches), missing)


def _get_object(
    client: BusinessCaseTypeFoundationGraphPort,
    path: str,
    metrics: dict[str, int],
) -> dict[str, Any]:
    metrics["reads"] += 1
    payload = client.get(path)
    if not isinstance(payload, dict):
        raise _SafetyStop("GRAPH_RESPONSE_INVALID")
    return payload


def _get_collection(
    client: BusinessCaseTypeFoundationGraphPort,
    path: str,
    metrics: dict[str, int],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current = path
    collection_path = urllib.parse.urlsplit(path).path
    visited: set[str] = set()
    for _page in range(MAX_COLLECTION_PAGES):
        if current in visited:
            raise _SafetyStop("GRAPH_PAGING_INVALID")
        visited.add(current)
        payload = _get_object(client, current, metrics)
        value = payload.get("value")
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise _SafetyStop("GRAPH_COLLECTION_INVALID")
        items.extend(value)
        next_link = payload.get("@odata.nextLink")
        if next_link is None:
            return items
        if not isinstance(next_link, str):
            raise _SafetyStop("GRAPH_PAGING_INVALID")
        parsed = urllib.parse.urlsplit(next_link)
        if parsed.scheme != "https" or parsed.netloc != "graph.microsoft.com":
            raise _SafetyStop("GRAPH_PAGING_INVALID")
        prefix = "/v1.0"
        if not parsed.path.startswith(prefix) or parsed.path[len(prefix) :] != collection_path:
            raise _SafetyStop("GRAPH_PAGING_INVALID")
        current = parsed.path[len(prefix) :] + (f"?{parsed.query}" if parsed.query else "")
    raise _SafetyStop("GRAPH_PAGING_LIMIT")


def _post(
    client: BusinessCaseTypeFoundationGraphPort,
    path: str,
    payload: dict[str, Any],
    metrics: dict[str, int],
) -> None:
    metrics["mutations"] += 1
    response = client.post(path, payload)
    if not isinstance(response, dict):
        raise _SafetyStop("GRAPH_MUTATION_RESPONSE_INVALID")


def _column_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key in ("name", "displayName", "required", "indexed", "enforceUniqueValues"):
        expected_value = expected.get(key, False if key in {"indexed", "enforceUniqueValues"} else None)
        actual_value = actual.get(key, False if key in {"indexed", "enforceUniqueValues"} else None)
        if actual_value != expected_value:
            return False
    facets = [name for name in ("text", "choice", "boolean") if name in expected]
    if len(facets) != 1:
        return False
    facet = facets[0]
    actual_facet = actual.get(facet)
    expected_facet = expected[facet]
    return isinstance(actual_facet, dict) and all(
        actual_facet.get(key) == value for key, value in expected_facet.items()
    )


def _legacy_column_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    choice = actual.get("choice")
    return (
        actual.get("name") == LEGACY_COLUMN_NAME
        and actual.get("required") is True
        and isinstance(choice, dict)
        and choice.get("allowTextEntry", False) is False
        and choice.get("choices") == expected.get("choices")
        and not isinstance(actual.get("text"), dict)
        and not isinstance(actual.get("boolean"), dict)
    )


def _validate_legacy_source(repo_root: Path, expected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        source = json.loads((repo_root / SOURCE_SCHEMA_PATH).read_text(encoding="utf-8"))
        akten = next(
            item
            for item in source["sharepoint"]["lists"]
            if item.get("display_name") == AKTEN_NAME
        )
        legacy = next(item for item in akten["columns"] if item.get("name") == LEGACY_COLUMN_NAME)
    except (OSError, json.JSONDecodeError, KeyError, StopIteration, TypeError):
        return ["legacy Akten.Vorgangstyp source baseline is unavailable"]
    fingerprint = _sha256_json(legacy)
    if fingerprint != expected.get("baseline_fingerprint_sha256"):
        errors.append("legacy Akten.Vorgangstyp source fingerprint drift")
    if (
        legacy.get("type") != expected.get("type")
        or legacy.get("required") != expected.get("required")
        or legacy.get("choices") != expected.get("choices")
    ):
        errors.append("legacy Akten.Vorgangstyp source shape drift")
    return errors


def _validate_registry_rows_against_repo(
    repo_root: Path, rows: list[dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    try:
        catalog = BusinessCaseTypeCatalog.from_repo(repo_root)
        inventory = build_business_case_inventory(repo_root)
    except Exception:
        return ["repo BusinessCaseType catalog is unavailable"]
    if catalog.catalog_version != CATALOG_VERSION:
        errors.append("repo BusinessCaseType catalog version drift")
    canonical = {
        item["business_case_type_id"]: item["title"]
        for item in inventory.get("business_cases", [])
        if isinstance(item, dict) and item.get("catalog_entry_kind") == "canonical"
    }
    identifiers = [row.get("BusinessCaseTypeId") for row in rows]
    if len(set(identifiers)) != 20 or set(identifiers) != set(canonical):
        errors.append("foundation canonical BusinessCaseTypeId set drift")
    expected_keys = set(REGISTRY_FIELDS)
    for row in rows:
        identifier = row.get("BusinessCaseTypeId")
        if set(row) != expected_keys:
            errors.append("foundation registry row field shape drift")
            continue
        if row.get("Title") != canonical.get(identifier):
            errors.append(f"foundation registry title drift: {identifier}")
        if (
            row.get("LifecycleStatus") != "active"
            or row.get("Selectable") is not True
            or row.get("CatalogVersion") != CATALOG_VERSION
        ):
            errors.append(f"foundation registry lifecycle/version drift: {identifier}")
    return errors


def _column_definition_is_bounded(value: object) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("name"), str):
        return False
    facets = [name for name in ("text", "choice", "boolean") if name in value]
    if len(facets) != 1 or type(value.get("required")) is not bool:
        return False
    if facets[0] == "text":
        text = value["text"]
        return (
            isinstance(text, dict)
            and text.get("allowMultipleLines") is False
            and type(text.get("maxLength")) is int
            and 1 <= text["maxLength"] <= 255
        )
    if facets[0] == "choice":
        choice = value["choice"]
        return (
            isinstance(choice, dict)
            and choice.get("allowTextEntry") is False
            and choice.get("choices") == ["active", "deprecated", "retired"]
        )
    return value["boolean"] == {}


def _runner_result(
    boundary: dict[str, Any],
    metrics: dict[str, int],
    operations: list[str],
    status: str,
    error_code: str | None,
) -> dict[str, Any]:
    result = {
        "schema_version": "nac.business-case-type-live-foundation-runner-evidence/v0.1",
        "status": status,
        "error_code": error_code,
        "plan_sha256": boundary.get("plan_sha256", ""),
        "approval_reference_sha256": boundary.get("approval_reference_sha256", ""),
        "reason_sha256": boundary.get("reason_sha256", ""),
        "summary": {
            "workspace_id": WORKSPACE_ID,
            "graph_read_count": metrics["reads"],
            "mutation_count": metrics["mutations"],
            "registry_list_create_count": operations.count("create_registry_list"),
            "akten_column_create_count": operations.count("create_akten_vorgangstyp_id"),
            "registry_row_create_count": operations.count("create_registry_row"),
            "delete_count": 0,
            "rollback_count": 0,
            "migration_count": 0,
            "raw_graph_payload_count": 0,
            "token_or_auth_header_count": 0,
        },
        "guardrails": {
            "graph_rest_v1_0_only": True,
            "additive_only": True,
            "legacy_vorgangstyp_unchanged": True,
            "automatic_rollback_allowed": False,
            "evidence_redacted": True,
        },
    }
    return result


def _blocked_plan(error_code: str) -> dict[str, Any]:
    return {
        "schema_version": "nac.business-case-type-live-foundation-plan/v0.1",
        "status": "BLOCKED",
        "error_code": error_code,
        "summary": _plan_summary(0),
    }


def _plan_summary(maximum_mutation_count: int) -> dict[str, Any]:
    return {
        "workspace_count": 1,
        "canonical_registry_row_count": 20,
        "alias_registry_row_count": 0,
        "maximum_mutation_count": maximum_mutation_count,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
    }


def _object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _segment(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def _sha256_json(value: object) -> str:
    canonical = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
