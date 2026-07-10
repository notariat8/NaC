from __future__ import annotations

import hashlib
import json
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from nac_m365_graph.graph_client import GraphHttpError

from .process_ontology_schema_apply_binding import (
    SCHEMA_VERSION as APPLY_BINDING_SCHEMA_VERSION,
    SELECTED_STEP_PROJECTION_FIELDS,
    build_process_ontology_sharepoint_schema_apply_binding,
)

from .process_ontology_schema_apply_live_runner import (
    build_process_ontology_sharepoint_schema_apply_live_runner,
)
from .process_ontology_schema_apply_plan import (
    CHOICE_COLUMN_ODATA_TYPE,
    build_process_ontology_sharepoint_schema_apply_plan,
)
from .process_ontology_schema_apply_readiness import build_process_ontology_sharepoint_schema_apply_readiness


LEGACY_SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-graph-dispatcher/v0.1"
SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-graph-dispatcher/v0.2"
SUPPORTED_SCHEMA_VERSIONS = {LEGACY_SCHEMA_VERSION, SCHEMA_VERSION}
CONTRACT_ID = "notarial.process_ontology_sharepoint_schema_apply_graph_dispatcher"
DEFAULT_GRAPH_DISPATCHER_JSON = Path("out/notary-kg/process-ontology-schema-apply-graph-dispatcher.redacted.json")
DEFAULT_GRAPH_DISPATCHER_MARKDOWN = Path("out/notary-kg/process-ontology-schema-apply-graph-dispatcher.redacted.md")
MUTATION_NOT_ATTEMPTED = "NOT_ATTEMPTED"
MUTATION_SKIPPED = "SKIPPED"
MUTATION_CONFIRMED = "CONFIRMED"
MUTATION_POSSIBLE = "POSSIBLE"
MAX_DIAGNOSTIC_COUNT = 1000
MAX_GRAPH_INNER_ERROR_DEPTH = 8
GRAPH_ERROR_CLASS_BY_CODE = {
    "badArgument": "REQUEST_VALIDATION",
    "invalidRequest": "REQUEST_VALIDATION",
}
GRAPH_ERROR_ENVELOPES = {"STANDARD", "NONSTANDARD", "MALFORMED", "EMPTY", "NOT_AVAILABLE"}
GRAPH_ERROR_CODES = {*GRAPH_ERROR_CLASS_BY_CODE, "UNCLASSIFIED"}
GRAPH_ERROR_CLASSES = {*GRAPH_ERROR_CLASS_BY_CODE.values(), "UNCLASSIFIED"}
RETRY_DISPOSITIONS = {"DO_NOT_RETRY_UNCHANGED", "RETRY_WITH_BACKOFF", "REVIEW_REQUIRED"}
STEP_ERROR_PHASES_BY_CODE = {
    "choice_column_resolution_failed": {"resolution"},
    "choice_readback_verification_failed": {"readback"},
    "dispatcher_validation_failed": {"validation"},
    "graph_http_error": {"resolution", "preflight", "mutation", "readback", "unknown"},
    "graph_request_failed": {"resolution", "preflight", "mutation", "readback", "unknown"},
    "readback_verification_failed": {"readback"},
}
GRAPH_REQUEST_ERROR_CODES = {"graph_http_error", "graph_request_failed"}
METHOD_BY_OPERATION = {
    "create_list": "POST",
    "create_document_library": "POST",
    "create_column": "POST",
    "extend_choice_column": "PATCH",
}
DIAGNOSTIC_TOP_LEVEL_FIELDS = {
    "contract",
    "graphError",
    "retryDisposition",
    "endpoint",
    "facet",
    "expectedHttpStatus",
    "columnShape",
    "requestShape",
    "counts",
}
GRAPH_ERROR_DIAGNOSTIC_FIELDS = {
    "envelope",
    "code",
    "class",
    "messagePresent",
    "innerErrorPresent",
    "detailsPresent",
}
COLUMN_SHAPE_FIELDS = {
    "choiceFacetPresent",
    "choiceFacetIsObject",
    "choicesPresent",
    "choicesIsArray",
    "readOnlyPresent",
    "readOnlyIsBoolean",
    "readOnlyTrue",
    "sealedPresent",
    "sealedIsBoolean",
    "sealedTrue",
    "indexedPresent",
    "indexedIsBoolean",
    "indexedTrue",
}
REQUEST_SHAPE_FIELDS = {
    "bodyIsObject",
    "choiceFacetPresent",
    "choiceFacetIsObject",
    "odataTypePresent",
    "odataTypeAllowlisted",
    "choicesPresent",
    "choicesIsArray",
    "allowTextEntryPresent",
    "allowTextEntryIsBoolean",
    "displayAsPresent",
    "displayAsRecognized",
}
DIAGNOSTIC_COUNT_FIELDS = {
    "currentChoiceCount",
    "requiredChoiceCount",
    "mergedChoiceCount",
    "requestChoiceCount",
    "requestBodyFieldCount",
    "choiceFacetFieldCount",
    "countsCapped",
}


class ProcessOntologySchemaApplyGraphClient(Protocol):
    def get(self, path: str) -> dict[str, Any]:
        ...

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaApplyGraphDispatcherValidation:
    status: str
    errors: tuple[str, ...]


