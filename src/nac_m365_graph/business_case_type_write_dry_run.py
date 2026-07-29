from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nac_m365_graph.business_case_type_write_plan import (
    BoundWriteTarget,
    BusinessCaseTypeWritePlanBuilder,
    MutationAuthorization,
)
from notary_kg.business_case_type_mutation import (
    BusinessCaseTypeMutation,
    S5BackfillBinding,
    canonical_hash,
)


CONTRACT_PATH = Path(
    "workflows/contracts/business-case-type-graph-write-edge-s4b.contract.json"
)
CONTRACT_VERSION = "nac.business-case-type-graph-write-edge-s4b/v0.1"
DEFAULT_OPERATION = "case_create"
WRITE_DRY_RUN_OPERATIONS = (
    "case_create",
    "case_status_update",
    "task_create",
    "task_update",
    "business_case_type_backfill",
)


def build_business_case_type_write_dry_run(
    repo_root: Path,
    *,
    operation: str = DEFAULT_OPERATION,
) -> dict[str, Any]:
    contract = _load_contract(repo_root)
    gates = {
        "contract_valid": _contract_is_valid(contract),
        "operation_allowed": operation in WRITE_DRY_RUN_OPERATIONS,
        "synthetic_input_only": True,
        "graph_rest_v1_only": True,
        "separate_write_identity": True,
        "bff_read_identity_unchanged": True,
        "credentials_loaded": False,
        "live_factory_instantiated": False,
        "graph_calls": 0,
        "tenant_writes": 0,
    }
    if not gates["contract_valid"] or not gates["operation_allowed"]:
        return _blocked_result(operation, gates)

    target = _synthetic_target()
    mutation = _synthetic_mutation(operation)
    authorization = _synthetic_authorization(target, mutation)
    plan = BusinessCaseTypeWritePlanBuilder(target).build(mutation, authorization)
    preflight = plan.dedupe_request or plan.freshness_request
    return {
        "status": "PASSED",
        "mode": "offline_dry_run",
        "operation": mutation.operation,
        "method": plan.write_method,
        "graph_version": "v1.0",
        "logical_list_name": plan.logical_list_name,
        "field_names": list(plan.mutation.fields),
        "request_phases": [preflight.phase, "write", "readback"],
        "preflight_method": preflight.method,
        "write_request_prepared": True,
        "write_request_executed": False,
        "plan_sha256": plan.plan_sha256,
        "target_binding_sha256": plan.target_binding_hash,
        "gate_results": gates,
        "contract_version": CONTRACT_VERSION,
    }


def format_business_case_type_write_dry_run(result: dict[str, Any]) -> str:
    lines = [
        f"STATUS: {result['status']}",
        "Mode: offline dry run",
        f"Operation: {result['operation']}",
        f"Method: {result.get('method', 'BLOCKED')}",
        f"Graph version: {result.get('graph_version', 'v1.0')}",
        f"Logical list: {result.get('logical_list_name', 'BLOCKED')}",
        f"Fields: {', '.join(result.get('field_names', []))}",
        f"Write executed: {str(result.get('write_request_executed', False)).lower()}",
        f"Contract version: {result['contract_version']}",
        "Gates:",
    ]
    lines.extend(
        f"  {name}: {str(value).lower()}"
        for name, value in result['gate_results'].items()
    )
    return "\n".join(lines) + "\n"


def _blocked_result(operation: str, gates: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "BLOCKED",
        "mode": "offline_dry_run",
        "operation": operation,
        "write_request_prepared": False,
        "write_request_executed": False,
        "gate_results": gates,
        "contract_version": CONTRACT_VERSION,
    }


