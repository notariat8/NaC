from __future__ import annotations

import hashlib
import json
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Protocol

from nac_bff.bpmn_asset import BpmnAssetError, CanonicalBpmnAssetFilePort
from nac_mvp_test_environment import (
    BPMN_PROCESS_KEY,
    BPMN_PROFILE_VERSION,
    BPMN_SHA256,
    BPMN_SOURCE_PATH,
    BUSINESS_CASE_TYPE_ID,
    DEADLINE,
    KG_GRAPH_ID,
    KG_SCHEMA_VERSION,
    KG_SHA256,
    KG_SOURCE_PATH,
    MATTER_ID,
    MATTER_STATUS,
    TASKS,
    WORKFLOW_VERSION,
)

from .mcp_runtime import DEFAULT_MCP_CONTRACT, RuntimeContext, load_mcp_contract, plan_tool_request
from .mvp_test_environment_binding import (
    MvpTestEnvironmentBindingError,
    validate_mvp_test_environment_binding,
)
from .privileged_change import DEFAULT_PROVISIONED_STATE, load_provisioned_state


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_WORKSPACE_ID = "notary_team_01"
SYNTHETIC_CASE_ID = MATTER_ID
SYNTHETIC_TASK_IDS = tuple(task["task_id"] for task in TASKS)
SYNTHETIC_DEADLINE_DUE_DATE = DEADLINE
DEFAULT_MVP_TEST_ENVIRONMENT_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "m365" / "mvp-test-environment" / "synthetic-bpmn.fixture.json"
)
EXPECTED_BPMN_PACKAGE = "@notariat8/nac-bpmn-viewer"


class GraphSmokeClient(Protocol):
    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def get(self, path: str) -> dict[str, Any]:
        ...

    def delete(self, path: str) -> dict[str, Any]:
        ...


class AccessDecisionFunction(Protocol):
    def __call__(self, request: dict[str, str]) -> str | Mapping[str, Any]:
        ...