class DispatchStepFailure(RuntimeError):
    def __init__(
        self,
        code: str,
        phase: str,
        *,
        mutation_attempted: bool = False,
        mutation_outcome: str = MUTATION_NOT_ATTEMPTED,
        http_status: int | None = None,
        diagnostic: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.phase = phase
        self.mutation_attempted = mutation_attempted
        self.mutation_outcome = mutation_outcome
        self.http_status = http_status
        self.diagnostic = diagnostic


def run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
    client: ProcessOntologySchemaApplyGraphClient,
    repo_root: Path,
    *,
    live_readiness_gate: Path,
    workspace_id: str,
    correlation_id: str,
    owner_approval_reference: str,
    reason: str,
    owner_approved: bool,
    execute_live_schema_apply: bool,
    write_redacted_evidence: bool,
    evidence_json_output: Path,
    evidence_markdown_output: Path,
    max_steps: int | None = None,
) -> dict[str, Any]:
    _validate_dispatch_inputs(
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        owner_approval_reference=owner_approval_reference,
        reason=reason,
        owner_approved=owner_approved,
        execute_live_schema_apply=execute_live_schema_apply,
        write_redacted_evidence=write_redacted_evidence,
        max_steps=max_steps,
    )
    json_path = _resolve_output_path(repo_root, evidence_json_output)
    markdown_path = _resolve_output_path(repo_root, evidence_markdown_output)
    if json_path.resolve() == markdown_path.resolve():
        raise ValueError("JSON and Markdown evidence outputs must be distinct")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    def evidence_checkpoint(payload: dict[str, Any]) -> None:
        payload["artifact_paths"] = {
            "json": _relative_path(repo_root, json_path),
            "markdown": _relative_path(repo_root, markdown_path),
        }
        _atomic_write_text(json_path, json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        _atomic_write_text(markdown_path, _dispatcher_markdown(payload))

    live_runner = build_process_ontology_sharepoint_schema_apply_live_runner(
        repo_root,
        live_readiness_gate=live_readiness_gate,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        owner_approval_reference=owner_approval_reference,
        reason=reason,
        owner_approved=owner_approved,
        execute_live_schema_apply=execute_live_schema_apply,
        write_redacted_evidence=write_redacted_evidence,
        ensure_default_artifacts=False,
    )
    if live_runner["status"] != "READY_FOR_GRAPH_REST_DISPATCH":
        raise ValueError("process ontology schema apply live runner is not ready for Graph REST dispatch")

    readiness = build_process_ontology_sharepoint_schema_apply_readiness(repo_root)
    apply_plan = build_process_ontology_sharepoint_schema_apply_plan(repo_root)
    binding = build_process_ontology_sharepoint_schema_apply_binding(repo_root, [workspace_id])
    plan_by_id = {step["id"]: step for step in apply_plan["steps"]}
    selected = [workspace for workspace in readiness["workspaces"] if workspace["workspace_id"] == workspace_id]
    if len(selected) != 1:
        raise ValueError("process ontology schema apply workspace selection must resolve exactly once")
    workspace = selected[0]
    steps = [(workspace, unit, plan_by_id[unit["source_step_id"]]) for unit in workspace["apply_units"]]
    if max_steps is not None and max_steps >= len(steps):
        raise ValueError("max_steps must be lower than the selected workspace plan; omit it for a full apply")
    dispatch_limit = len(steps) if max_steps is None else min(max_steps, len(steps))

    dispatch_steps: list[dict[str, Any]] = []
    payload = _build_dispatch_payload(
        live_runner=live_runner,
        readiness=readiness,
        apply_plan=apply_plan,
        binding=binding,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        owner_approval_reference=owner_approval_reference,
        reason=reason,
        planned_step_count=len(steps),
        dispatch_limit=dispatch_limit,
        dispatch_steps=dispatch_steps,
        status="RUNNING",
        stop_reason="",
    )
    evidence_checkpoint(payload)
    stop_reason = ""
    for sequence, (workspace, unit, plan_step) in enumerate(steps[:dispatch_limit], start=1):
        dispatch_steps.append(_pending_step(workspace, unit, plan_step, sequence))
        payload = _build_dispatch_payload(
            live_runner=live_runner,
            readiness=readiness,
            apply_plan=apply_plan,
            binding=binding,
            workspace_id=workspace_id,
            correlation_id=correlation_id,
            owner_approval_reference=owner_approval_reference,
            reason=reason,
            planned_step_count=len(steps),
            dispatch_limit=dispatch_limit,
            dispatch_steps=dispatch_steps,
            status="RUNNING",
            stop_reason="",
        )
        evidence_checkpoint(payload)
        try:
            result = _dispatch_step(client, workspace, unit, plan_step, sequence)
        except DispatchStepFailure as exc:
            result = _failed_step(workspace, unit, plan_step, sequence, exc)
            stop_reason = exc.code
        except Exception as exc:  # defensive: never persist exception text
            safe = _safe_failure(exc, "unknown")
            result = _failed_step(workspace, unit, plan_step, sequence, safe)
            stop_reason = safe.code
        dispatch_steps[-1] = result
        payload = _build_dispatch_payload(
            live_runner=live_runner,
            readiness=readiness,
            apply_plan=apply_plan,
            binding=binding,
            workspace_id=workspace_id,
            correlation_id=correlation_id,
            owner_approval_reference=owner_approval_reference,
            reason=reason,
            planned_step_count=len(steps),
            dispatch_limit=dispatch_limit,
            dispatch_steps=dispatch_steps,
            status="FAILED" if result["status"] == "FAILED" else "RUNNING",
            stop_reason=stop_reason,
        )
        evidence_checkpoint(payload)
        if result["status"] == "FAILED":
            break

    final_status = (
        "FAILED"
        if any(step["status"] == "FAILED" for step in dispatch_steps)
        else "PARTIAL"
        if len(dispatch_steps) < len(steps)
        else "PASSED"
    )
    payload = _build_dispatch_payload(
        live_runner=live_runner,
        readiness=readiness,
        apply_plan=apply_plan,
        binding=binding,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        owner_approval_reference=owner_approval_reference,
        reason=reason,
        planned_step_count=len(steps),
        dispatch_limit=dispatch_limit,
        dispatch_steps=dispatch_steps,
        status=final_status,
        stop_reason=stop_reason,
    )
    validation = validate_process_ontology_sharepoint_schema_apply_graph_dispatcher(payload)
    if validation.errors:
        payload = _validation_failure_payload(payload)
        revalidation = validate_process_ontology_sharepoint_schema_apply_graph_dispatcher(payload)
        if revalidation.errors:
            raise RuntimeError("dispatcher validation-failure evidence invariant failed")
    evidence_checkpoint(payload)
    return payload


def _validate_dispatch_inputs(
    *,
    workspace_id: str,
    correlation_id: str,
    owner_approval_reference: str,
    reason: str,
    owner_approved: bool,
    execute_live_schema_apply: bool,
    write_redacted_evidence: bool,
    max_steps: int | None,
) -> None:
    if not owner_approved:
        raise ValueError("process ontology schema apply Graph dispatcher requires owner_approved")
    if not execute_live_schema_apply:
        raise ValueError("process ontology schema apply Graph dispatcher requires execute_live_schema_apply")
    if not write_redacted_evidence:
        raise ValueError("process ontology schema apply Graph dispatcher requires write_redacted_evidence")
    for name, value in (
        ("workspace_id", workspace_id),
        ("correlation_id", correlation_id),
        ("owner_approval_reference", owner_approval_reference),
        ("reason", reason),
    ):
        if not str(value).strip():
            raise ValueError(f"process ontology schema apply Graph dispatcher requires {name}")
    if max_steps is not None and max_steps < 1:
        raise ValueError("max_steps must be positive")


def _build_dispatch_payload(
    *,
    live_runner: dict[str, Any],
    readiness: dict[str, Any],
    apply_plan: dict[str, Any],
    binding: dict[str, Any],
    workspace_id: str,
    correlation_id: str,
    owner_approval_reference: str,
    reason: str,
    planned_step_count: int,
    dispatch_limit: int,
    dispatch_steps: list[dict[str, Any]],
    status: str,
    stop_reason: str,
) -> dict[str, Any]:
    failed_steps = [step for step in dispatch_steps if step["status"] == "FAILED"]
    confirmed = sum(step["mutationOutcome"] == MUTATION_CONFIRMED for step in dispatch_steps)
    possible = sum(step["mutationOutcome"] == MUTATION_POSSIBLE for step in dispatch_steps)
    skipped = sum(step["mutationOutcome"] == MUTATION_SKIPPED for step in dispatch_steps)
    attempted = sum(bool(step["mutationAttempted"]) for step in dispatch_steps)
    completion = (
        "FAILED"
        if status == "FAILED"
        else "PARTIAL"
        if status in {"RUNNING", "PARTIAL"}
        else "APPLIED"
        if confirmed
        else "NO_CHANGES"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": status,
        "completion": completion,
        "mode": "owner_gated_graph_rest_dispatcher",
        "source": {
            "live_runner_schema": live_runner["schema_version"],
            "live_runner_status": live_runner["status"],
            "apply_readiness_schema": readiness["schema_version"],
            "apply_readiness_status": readiness["status"],
            "apply_plan_schema": apply_plan["schema_version"],
            "apply_plan_status": apply_plan["status"],
            "graph_base_url": readiness["source"]["graph_base_url"],
            "graph_rest_only": True,
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
        },
        "approval_binding": binding,
        "summary": {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "owner_approval_reference_sha256": _sha256(owner_approval_reference),
            "reason_sha256": _sha256(reason),
            "planned_step_count": planned_step_count,
            "dispatch_limit": dispatch_limit,
            "dispatched_step_count": len(dispatch_steps),
            "passed_step_count": sum(step["status"] == "PASSED" for step in dispatch_steps),
            "failed_step_count": len(failed_steps),
            "mutation_request_count": attempted,
            "confirmed_mutation_count": confirmed,
            "possible_mutation_count": possible,
            "skipped_mutation_count": skipped,
            "executed_graph_requests": bool(dispatch_steps),
            "executed_graph_writes": attempted > 0,
            "writes_sharepoint": confirmed > 0,
            "writes_may_have_occurred": confirmed + possible > 0,
            "changes_sharepoint_schema": confirmed > 0,
            "stopped_on_first_failure": bool(failed_steps),
            "stop_reason": stop_reason,
        },
        "dispatch_steps": list(dispatch_steps),
        "privacy": {
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "storesRawMutationPayload": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "readsSharePointFileContent": False,
        },
        "guardrails": {
            "owner_gated": True,
            "graph_rest_only": True,
            "executes_graph_requests": bool(dispatch_steps),
            "executes_graph_writes": attempted > 0,
            "writes_sharepoint": confirmed > 0,
            "writes_may_have_occurred": confirmed + possible > 0,
            "changes_sharepoint_schema": confirmed > 0,
            "stores_tokens_or_secrets": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "raw_mutation_payload_stored": False,
        },
        "errors": [step["error"] for step in failed_steps if step.get("error")],
    }


def validate_process_ontology_sharepoint_schema_apply_graph_dispatcher(
    payload: dict[str, Any],
) -> ProcessOntologySchemaApplyGraphDispatcherValidation:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append("unexpected graph dispatcher schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected graph dispatcher contract_id")
    if payload.get("mode") != "owner_gated_graph_rest_dispatcher":
        errors.append("graph dispatcher must be owner-gated")
    source = payload.get("source", {})
    if source.get("graph_base_url") != "https://graph.microsoft.com/v1.0":
        errors.append("graph dispatcher must use Microsoft Graph v1.0")
    if source.get("graph_rest_only") is not True:
        errors.append("graph dispatcher must remain Graph REST only")
    if source.get("legacy_sharepoint_api_allowed") is not False:
        errors.append("legacy SharePoint API must remain blocked")
    if source.get("graph_sdk_allowed") is not False:
        errors.append("Graph SDK must remain blocked")

    summary = payload.get("summary", {})
    status = payload.get("status")
    dispatched = summary.get("dispatched_step_count", 0)
    planned = summary.get("planned_step_count", 0)
    if dispatched < 1:
        errors.append("graph dispatcher must dispatch at least one step")
    if status == "PASSED":
        if summary.get("failed_step_count") != 0 or summary.get("passed_step_count") != dispatched:
            errors.append("passed graph dispatcher must pass all dispatched steps")
        if dispatched != planned:
            errors.append("passed graph dispatcher must complete all selected workspace steps")
    elif status == "PARTIAL":
        if not 0 < dispatched < planned or summary.get("failed_step_count") != 0:
            errors.append("partial graph dispatcher must be a failure-free strict prefix")
    elif status == "FAILED":
        if summary.get("failed_step_count", 0) < 1:
            errors.append("failed graph dispatcher must expose a failed step")
    else:
        errors.append("graph dispatcher final status must be PASSED, PARTIAL or FAILED")
    if summary.get("executed_graph_requests") is not True:
        errors.append("graph dispatcher must execute Graph requests")
    approval_binding = payload.get("approval_binding")
    if type(approval_binding) is not dict:
        errors.append("graph dispatcher approval binding must be an object")
        approval_binding = {}
    workspace_ids = approval_binding.get("workspace_ids", [])
    if len(workspace_ids) != 1 or summary.get("workspace_id") != workspace_ids[0]:
        errors.append("graph dispatcher workspace must match approval binding")
    if approval_binding.get("selected_apply_unit_count") != planned:
        errors.append("planned step count must match approval binding")
    if not summary.get("owner_approval_reference_sha256") or not summary.get("reason_sha256"):
        errors.append("graph dispatcher must retain redacted approval and reason hashes")

    dispatch_steps = payload.get("dispatch_steps")
    if type(dispatch_steps) is not list:
        errors.append("dispatch_steps must be a list")
        dispatch_steps = []
    allowed_outcomes = {
        MUTATION_NOT_ATTEMPTED,
        MUTATION_SKIPPED,
        MUTATION_CONFIRMED,
        MUTATION_POSSIBLE,
    }
    failed_errors: list[Any] = []
    for index, step in enumerate(dispatch_steps):
        if type(step) is not dict:
            errors.append(f"dispatch step {index}: step must be an object")
            continue
        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id:
            errors.append(f"dispatch step {index}: step id must be a non-empty string")
            step_id = f"<step-{index}>"
        if step.get("ownerGateRequired") is not True:
            errors.append(f"{step_id}: owner gate must be required")
        if step.get("graphRestOnly") is not True:
            errors.append(f"{step_id}: step must be Graph REST only")
        operation = step.get("operation")
        method = step.get("method")
        expected_method = METHOD_BY_OPERATION.get(operation)
        if expected_method is None:
            errors.append(f"{step_id}: invalid closed operation")
        elif method != expected_method:
            errors.append(f"{step_id}: method must match the closed operation contract")
        if step.get("mutationOutcome") not in allowed_outcomes:
            errors.append(f"{step_id}: invalid mutation outcome")
        if step.get("status") not in {"PASSED", "FAILED"}:
            errors.append(f"{step_id}: final step status must be PASSED or FAILED")
        if step.get("status") == "PASSED" and step.get("mutationOutcome") == MUTATION_POSSIBLE:
            errors.append(f"{step_id}: possible mutation cannot be reported as passed")
        for raw_key in ("rawGraphPathStored", "rawGraphResponseStored", "rawMutationPayloadStored"):
            if step.get(raw_key) is not False:
                errors.append(f"{step_id}: {raw_key} must be false")

        if step.get("status") == "FAILED":
            failed_errors.append(step.get("error"))
            errors.extend(_validate_failed_step_error(step_id, step, schema_version))
        elif "error" in step:
            errors.append(f"{step_id}: nonfailed step must not expose error")

    if schema_version == SCHEMA_VERSION:
        errors.extend(
            _validate_v02_approval_binding(
                approval_binding,
                dispatch_steps,
                planned,
            )
        )

    if type(payload.get("errors")) is not list or payload.get("errors") != failed_errors:
        errors.append("top-level errors must exactly mirror failed-step errors")

    privacy = payload.get("privacy", {})
    for key in (
        "storesRawGraphPath",
        "storesRawGraphResponse",
        "storesRawMutationPayload",
        "storesTokensOrSecrets",
        "storesMatterData",
        "readsSharePointFileContent",
    ):
        if privacy.get(key) is not False:
            errors.append(f"privacy must keep {key} false")

    guardrails = payload.get("guardrails", {})
    for key in ("owner_gated", "graph_rest_only", "executes_graph_requests"):
        if guardrails.get(key) is not True:
            errors.append(f"guardrail must be true: {key}")
    for key in (
        "stores_tokens_or_secrets",
        "stores_matter_instance_values",
        "stores_document_full_text",
        "legacy_sharepoint_api_allowed",
        "graph_sdk_allowed",
        "raw_graph_path_stored",
        "raw_graph_response_stored",
        "raw_mutation_payload_stored",
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")
    return ProcessOntologySchemaApplyGraphDispatcherValidation(
        status="PASSED" if not errors else "FAILED",
        errors=tuple(errors),
    )


def _validate_v02_approval_binding(
    binding: dict[str, Any],
    dispatch_steps: list[dict[str, Any]],
    planned_step_count: Any,
) -> list[str]:
    errors: list[str] = []
    expected_binding_fields = {
        "schema_version",
        "workspace_ids",
        "workspace_bindings",
        "apply_plan_sha256",
        "workspace_readiness_sha256",
        "selected_apply_unit_count",
        "selected_step_projection",
        "selected_step_projection_sha256",
        "binding_sha256",
    }
    if set(binding) != expected_binding_fields:
        errors.append("v0.2 approval binding fields must match the closed contract")
    if binding.get("schema_version") != APPLY_BINDING_SCHEMA_VERSION:
        errors.append("v0.2 dispatcher must use the current apply binding schema")

    projection = binding.get("selected_step_projection")
    if type(projection) is not list:
        errors.append("selected-step projection must be a list")
        projection = []
    if binding.get("selected_apply_unit_count") != len(projection):
        errors.append("selected apply unit count must match selected-step projection")
    if planned_step_count != len(projection):
        errors.append("planned step count must match selected-step projection")

    for index, entry in enumerate(projection, start=1):
        if type(entry) is not dict or set(entry) != SELECTED_STEP_PROJECTION_FIELDS:
            errors.append(f"selected-step projection {index}: fields must match the closed contract")
            continue
        if entry.get("sequence") != index:
            errors.append(f"selected-step projection {index}: sequence must match position")
        for key in ("apply_unit_id", "source_step_id"):
            if not isinstance(entry.get(key), str) or not entry[key]:
                errors.append(f"selected-step projection {index}: {key} must be a non-empty string")
        operation = entry.get("operation")
        expected_method = METHOD_BY_OPERATION.get(operation)
        if expected_method is None:
            errors.append(f"selected-step projection {index}: invalid closed operation")
        elif entry.get("method") != expected_method:
            errors.append(
                f"selected-step projection {index}: method must match the closed operation contract"
            )

    projection_hash = binding.get("selected_step_projection_sha256")
    if projection_hash != _payload_sha256({"steps": projection}):
        errors.append("selected-step projection hash must match its redacted content")
    binding_source = {
        key: value
        for key, value in binding.items()
        if key not in {"schema_version", "binding_sha256"}
    }
    if binding.get("binding_sha256") != _payload_sha256(binding_source):
        errors.append("approval binding hash must include the selected-step projection")

    for index, step in enumerate(dispatch_steps):
        if index >= len(projection):
            errors.append(f"{step.get('id', f'<step-{index}>')}: no approved projection entry")
            continue
        approved = projection[index]
        actual = {
            "sequence": step.get("sequence"),
            "apply_unit_id": step.get("id"),
            "source_step_id": step.get("sourceStepId"),
            "operation": step.get("operation"),
            "method": step.get("method"),
        }
        if actual != approved:
            errors.append(
                f"{step.get('id', f'<step-{index}>')}: dispatch step must match the approved "
                "selected-step projection"
            )
    return errors


def _validate_failed_step_error(
    step_id: str,
    step: dict[str, Any],
    schema_version: Any,
) -> list[str]:
    error = step.get("error")
    if type(error) is not dict:
        return [f"{step_id}: failed step error must be an exact object"]
    code = error.get("code")
    phase = error.get("phase")
    expected_fields = {"stepId", "code", "phase"}
    if code == "graph_http_error":
        expected_fields.add("httpStatus")
    choice_patch_failure = phase == "mutation" and code in GRAPH_REQUEST_ERROR_CODES and (
        step.get("operation") == "extend_choice_column" or step.get("method") == "PATCH"
    )
    diagnostic = error.get("diagnostic")
    diagnostic_required = choice_patch_failure and schema_version == SCHEMA_VERSION
    diagnostic_present = "diagnostic" in error
    if diagnostic_required or diagnostic_present:
        expected_fields.add("diagnostic")

    errors: list[str] = []
    if set(error) != expected_fields:
        errors.append(f"{step_id}: error fields must match the closed code contract")
    if error.get("stepId") != step_id:
        errors.append(f"{step_id}: error stepId must exactly match step id")
    allowed_phases = STEP_ERROR_PHASES_BY_CODE.get(code)
    if allowed_phases is None:
        errors.append(f"{step_id}: invalid closed error code")
    elif phase not in allowed_phases:
        errors.append(f"{step_id}: invalid phase for error code")
    http_status = error.get("httpStatus")
    if code == "graph_http_error" and (
        isinstance(http_status, bool)
        or not isinstance(http_status, int)
        or not 100 <= http_status <= 599
    ):
        errors.append(f"{step_id}: HTTP status must be an integer from 100 through 599")
    if diagnostic_required or diagnostic_present:
        if type(diagnostic) is not dict:
            errors.append(f"{step_id}: failed Choice PATCH must expose closed diagnostics")
        elif choice_patch_failure:
            errors.extend(_validate_choice_patch_failure_diagnostic(step_id, diagnostic, http_status))
        else:
            errors.append(f"{step_id}: diagnostics are only allowed for Choice PATCH failures")
    return errors


def _validate_choice_patch_failure_diagnostic(
    step_id: str,
    diagnostic: dict[str, Any],
    http_status: Any,
) -> list[str]:
    errors: list[str] = []
    if set(diagnostic) != DIAGNOSTIC_TOP_LEVEL_FIELDS:
        return [f"{step_id}: Choice PATCH diagnostic fields must match the closed contract"]
    if diagnostic.get("contract") != "choice_patch_failure/v1":
        errors.append(f"{step_id}: unexpected Choice PATCH diagnostic contract")
    if diagnostic.get("endpoint") != "COLUMN_DEFINITION_UPDATE":
        errors.append(f"{step_id}: unexpected Choice PATCH diagnostic endpoint")
    if diagnostic.get("facet") != "CHOICE":
        errors.append(f"{step_id}: unexpected Choice PATCH diagnostic facet")
    if diagnostic.get("expectedHttpStatus") != 200:
        errors.append(f"{step_id}: Choice PATCH expected HTTP status must be 200")
    if diagnostic.get("retryDisposition") not in RETRY_DISPOSITIONS:
        errors.append(f"{step_id}: invalid Choice PATCH retry disposition")

    graph_error = diagnostic.get("graphError")
    if type(graph_error) is not dict or set(graph_error) != GRAPH_ERROR_DIAGNOSTIC_FIELDS:
        errors.append(f"{step_id}: Graph error diagnostic fields must match the closed contract")
    else:
        envelope = graph_error.get("envelope")
        code = graph_error.get("code")
        error_class = graph_error.get("class")
        if envelope not in GRAPH_ERROR_ENVELOPES:
            errors.append(f"{step_id}: invalid Graph error envelope")
        if code not in GRAPH_ERROR_CODES:
            errors.append(f"{step_id}: invalid Graph error code")
        if error_class not in GRAPH_ERROR_CLASSES:
            errors.append(f"{step_id}: invalid Graph error class")
        expected_class = GRAPH_ERROR_CLASS_BY_CODE.get(code, "UNCLASSIFIED")
        if error_class != expected_class:
            errors.append(f"{step_id}: Graph error code and class must agree")
        if code != "UNCLASSIFIED" and envelope != "STANDARD":
            errors.append(f"{step_id}: allowlisted Graph error codes require a standard envelope")
        expected_retry = (
            "DO_NOT_RETRY_UNCHANGED"
            if error_class == "REQUEST_VALIDATION"
            else "RETRY_WITH_BACKOFF"
            if http_status in {429, 500, 502, 503, 504}
            else "REVIEW_REQUIRED"
        )
        if diagnostic.get("retryDisposition") != expected_retry:
            errors.append(f"{step_id}: Graph error class and retry disposition must agree")
        for key in ("messagePresent", "innerErrorPresent", "detailsPresent"):
            if not isinstance(graph_error.get(key), bool):
                errors.append(f"{step_id}: Graph error shape values must be booleans")

    for name, expected_fields in (
        ("columnShape", COLUMN_SHAPE_FIELDS),
        ("requestShape", REQUEST_SHAPE_FIELDS),
    ):
        shape = diagnostic.get(name)
        if type(shape) is not dict or set(shape) != expected_fields:
            errors.append(f"{step_id}: {name} fields must match the closed contract")
        elif any(not isinstance(value, bool) for value in shape.values()):
            errors.append(f"{step_id}: {name} values must be booleans")

    counts = diagnostic.get("counts")
    if type(counts) is not dict or set(counts) != DIAGNOSTIC_COUNT_FIELDS:
        errors.append(f"{step_id}: diagnostic count fields must match the closed contract")
    else:
        if not isinstance(counts.get("countsCapped"), bool):
            errors.append(f"{step_id}: countsCapped must be boolean")
        for key in DIAGNOSTIC_COUNT_FIELDS - {"countsCapped"}:
            value = counts.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= MAX_DIAGNOSTIC_COUNT
            ):
                errors.append(f"{step_id}: {key} must be a bounded non-negative integer")
    return errors


def _validation_failure_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    dispatch_steps = [dict(step) for step in payload.get("dispatch_steps", [])]
    if not dispatch_steps:
        raise RuntimeError("dispatcher validation failure has no dispatched step")
    failed_step = dispatch_steps[-1]
    failed_step["status"] = "FAILED"
    failed_step["error"] = {
        "stepId": failed_step["id"],
        "code": "dispatcher_validation_failed",
        "phase": "validation",
    }
    dispatch_steps[-1] = failed_step
    normalized["dispatch_steps"] = dispatch_steps
    normalized["status"] = "FAILED"
    normalized["completion"] = "FAILED"
    summary = dict(payload["summary"])
    summary["passed_step_count"] = sum(step.get("status") == "PASSED" for step in dispatch_steps)
    summary["failed_step_count"] = 1
    summary["stopped_on_first_failure"] = True
    summary["stop_reason"] = "dispatcher_validation_failed"
    normalized["summary"] = summary
    normalized["errors"] = [failed_step["error"]]
    return normalized


def write_process_ontology_sharepoint_schema_apply_graph_dispatcher_artifact(
    client: ProcessOntologySchemaApplyGraphClient,
    repo_root: Path,
    json_output: Path | None = None,
    markdown_output: Path | None = None,
    *,
    live_readiness_gate: Path,
    workspace_id: str,
    correlation_id: str,
    owner_approval_reference: str,
    reason: str,
    owner_approved: bool,
    execute_live_schema_apply: bool,
    write_redacted_evidence: bool,
    max_steps: int | None = None,
) -> dict[str, Any]:
    json_path = _resolve_output_path(repo_root, json_output or DEFAULT_GRAPH_DISPATCHER_JSON)
    markdown_path = _resolve_output_path(repo_root, markdown_output or DEFAULT_GRAPH_DISPATCHER_MARKDOWN)

    return run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
        client,
        repo_root,
        live_readiness_gate=live_readiness_gate,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        owner_approval_reference=owner_approval_reference,
        reason=reason,
        owner_approved=owner_approved,
        execute_live_schema_apply=execute_live_schema_apply,
        write_redacted_evidence=write_redacted_evidence,
        evidence_json_output=json_path,
        evidence_markdown_output=markdown_path,
        max_steps=max_steps,
    )