def _load_contract(repo_root: Path) -> dict[str, Any]:
    try:
        payload = json.loads((repo_root / CONTRACT_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _contract_is_valid(contract: dict[str, Any]) -> bool:
    offline = contract.get("offline_boundary")
    cli = contract.get("offline_cli")
    identity = contract.get("identity_boundary")
    binding = contract.get("binding")
    operations = contract.get("operations")
    return all(
        (
            contract.get("schema_version") == CONTRACT_VERSION,
            contract.get("status") == "implemented_offline",
            isinstance(operations, dict)
            and tuple(operations) == WRITE_DRY_RUN_OPERATIONS,
            isinstance(binding, dict)
            and binding.get("graph_base_url_exact")
            == "https://graph.microsoft.com/v1.0",
            isinstance(identity, dict)
            and identity.get("write_permission_exact") == "Sites.Selected",
            isinstance(identity, dict)
            and identity.get("write_site_grant_role_exact") == "write",
            isinstance(identity, dict)
            and identity.get("bff_uami_site_grant_role_exact") == "read",
            isinstance(offline, dict)
            and offline.get("cli_changes_in_scope") is True,
            isinstance(offline, dict)
            and offline.get("dns_network_graph_sharepoint_entra_calls_allowed")
            is False,
            isinstance(offline, dict)
            and offline.get("credential_environment_token_or_certificate_reads_allowed")
            is False,
            isinstance(offline, dict)
            and offline.get("tenant_schema_permission_or_data_writes_allowed")
            is False,
            isinstance(cli, dict)
            and cli.get("command_exact")
            == "nac m365 teams-sharepoint business-case-type-write-dry-run",
            isinstance(cli, dict)
            and isinstance(cli.get("operations_exact"), list)
            and tuple(cli["operations_exact"]) == WRITE_DRY_RUN_OPERATIONS,
            isinstance(cli, dict) and cli.get("synthetic_only") is True,
            isinstance(cli, dict) and cli.get("redacted_output_only") is True,
            isinstance(cli, dict)
            and cli.get("resource_identifiers_or_urls_in_output_allowed")
            is False,
            isinstance(cli, dict)
            and cli.get("field_values_in_output_allowed") is False,
            isinstance(cli, dict) and cli.get("live_factory_allowed") is False,
            isinstance(cli, dict) and cli.get("credentials_allowed") is False,
            isinstance(cli, dict) and cli.get("live_graph_calls_allowed") == 0,
            isinstance(cli, dict) and cli.get("tenant_writes_allowed") == 0,
        )
    )


def _synthetic_target() -> BoundWriteTarget:
    return BoundWriteTarget(
        workspace_id="synthetic-workspace-dry-run",
        site_id="synthetic.example,dry-run,site",
        akten_list_id="00000000-0000-4000-8000-000000000010",
        aufgaben_list_id="00000000-0000-4000-8000-000000000011",
        write_identity_id="synthetic-write-identity-dry-run",
        bff_uami_identity_id="synthetic-bff-read-identity-dry-run",
    )


def _synthetic_authorization(
    target: BoundWriteTarget,
    mutation: BusinessCaseTypeMutation,
) -> MutationAuthorization:
    task_operation = mutation.operation in {"task_create", "task_update"}
    backfill = mutation.operation == "business_case_type_backfill"
    return MutationAuthorization(
        workspace_id=target.workspace_id,
        site_id=target.site_id,
        list_id=target.aufgaben_list_id if task_operation else target.akten_list_id,
        actor_role="BackfillOperator" if backfill else "notary_clerk",
        purpose="business_case_type_migration" if backfill else "matter_workflow",
        approval_ref=f"synthetic-approval-{mutation.operation}",
        approved_operation=mutation.operation,
        write_approved=True,
        write_identity_id=target.write_identity_id,
        write_identity_permission="Sites.Selected",
        write_site_grant_role="write",
        write_identity_site_id=target.site_id,
        bff_uami_identity_id=target.bff_uami_identity_id,
        bff_uami_permission="Sites.Selected",
        bff_uami_site_grant_role="read",
        bff_uami_site_id=target.site_id,
    )


def _synthetic_mutation(operation: str) -> BusinessCaseTypeMutation:
    if operation == "case_create":
        return BusinessCaseTypeMutation.case_create(
            {
                "NacCaseId": "synthetic-case-dry-run",
                "Aktenzeichen": "SYN-DRY-RUN",
                "Vorgangstyp": "immobilienkaufvertrag",
                "VorgangstypId": "immobilienkaufvertrag",
                "Status": "Entwurf",
                "NotarTeam": "NaC-Notar-01",
                "Vertraulichkeitsstufe": "Normal",
                "NacWorkflowVersion": "synthetic-workflow-v1",
                "KgVersion": "synthetic-kg-v1",
            }
        )
    if operation == "case_status_update":
        return BusinessCaseTypeMutation.case_status_update(
            item_id="17",
            expected_etag="synthetic-etag-17",
            fields={"Status": "Vollzug"},
        )
    if operation == "task_create":
        return BusinessCaseTypeMutation.task_create(
            {
                "NacTaskId": "synthetic-task-dry-run",
                "NacCaseId": "synthetic-case-dry-run",
                "BpmnStepCode": "synthetic-draft-contract",
                "Status": "Offen",
                "RequiresNotaryApproval": True,
                "DueDate": "2026-08-31T16:00:00Z",
            }
        )
    if operation == "task_update":
        return BusinessCaseTypeMutation.task_update(
            item_id="23",
            expected_etag="synthetic-etag-23",
            fields={"Status": "Erledigt"},
        )
    if operation == "business_case_type_backfill":
        manifest_hash = "a" * 64
        record_ref_hash = "b" * 64
        target = "immobilienkaufvertrag"
        etag = "synthetic-etag-41"
        idempotency_key = canonical_hash(
            [manifest_hash, record_ref_hash, target, etag]
        )
        operation_payload = {
            "record_ref_hash": record_ref_hash,
            "field": "VorgangstypId",
            "value": target,
            "if_match": etag,
            "idempotency_key": idempotency_key,
        }
        return BusinessCaseTypeMutation.business_case_type_backfill(
            item_id="41",
            expected_etag=etag,
            business_case_type_id=target,
            s5_binding=S5BackfillBinding(
                manifest_hash=manifest_hash,
                record_ref_hash=record_ref_hash,
                operation_hash=canonical_hash(operation_payload),
                idempotency_key=idempotency_key,
            ),
        )
    raise ValueError("unsupported write dry-run operation")