class _SmokeFailure(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(slots=True)
class _WriteTarget:
    kind: str
    collection_path: str
    read_path: str
    key_field: str
    key_value: str
    payload: dict[str, Any]
    attempted: bool = False
    item_id: str | None = None
    readback_verified: bool = False


def run_mvp_test_environment_smoke(
    client: GraphSmokeClient,
    contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    decision_function: AccessDecisionFunction,
    *,
    workspace_id: str,
    owner_approved: bool,
    correlation_id: str = "mvp-test-environment-smoke",
    fixture_path: Path = DEFAULT_MVP_TEST_ENVIRONMENT_FIXTURE,
    timestamp: str | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    targets: list[_WriteTarget] = []
    role_checks: list[dict[str, Any]] = []
    bpmn_evidence: dict[str, Any] = {"verified": False, "packageBound": False}
    primary_error_code: str | None = None
    cleanup_error_code: str | None = None
    phase = "scope"
    write_count = 0
    readback_count = 0
    cleanup_attempt_count = 0
    cleanup_delete_count = 0
    cleanup_absent_count = 0
    workspace_verified = False
    contract_verified = False
    binding_evidence: dict[str, str] = {}

    try:
        _require_workspace(workspace_id)
        if owner_approved is not True:
            raise _SmokeFailure("OWNER_GATE_CLOSED")
        if not correlation_id:
            raise _SmokeFailure("RUNTIME_CONTEXT_INVALID")

        phase = "contract"
        _validate_contract_boundary(contract)

        phase = "binding"
        try:
            binding_evidence = validate_mvp_test_environment_binding(contract, provisioned_state)
        except MvpTestEnvironmentBindingError as exc:
            raise _SmokeFailure(str(exc)) from exc
        workspace_verified = True
        contract_verified = True

        phase = "fixture"
        bpmn_evidence = _load_and_verify_bpmn_fixture(fixture_path)

        phase = "decision"
        role_checks = _verify_access_decisions(decision_function)

        phase = "planning"
        context = RuntimeContext(
            actor_id="nac-synthetic-mvp-smoke-owner",
            actor_role="runtime_service",
            workspace_id=EXPECTED_WORKSPACE_ID,
            purpose="m365_mvp_test_environment_smoke",
            correlation_id=correlation_id,
            case_id=SYNTHETIC_CASE_ID,
            role_case_gate="open",
            write_approved=owner_approved,
        )
        case_plan = plan_tool_request(
            contract,
            provisioned_state,
            context,
            "case_create",
            _case_arguments(),
        )
        case_read_plan = plan_tool_request(
            contract,
            provisioned_state,
            context,
            "case_get",
            {"case_id": SYNTHETIC_CASE_ID},
        )
        task_arguments = _task_arguments()
        task_plans = [
            plan_tool_request(contract, provisioned_state, context, "task_create", arguments)
            for arguments in task_arguments
        ]
        _assert_write_plan(case_plan, "case_create", "Akten")
        for task_plan, arguments in zip(task_plans, task_arguments, strict=True):
            expected_fields = {"DueDate": arguments["due_date"]} if "due_date" in arguments else None
            _assert_write_plan(task_plan, "task_create", "AufgabenFristen", expected_fields=expected_fields)

        targets = [
            _WriteTarget(
                kind="matter",
                collection_path=case_plan.path,
                read_path=case_read_plan.path,
                key_field="NacCaseId",
                key_value=SYNTHETIC_CASE_ID,
                payload=case_plan.payload or {},
            )
        ]
        for task_id, task_plan in zip(SYNTHETIC_TASK_IDS, task_plans, strict=True):
            targets.append(
                _WriteTarget(
                    kind="task_or_deadline",
                    collection_path=task_plan.path,
                    read_path=_targeted_read_path(task_plan.path, "NacTaskId", task_id),
                    key_field="NacTaskId",
                    key_value=task_id,
                    payload=task_plan.payload or {},
                )
            )

        phase = "preflight"
        for target in targets:
            if _matching_items(client.get(target.read_path), target.key_field, target.key_value):
                raise _SmokeFailure("SYNTHETIC_TARGET_ALREADY_EXISTS")

        phase = "write"
        for target in targets:
            target.attempted = True
            response = client.post(target.collection_path, target.payload)
            item_id = response.get("id") if isinstance(response, dict) else None
            if not isinstance(item_id, str) or not item_id:
                raise _SmokeFailure("WRITE_RESPONSE_INVALID")
            target.item_id = item_id
            write_count += 1

        phase = "readback"
        for target in targets:
            item = _single_matching_item(client.get(target.read_path), target.key_field, target.key_value)
            if _item_id(item) != target.item_id:
                raise _SmokeFailure("READBACK_ITEM_MISMATCH")
            _verify_fields(item, target.payload)
            target.readback_verified = True
            readback_count += 1
    except _SmokeFailure as exc:
        primary_error_code = exc.code
    except Exception:
        primary_error_code = _phase_error_code(phase)
    finally:
        for target in reversed(targets):
            if not target.attempted:
                continue
            cleanup_attempt_count += 1
            try:
                if target.item_id is None:
                    raise _SmokeFailure("CLEANUP_POST_ID_UNBOUND")
                matches = _matching_items(client.get(target.read_path), target.key_field, target.key_value)
                if len(matches) != 1:
                    raise _SmokeFailure("CLEANUP_TARGET_CARDINALITY_INVALID")
                if _item_id(matches[0]) != target.item_id:
                    raise _SmokeFailure("CLEANUP_POST_ID_MISMATCH")
                client.delete(_delete_path(target.collection_path, target.item_id))
                cleanup_delete_count += 1
                if _matching_items(client.get(target.read_path), target.key_field, target.key_value):
                    raise _SmokeFailure("CLEANUP_READBACK_NOT_EMPTY")
                cleanup_absent_count += 1
            except Exception:
                cleanup_error_code = "CLEANUP_FAILED"

    passed = (
        primary_error_code is None
        and cleanup_error_code is None
        and write_count == 3
        and readback_count == 3
        and cleanup_delete_count == 3
        and cleanup_absent_count == 3
    )
    return _redacted_evidence(
        status="PASSED" if passed else "FAILED",
        generated_at=generated_at,
        correlation_id=correlation_id,
        owner_approved=owner_approved,
        workspace_verified=workspace_verified,
        contract_verified=contract_verified,
        binding_evidence=binding_evidence,
        role_checks=role_checks,
        bpmn_evidence=bpmn_evidence,
        write_count=write_count,
        readback_count=readback_count,
        cleanup_attempt_count=cleanup_attempt_count,
        cleanup_delete_count=cleanup_delete_count,
        cleanup_absent_count=cleanup_absent_count,
        primary_error_code=primary_error_code,
        cleanup_error_code=cleanup_error_code,
    )


def run_mvp_test_environment_smoke_from_paths(
    client: GraphSmokeClient,
    decision_function: AccessDecisionFunction,
    *,
    workspace_id: str,
    owner_approved: bool,
    contract_path: Path = DEFAULT_MCP_CONTRACT,
    provisioned_state_path: Path = DEFAULT_PROVISIONED_STATE,
    fixture_path: Path = DEFAULT_MVP_TEST_ENVIRONMENT_FIXTURE,
    correlation_id: str = "mvp-test-environment-smoke",
) -> dict[str, Any]:
    return run_mvp_test_environment_smoke(
        client,
        load_mcp_contract(contract_path),
        load_provisioned_state(provisioned_state_path),
        decision_function,
        workspace_id=workspace_id,
        owner_approved=owner_approved,
        correlation_id=correlation_id,
        fixture_path=fixture_path,
    )


def _require_workspace(workspace_id: str) -> None:
    if workspace_id != EXPECTED_WORKSPACE_ID:
        raise _SmokeFailure("WORKSPACE_SCOPE_REJECTED")


def _validate_contract_boundary(contract: dict[str, Any]) -> None:
    graph = contract.get("graph")
    if (
        contract.get("server_id") != "teams-sharepoint-data-mcp"
        or not isinstance(graph, dict)
        or graph.get("base_url") != "https://graph.microsoft.com/v1.0"
        or graph.get("rest_only") is not True
    ):
        raise _SmokeFailure("MCP_CONTRACT_BOUNDARY_INVALID")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _tasks_match_exactly(value: Any) -> bool:
    expected_tasks = [dict(task) for task in TASKS]
    if not isinstance(value, list) or len(value) != len(expected_tasks):
        return False
    for actual, expected in zip(value, expected_tasks, strict=True):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            return False
        if any(
            type(actual[key]) is not type(expected_value)
            or actual[key] != expected_value
            for key, expected_value in expected.items()
        ):
            return False
    return True


def _load_and_verify_bpmn_fixture(path: Path) -> dict[str, Any]:
    try:
        fixture = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, ValueError) as exc:
        raise _SmokeFailure("BPMN_FIXTURE_INVALID") from exc

    package = fixture.get("package")
    workspace = fixture.get("workspace")
    model = fixture.get("model")
    knowledge_graph = fixture.get("knowledge_graph")
    if (
        set(fixture) != {
            "schema_version",
            "fixture_id",
            "package",
            "workspace",
            "model",
            "knowledge_graph",
        }
        or fixture.get("schema_version") != "nac.m365-mvp-test-environment-bpmn-fixture/v0.2"
        or fixture.get("fixture_id") != "NAC-SYN-MATTER-001-BPMN"
        or package != {
            "name": EXPECTED_BPMN_PACKAGE,
            "version": "0.2.0",
            "binding": "canonical_repo_asset",
        }
        or not isinstance(workspace, dict)
        or set(workspace) != {"workspace_id", "matter", "tasks"}
        or workspace.get("workspace_id") != EXPECTED_WORKSPACE_ID
        or not isinstance(workspace.get("matter"), dict)
        or set(workspace["matter"]) != {
            "matter_id",
            "business_case_type_id",
            "status",
            "deadline",
            "workflow_version",
            "kg_version",
        }
        or workspace.get("matter") != {
            "matter_id": MATTER_ID,
            "business_case_type_id": BUSINESS_CASE_TYPE_ID,
            "status": MATTER_STATUS,
            "deadline": DEADLINE,
            "workflow_version": WORKFLOW_VERSION,
            "kg_version": KG_SCHEMA_VERSION,
        }
        or not _tasks_match_exactly(workspace.get("tasks"))
        or not isinstance(model, dict)
        or set(model) != {
            "model_id",
            "title",
            "notation",
            "version",
            "process_key",
            "source_path",
            "content_sha256",
        }
        or model.get("model_id") != BUSINESS_CASE_TYPE_ID
        or model.get("title") != "Immobilienkaufvertrag"
        or model.get("notation") != "BPMN 2.0"
        or model.get("version") != BPMN_PROFILE_VERSION
        or model.get("process_key") != BPMN_PROCESS_KEY
        or model.get("source_path") != BPMN_SOURCE_PATH
        or model.get("content_sha256") != BPMN_SHA256
        or not isinstance(knowledge_graph, dict)
        or knowledge_graph != {
            "graph_id": KG_GRAPH_ID,
            "schema_version": KG_SCHEMA_VERSION,
            "source_path": KG_SOURCE_PATH,
            "content_sha256": KG_SHA256,
        }
    ):
        raise _SmokeFailure("BPMN_FIXTURE_INVALID")

    try:
        asset = CanonicalBpmnAssetFilePort(REPO_ROOT / BPMN_SOURCE_PATH).read_canonical_bpmn()
    except BpmnAssetError as exc:
        raise _SmokeFailure("BPMN_SOURCE_BINDING_MISMATCH") from exc
    if asset.model_key != BPMN_PROCESS_KEY or asset.sha256 != BPMN_SHA256:
        raise _SmokeFailure("BPMN_MODEL_METADATA_MISMATCH")

    try:
        root = ET.fromstring(asset.xml)
    except ET.ParseError as exc:
        raise _SmokeFailure("BPMN_FIXTURE_INVALID") from exc
    namespace = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
    processes = root.findall(f"{namespace}process")
    if len(processes) != 1 or processes[0].get("id") != BPMN_PROCESS_KEY:
        raise _SmokeFailure("BPMN_MODEL_METADATA_MISMATCH")
    allowed_task_tags = {
        f"{namespace}businessRuleTask",
        f"{namespace}manualTask",
        f"{namespace}receiveTask",
        f"{namespace}scriptTask",
        f"{namespace}sendTask",
        f"{namespace}serviceTask",
        f"{namespace}task",
        f"{namespace}userTask",
    }
    nac_namespace = "{https://github.com/notariat8/NaC/bpmn/nac}"
    if processes[0].get(f"{nac_namespace}profile") != BPMN_PROFILE_VERSION:
        raise _SmokeFailure("BPMN_MODEL_METADATA_MISMATCH")
    for task in TASKS:
        matches = [
            element
            for element in processes[0].iter()
            if element.get("id") == task["step_code"]
        ]
        if (
            len(matches) != 1
            or matches[0].tag not in allowed_task_tags
            or matches[0].get(f"{nac_namespace}kgRef") != BUSINESS_CASE_TYPE_ID
        ):
            raise _SmokeFailure("BPMN_TASK_BINDING_MISMATCH")

    try:
        kg_content = (REPO_ROOT / KG_SOURCE_PATH).read_bytes()
        kg_payload = json.loads(
            kg_content.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise _SmokeFailure("KG_SOURCE_BINDING_MISMATCH") from exc
    if (
        hashlib.sha256(kg_content).hexdigest() != KG_SHA256
        or kg_payload.get("schema_version") != KG_SCHEMA_VERSION
        or kg_payload.get("graph_id") != KG_GRAPH_ID
    ):
        raise _SmokeFailure("KG_SOURCE_BINDING_MISMATCH")

    return {
        "verified": True,
        "packageBound": True,
        "packageName": package["name"],
        "packageVersion": package["version"],
        "notation": model["notation"],
        "modelVersion": model["version"],
        "modelTitle": model["title"],
        "modelRefSha256": _sha256(model["model_id"]),
        "processRefSha256": _sha256(model["process_key"]),
        "contentSha256": asset.sha256,
        "knowledgeGraphSha256": KG_SHA256,
        "businessCaseTypeRefSha256": _sha256(BUSINESS_CASE_TYPE_ID),
        "taskBindingCount": len(TASKS),
        "xmlParsed": True,
        "embeddedModelStored": False,
    }


def _verify_access_decisions(decision_function: AccessDecisionFunction) -> list[dict[str, Any]]:
    expectations = (("assigned", "ALLOW"), ("deputy", "ALLOW"), ("deny", "DENY"))
    checks = []
    for scenario, expected in expectations:
        raw = decision_function(
            {
                "scenario": scenario,
                "actor_id": f"nac-synthetic-{scenario}",
                "workspace_id": EXPECTED_WORKSPACE_ID,
                "case_id": SYNTHETIC_CASE_ID,
                "purpose": "m365_mvp_test_environment_smoke",
            }
        )
        decision = raw.get("decision") if isinstance(raw, Mapping) else raw
        canonical = "DENY" if str(decision).upper() == "BLOCK" else str(decision).upper()
        passed = canonical == expected
        checks.append({"scenario": scenario, "expected": expected, "actual": canonical, "passed": passed})
        if not passed:
            raise _SmokeFailure("ACCESS_DECISION_FAILED")
    return checks


def _case_arguments() -> dict[str, Any]:
    return {
        "case_id": SYNTHETIC_CASE_ID,
        "aktenzeichen": "SYN-MAT-001",
        "vorgangstyp": BUSINESS_CASE_TYPE_ID,
        "status": "Entwurf",
        "notar_team": "NaC-Notar-01",
        "vertraulichkeitsstufe": "Normal",
        "nac_workflow_version": WORKFLOW_VERSION,
        "kg_version": KG_SCHEMA_VERSION,
    }


def _task_arguments() -> list[dict[str, Any]]:
    return [
        {
            "task_id": task["task_id"],
            "case_id": SYNTHETIC_CASE_ID,
            "bpmn_step_code": task["step_code"],
            "status": task["status"],
            "requires_notary_approval": task["requires_notary_approval"],
            **({"due_date": task["due_at"]} if task["due_at"] else {}),
        }
        for task in TASKS
    ]


def _assert_write_plan(
    plan: Any,
    tool: str,
    list_name: str,
    *,
    expected_fields: Mapping[str, Any] | None = None,
) -> None:
    payload_fields = plan.payload.get("fields") if isinstance(plan.payload, dict) else None
    if (
        plan.tool != tool
        or plan.method != "POST"
        or plan.list_name != list_name
        or plan.payload is None
        or not isinstance(payload_fields, dict)
        or any(payload_fields.get(key) != value for key, value in (expected_fields or {}).items())
        or plan.writes_items is not True
        or plan.owner_gate_required is not True
        or plan.graph_rest_only is not True
        or not plan.path.startswith("/sites/")
        or "_api" in plan.path
        or "/beta" in plan.path
    ):
        raise _SmokeFailure("GRAPH_WRITE_PLAN_INVALID")


def _targeted_read_path(collection_path: str, field: str, value: str) -> str:
    encoded_value = urllib.parse.quote(value.replace("'", "''"), safe="")
    return f"{collection_path}?$expand=fields&$filter=fields/{field}%20eq%20%27{encoded_value}%27"


def _matching_items(response: dict[str, Any], field: str, value: str) -> list[dict[str, Any]]:
    values = response.get("value") if isinstance(response, dict) else None
    if not isinstance(values, list):
        raise _SmokeFailure("GRAPH_RESPONSE_SHAPE_INVALID")
    return [
        item
        for item in values
        if isinstance(item, dict)
        and isinstance(item.get("fields"), dict)
        and item["fields"].get(field) == value
    ]


def _single_matching_item(response: dict[str, Any], field: str, value: str) -> dict[str, Any]:
    matches = _matching_items(response, field, value)
    if len(matches) != 1:
        raise _SmokeFailure("READBACK_CARDINALITY_INVALID")
    return matches[0]


def _verify_fields(item: dict[str, Any], payload: dict[str, Any]) -> None:
    expected = payload.get("fields")
    actual = item.get("fields")
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        raise _SmokeFailure("READBACK_FIELDS_INVALID")
    if any(actual.get(key) != value for key, value in expected.items()):
        raise _SmokeFailure("READBACK_FIELDS_MISMATCH")


def _item_id(item: dict[str, Any]) -> str:
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id:
        raise _SmokeFailure("GRAPH_ITEM_ID_MISSING")
    return item_id


def _delete_path(collection_path: str, item_id: str) -> str:
    if "?" in collection_path or not collection_path.endswith("/items"):
        raise _SmokeFailure("CLEANUP_PATH_INVALID")
    return f"{collection_path}/{urllib.parse.quote(item_id, safe='')}"


def _phase_error_code(phase: str) -> str:
    return {
        "scope": "WORKSPACE_SCOPE_REJECTED",
        "contract": "MCP_CONTRACT_BOUNDARY_INVALID",
        "binding": "INPUT_BINDING_INVALID",
        "fixture": "BPMN_FIXTURE_INVALID",
        "decision": "ACCESS_DECISION_FAILED",
        "planning": "PLAN_FAILED",
        "preflight": "PREFLIGHT_FAILED",
        "write": "WRITE_FAILED",
        "readback": "READBACK_FAILED",
    }.get(phase, "SMOKE_FAILED")


def _redacted_evidence(
    *,
    status: str,
    generated_at: str,
    correlation_id: str,
    owner_approved: bool,
    workspace_verified: bool,
    contract_verified: bool,
    binding_evidence: dict[str, str],
    role_checks: list[dict[str, Any]],
    bpmn_evidence: dict[str, Any],
    write_count: int,
    readback_count: int,
    cleanup_attempt_count: int,
    cleanup_delete_count: int,
    cleanup_absent_count: int,
    primary_error_code: str | None,
    cleanup_error_code: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": "nac.m365-mvp-test-environment-smoke-evidence/v0.1",
        "status": status,
        "generated_at": generated_at,
        "summary": {
            "workspaceScopeVerified": workspace_verified,
            "workspaceRefSha256": _sha256(EXPECTED_WORKSPACE_ID),
            "syntheticMatterRefSha256": _sha256(SYNTHETIC_CASE_ID),
            "correlationRefSha256": _sha256(correlation_id),
            "matterWriteCount": min(write_count, 1),
            "taskDeadlineWriteCount": max(write_count - 1, 0),
            "targetedReadbackCount": readback_count,
            "roleDecisionCheckCount": len(role_checks),
            "graphRestV1Only": contract_verified,
            "canonicalInputBindingVerified": bool(binding_evidence),
        },
        "inputBinding": {
            "contractSha256": binding_evidence.get("contractSha256"),
            "provisionedStateSha256": binding_evidence.get("provisionedStateSha256"),
            "workspaceBindingSha256": binding_evidence.get("workspaceBindingSha256"),
        },
        "ownerGate": {"required": True, "approved": owner_approved is True},
        "roleChecks": role_checks,
        "bpmnFixture": bpmn_evidence,
        "cleanup": {
            "finallyExecuted": True,
            "strategy": "created_items_only",
            "attemptCount": cleanup_attempt_count,
            "deleteCount": cleanup_delete_count,
            "verifiedAbsentCount": cleanup_absent_count,
            "automaticGlobalLeftoverDelete": False,
        },
        "error": {
            "code": primary_error_code,
            "cleanupCode": cleanup_error_code,
            "rawMessageStored": False,
        },
        "privacy": {
            "storesRawIds": False,
            "storesRawGraphPaths": False,
            "storesRawPayloads": False,
            "storesRawGraphResponses": False,
            "storesTokensOrSecrets": False,
            "usesRealMatterData": False,
            "readsSharePointFileContent": False,
        },
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