def _dispatch_step(
    client: ProcessOntologySchemaApplyGraphClient,
    workspace: dict[str, Any],
    unit: dict[str, Any],
    plan_step: dict[str, Any],
    sequence: int,
) -> dict[str, Any]:
    operation = unit["operation"]
    if operation == "extend_choice_column":
        return _dispatch_extend_choice_step(client, workspace, unit, plan_step, sequence)
    return _dispatch_create_step(client, workspace, unit, plan_step, sequence)


def _dispatch_create_step(
    client: ProcessOntologySchemaApplyGraphClient,
    workspace: dict[str, Any],
    unit: dict[str, Any],
    plan_step: dict[str, Any],
    sequence: int,
) -> dict[str, Any]:
    replacements = _base_replacements(workspace, unit, plan_step)
    preflight_path = _render_path(unit["preflight_idempotency_check"]["path_template"], replacements)
    try:
        preflight = client.get(preflight_path)
    except Exception as exc:
        raise _safe_failure(exc, "preflight") from exc
    exists = _value_count(preflight) > 0
    mutation_path = _render_path(plan_step["request"]["path_template"], replacements)
    mutation_shape: dict[str, Any] = {}
    mutation_outcome = MUTATION_SKIPPED if exists else MUTATION_NOT_ATTEMPTED
    if not exists:
        try:
            body = plan_step["request"]["body"]
            mutation_shape = (
                client.post(mutation_path, body)
                if plan_step["request"]["method"] == "POST"
                else client.patch(mutation_path, body)
            )
            mutation_outcome = MUTATION_CONFIRMED
        except Exception as exc:
            raise _safe_failure(
                exc,
                "mutation",
                mutation_attempted=True,
                mutation_outcome=MUTATION_POSSIBLE,
            ) from exc
    readback_path = preflight_path
    try:
        readback = client.get(readback_path)
    except Exception as exc:
        raise _safe_failure(
            exc,
            "readback",
            mutation_attempted=not exists,
            mutation_outcome=mutation_outcome,
        ) from exc
    readback_count = _value_count(readback)
    if readback_count < 1:
        raise DispatchStepFailure(
            "readback_verification_failed",
            "readback",
            mutation_attempted=not exists,
            mutation_outcome=mutation_outcome,
        )
    return _redacted_dispatch_step(
        workspace=workspace,
        unit=unit,
        plan_step=plan_step,
        sequence=sequence,
        preflight_path=preflight_path,
        mutation_path=mutation_path,
        readback_path=readback_path,
        mutation_outcome=mutation_outcome,
        readback_count=readback_count,
        mutation_shape=mutation_shape,
    )


def _dispatch_extend_choice_step(
    client: ProcessOntologySchemaApplyGraphClient,
    workspace: dict[str, Any],
    unit: dict[str, Any],
    plan_step: dict[str, Any],
    sequence: int,
) -> dict[str, Any]:
    replacements = _base_replacements(workspace, unit, plan_step)
    resolution_path = _render_path(
        "/sites/{site-id}/lists/{list-id}/columns?$filter=name eq '{column-name}'",
        replacements,
    )
    try:
        resolution = client.get(resolution_path)
    except Exception as exc:
        raise _safe_failure(exc, "resolution") from exc
    column_id = _first_value_id(resolution)
    if not column_id:
        raise DispatchStepFailure("choice_column_resolution_failed", "resolution")
    replacements["column-id"] = column_id
    preflight_path = _render_path(unit["preflight_idempotency_check"]["path_template"], replacements)
    try:
        preflight = client.get(preflight_path)
    except Exception as exc:
        raise _safe_failure(exc, "preflight") from exc
    required_choices = [
        str(value) for value in unit["preflight_idempotency_check"].get("required_choice_values", [])
    ]
    current_choice = _choice_config(preflight)
    preserved_choice_settings = {
        key: current_choice[key]
        for key in ("allowTextEntry", "displayAs")
        if key in current_choice
    }
    current_choices = [str(value) for value in current_choice.get("choices", [])]
    merged_choices = list(dict.fromkeys([*current_choices, *required_choices]))
    exists = all(choice in current_choices for choice in required_choices)
    mutation_path = _render_path(plan_step["request"]["path_template"], replacements)
    mutation_shape: dict[str, Any] = {}
    mutation_outcome = MUTATION_SKIPPED if exists else MUTATION_NOT_ATTEMPTED
    if not exists:
        plan_choice = dict(plan_step["request"]["body"].get("choice", {}))
        plan_choice["@odata.type"] = CHOICE_COLUMN_ODATA_TYPE
        for key in ("allowTextEntry", "displayAs"):
            if key in current_choice:
                plan_choice[key] = current_choice[key]
        plan_choice["choices"] = merged_choices
        patch_body = {"choice": plan_choice}
        try:
            mutation_shape = client.patch(mutation_path, patch_body)
            mutation_outcome = MUTATION_CONFIRMED
        except Exception as exc:
            raise _safe_failure(
                exc,
                "mutation",
                mutation_attempted=True,
                mutation_outcome=MUTATION_POSSIBLE,
                diagnostic=_choice_patch_failure_diagnostic(
                    exc,
                    preflight=preflight,
                    request_body=patch_body,
                    current_choice_count=len(current_choices),
                    required_choice_count=len(required_choices),
                    merged_choice_count=len(merged_choices),
                ),
            ) from exc
    try:
        readback = client.get(preflight_path)
    except Exception as exc:
        raise _safe_failure(
            exc,
            "readback",
            mutation_attempted=not exists,
            mutation_outcome=mutation_outcome,
        ) from exc
    readback_choice = _choice_config(readback)
    readback_choices = [str(value) for value in readback_choice.get("choices", [])]
    choices_preserved = all(choice in readback_choices for choice in merged_choices)
    settings_preserved = all(
        readback_choice.get(key) == value for key, value in preserved_choice_settings.items()
    )
    if not choices_preserved or not settings_preserved:
        raise DispatchStepFailure(
            "choice_readback_verification_failed",
            "readback",
            mutation_attempted=not exists,
            mutation_outcome=mutation_outcome,
        )
    return _redacted_dispatch_step(
        workspace=workspace,
        unit=unit,
        plan_step=plan_step,
        sequence=sequence,
        preflight_path=preflight_path,
        mutation_path=mutation_path,
        readback_path=preflight_path,
        mutation_outcome=mutation_outcome,
        readback_count=1,
        mutation_shape=mutation_shape,
    )


def _pending_step(
    workspace: dict[str, Any],
    unit: dict[str, Any],
    plan_step: dict[str, Any],
    sequence: int,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "id": unit["id"],
        "sourceStepId": unit["source_step_id"],
        "workspaceId": workspace["workspace_id"],
        "operation": unit["operation"],
        "target": unit["target"],
        "status": "RUNNING",
        "method": plan_step["request"]["method"],
        "ownerGateRequired": True,
        "graphRestOnly": True,
        "mutationIntentPersisted": True,
        "mutationAttempted": False,
        "mutationOutcome": MUTATION_POSSIBLE,
        "mutationExecuted": False,
        "skippedBecauseAlreadyExists": False,
        "rawGraphPathStored": False,
        "rawGraphResponseStored": False,
        "rawMutationPayloadStored": False,
    }


def _failed_step(
    workspace: dict[str, Any],
    unit: dict[str, Any],
    plan_step: dict[str, Any],
    sequence: int,
    failure: DispatchStepFailure,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "stepId": unit["id"],
        "code": failure.code,
        "phase": failure.phase,
    }
    if failure.http_status is not None:
        error["httpStatus"] = failure.http_status
    if failure.diagnostic is not None:
        error["diagnostic"] = failure.diagnostic
    return {
        "sequence": sequence,
        "id": unit["id"],
        "sourceStepId": unit["source_step_id"],
        "workspaceId": workspace["workspace_id"],
        "operation": unit["operation"],
        "target": unit["target"],
        "status": "FAILED",
        "error": error,
        "method": plan_step["request"]["method"],
        "ownerGateRequired": True,
        "graphRestOnly": True,
        "mutationAttempted": failure.mutation_attempted,
        "mutationOutcome": failure.mutation_outcome,
        "mutationExecuted": failure.mutation_outcome == MUTATION_CONFIRMED,
        "skippedBecauseAlreadyExists": failure.mutation_outcome == MUTATION_SKIPPED,
        "rawGraphPathStored": False,
        "rawGraphResponseStored": False,
        "rawMutationPayloadStored": False,
    }


def _redacted_dispatch_step(
    *,
    workspace: dict[str, Any],
    unit: dict[str, Any],
    plan_step: dict[str, Any],
    sequence: int,
    preflight_path: str,
    mutation_path: str,
    readback_path: str,
    mutation_outcome: str,
    readback_count: int,
    mutation_shape: dict[str, Any],
) -> dict[str, Any]:
    mutation_executed = mutation_outcome == MUTATION_CONFIRMED
    skipped = mutation_outcome == MUTATION_SKIPPED
    return {
        "sequence": sequence,
        "id": unit["id"],
        "sourceStepId": unit["source_step_id"],
        "workspaceId": workspace["workspace_id"],
        "operation": unit["operation"],
        "target": unit["target"],
        "status": "PASSED",
        "method": plan_step["request"]["method"],
        "ownerGateRequired": True,
        "graphRestOnly": True,
        "preflightPathSha256": _sha256(preflight_path),
        "mutationPathSha256": _sha256(mutation_path),
        "readbackPathSha256": _sha256(readback_path),
        "mutationAttempted": mutation_executed,
        "mutationOutcome": mutation_outcome,
        "mutationExecuted": mutation_executed,
        "skippedBecauseAlreadyExists": skipped,
        "readbackValueCount": readback_count,
        "mutationResponseShapeKeys": sorted(mutation_shape) if mutation_shape else [],
        "bodyShapeKeys": sorted(plan_step["request"]["body"]),
        "rawGraphPathStored": False,
        "rawGraphResponseStored": False,
        "rawMutationPayloadStored": False,
    }


def _safe_failure(
    exc: Exception,
    phase: str,
    *,
    mutation_attempted: bool = False,
    mutation_outcome: str = MUTATION_NOT_ATTEMPTED,
    diagnostic: dict[str, Any] | None = None,
) -> DispatchStepFailure:
    if isinstance(exc, DispatchStepFailure):
        return exc
    if isinstance(exc, GraphHttpError):
        return DispatchStepFailure(
            "graph_http_error",
            phase,
            mutation_attempted=mutation_attempted,
            mutation_outcome=mutation_outcome,
            http_status=exc.status,
            diagnostic=diagnostic,
        )
    return DispatchStepFailure(
        "graph_request_failed",
        phase,
        mutation_attempted=mutation_attempted,
        mutation_outcome=mutation_outcome,
        diagnostic=diagnostic,
    )


def _choice_patch_failure_diagnostic(
    exc: Exception,
    *,
    preflight: dict[str, Any],
    request_body: dict[str, Any],
    current_choice_count: int,
    required_choice_count: int,
    merged_choice_count: int,
) -> dict[str, Any]:
    graph_error = _closed_graph_error(exc)
    request_choice = request_body.get("choice")
    request_choice_object = request_choice if isinstance(request_choice, dict) else {}
    request_choices = request_choice_object.get("choices")
    column = _column_definition(preflight)
    column_choice = column.get("choice")
    column_choice_object = column_choice if isinstance(column_choice, dict) else {}
    column_choices = column_choice_object.get("choices")
    raw_counts = {
        "currentChoiceCount": current_choice_count,
        "requiredChoiceCount": required_choice_count,
        "mergedChoiceCount": merged_choice_count,
        "requestChoiceCount": len(request_choices) if isinstance(request_choices, list) else 0,
        "requestBodyFieldCount": len(request_body),
        "choiceFacetFieldCount": len(request_choice_object),
    }
    return {
        "contract": "choice_patch_failure/v1",
        "graphError": graph_error,
        "retryDisposition": _retry_disposition(exc, graph_error["class"]),
        "endpoint": "COLUMN_DEFINITION_UPDATE",
        "facet": "CHOICE",
        "expectedHttpStatus": 200,
        "columnShape": {
            "choiceFacetPresent": "choice" in column,
            "choiceFacetIsObject": isinstance(column_choice, dict),
            "choicesPresent": "choices" in column_choice_object,
            "choicesIsArray": isinstance(column_choices, list),
            "readOnlyPresent": "readOnly" in column,
            "readOnlyIsBoolean": isinstance(column.get("readOnly"), bool),
            "readOnlyTrue": column.get("readOnly") is True,
            "sealedPresent": "sealed" in column,
            "sealedIsBoolean": isinstance(column.get("sealed"), bool),
            "sealedTrue": column.get("sealed") is True,
            "indexedPresent": "indexed" in column,
            "indexedIsBoolean": isinstance(column.get("indexed"), bool),
            "indexedTrue": column.get("indexed") is True,
        },
        "requestShape": {
            "bodyIsObject": isinstance(request_body, dict),
            "choiceFacetPresent": "choice" in request_body,
            "choiceFacetIsObject": isinstance(request_choice, dict),
            "odataTypePresent": "@odata.type" in request_choice_object,
            "odataTypeAllowlisted": request_choice_object.get("@odata.type")
            == CHOICE_COLUMN_ODATA_TYPE,
            "choicesPresent": "choices" in request_choice_object,
            "choicesIsArray": isinstance(request_choices, list),
            "allowTextEntryPresent": "allowTextEntry" in request_choice_object,
            "allowTextEntryIsBoolean": isinstance(
                request_choice_object.get("allowTextEntry"), bool
            ),
            "displayAsPresent": "displayAs" in request_choice_object,
            "displayAsRecognized": request_choice_object.get("displayAs")
            in {"checkBoxes", "dropDownMenu", "radioButtons"},
        },
        "counts": {
            **{key: min(value, MAX_DIAGNOSTIC_COUNT) for key, value in raw_counts.items()},
            "countsCapped": any(value > MAX_DIAGNOSTIC_COUNT for value in raw_counts.values()),
        },
    }


def _closed_graph_error(exc: Exception) -> dict[str, Any]:
    envelope = "NOT_AVAILABLE"
    error_object: dict[str, Any] = {}
    if isinstance(exc, GraphHttpError):
        body = exc.body
        if not body:
            envelope = "EMPTY"
        else:
            try:
                parsed = json.loads(body)
            except (json.JSONDecodeError, TypeError):
                envelope = "MALFORMED"
            else:
                candidate = parsed.get("error") if isinstance(parsed, dict) else None
                if isinstance(candidate, dict):
                    envelope = "STANDARD"
                    error_object = candidate
                else:
                    envelope = "NONSTANDARD"
    code = _deepest_recognized_graph_code(error_object)
    return {
        "envelope": envelope,
        "code": code,
        "class": GRAPH_ERROR_CLASS_BY_CODE.get(code, "UNCLASSIFIED"),
        "messagePresent": "message" in error_object,
        "innerErrorPresent": "innerError" in error_object,
        "detailsPresent": "details" in error_object,
    }


def _deepest_recognized_graph_code(error_object: dict[str, Any]) -> str:
    code = "UNCLASSIFIED"
    current = error_object
    for _depth in range(MAX_GRAPH_INNER_ERROR_DEPTH + 1):
        candidate = current.get("code")
        if isinstance(candidate, str) and candidate in GRAPH_ERROR_CLASS_BY_CODE:
            code = candidate
        inner_error = current.get("innerError")
        if type(inner_error) is not dict:
            break
        current = inner_error
    return code


def _retry_disposition(exc: Exception, error_class: str) -> str:
    if error_class == "REQUEST_VALIDATION":
        return "DO_NOT_RETRY_UNCHANGED"
    if isinstance(exc, GraphHttpError) and exc.status in {429, 500, 502, 503, 504}:
        return "RETRY_WITH_BACKOFF"
    return "REVIEW_REQUIRED"


def _column_definition(response: dict[str, Any]) -> dict[str, Any]:
    value = response.get("value")
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return response


def _base_replacements(workspace: dict[str, Any], unit: dict[str, Any], plan_step: dict[str, Any]) -> dict[str, str]:
    body = plan_step["request"]["body"]
    column_name = str(body.get("name") or unit["preflight_idempotency_check"].get("match", {}).get("name") or "")
    return {
        "site-id": str(workspace["site_id"]),
        "list-id": str(unit.get("target_list_or_library_id") or ""),
        "target-display-name": str(unit["target"]),
        "column-name": column_name,
    }


def _render_path(template: str, replacements: dict[str, str]) -> str:
    path = template
    for key, value in replacements.items():
        safe = "," if key == "site-id" else ""
        if key in {"target-display-name", "column-name"}:
            safe = ""
        path = path.replace("{" + key + "}", urllib.parse.quote(value.replace("'", "''"), safe=safe))
    if not path.startswith("/"):
        raise RuntimeError("Graph REST path must start with /")
    if path.startswith("/_api") or "/_api/" in path:
        raise RuntimeError("legacy SharePoint REST path is blocked")
    return urllib.parse.quote(path, safe="/:?&=$,()%-")


def _value_count(response: dict[str, Any]) -> int:
    value = response.get("value")
    return len(value) if isinstance(value, list) else (1 if response else 0)


def _first_value_id(response: dict[str, Any]) -> str:
    value = response.get("value")
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return str(value[0].get("id") or "")
    return ""


def _choice_config(response: dict[str, Any]) -> dict[str, Any]:
    if isinstance(response.get("choice"), dict):
        return dict(response["choice"])
    value = response.get("value")
    if isinstance(value, list) and value and isinstance(value[0], dict):
        choice = value[0].get("choice")
        if isinstance(choice, dict):
            return dict(choice)
    return {}


def _payload_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _sha256(canonical)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _dispatcher_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Process Ontology SharePoint Schema Apply Graph Dispatcher",
        "",
        f"- Status: `{payload['status']}`",
        f"- Schema: `{payload['schema_version']}`",
        f"- Correlation ID: `{summary['correlation_id']}`",
        f"- Dispatched steps: `{summary['dispatched_step_count']}`",
        f"- Mutations executed: `{summary['mutation_request_count']}`",
        f"- Executed Graph requests: `{summary['executed_graph_requests']}`",
        f"- Executed Graph writes: `{summary['executed_graph_writes']}`",
        f"- Stopped on first failure: `{summary['stopped_on_first_failure']}`",
        "",
        "## Guardrails",
        "",
    ]
    for key, value in payload["guardrails"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def _atomic_write_text(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _resolve_output_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _relative_path(repo_root: Path, path: Path) -> str:
    return str(path.relative_to(repo_root) if path.is_relative_to(repo_root) else path)
