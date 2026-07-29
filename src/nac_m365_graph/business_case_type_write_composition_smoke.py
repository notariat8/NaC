from __future__ import annotations

import json
from collections import deque
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from notary_kg.business_case_type_mutation import (
    BusinessCaseTypeMutation,
    S5BackfillBinding,
    canonical_hash,
)

from .business_case_type_write_composition import (
    build_offline_business_case_type_write_composition,
)
from .business_case_type_write_plan import BoundWriteTarget, MutationAuthorization
from .business_case_type_write_transport import HttpTransportResponse


S4C_COMPOSITION_READY_OFFLINE = "S4C_COMPOSITION_READY_OFFLINE"
_OPERATIONS = (
    "case_create",
    "case_status_update",
    "task_create",
    "task_update",
    "business_case_type_backfill",
)


class _SyntheticTokenProvider:
    def __init__(self) -> None:
        self.calls = 0

    def fetch_access_token(self) -> str:
        self.calls += 1
        return "synthetic-offline-token"


class _ScriptedHttpPort:
    def __init__(self, responses: list[HttpTransportResponse]) -> None:
        self._responses = deque(responses)
        self.calls = 0

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        follow_redirects: bool,
        automatic_retries: int,
        max_response_bytes: int,
    ) -> HttpTransportResponse:
        self.calls += 1
        if follow_redirects or automatic_retries != 0:
            raise AssertionError("offline transport policy drift")
        if not url.startswith("https://graph.microsoft.com/v1.0/"):
            raise AssertionError("offline Graph origin drift")
        if headers.get("Authorization") != "Bearer synthetic-offline-token":
            raise AssertionError("synthetic token injection drift")
        if max_response_bytes != 1024 * 1024:
            raise AssertionError("response limit drift")
        if method == "GET" and body is not None:
            raise AssertionError("GET body drift")
        if not self._responses:
            raise AssertionError("unexpected synthetic HTTP call")
        return self._responses.popleft()

    @property
    def exhausted(self) -> bool:
        return not self._responses


def build_business_case_type_write_composition_smoke(
    *,
    database_path: Path,
) -> dict[str, Any]:
    if not isinstance(database_path, Path) or not database_path.is_absolute():
        raise ValueError("database_path must be absolute")
    target = _target()
    base_authorization = _authorization(target)
    mutations = _mutations()
    token_provider = _SyntheticTokenProvider()
    http_port = _ScriptedHttpPort(_responses(mutations))
    composition = build_offline_business_case_type_write_composition(
        target=target,
        database_path=database_path,
        token_provider=token_provider,
        http_port=http_port,
    )

    results: list[dict[str, Any]] = []
    for mutation in mutations:
        authorization = _authorization_for(base_authorization, target, mutation)
        result = composition.execute(mutation, authorization)
        results.append(
            {
                "operation": result.operation,
                "status": result.status,
                "reason_code": result.reason_code,
                "transport_calls": result.transport_calls,
                "write_attempts": result.write_attempts,
            }
        )

    statuses = [result["status"] for result in results]
    ready = (
        tuple(result["operation"] for result in results) == _OPERATIONS
        and statuses == ["APPLIED"] * len(_OPERATIONS)
        and http_port.exhausted
        and token_provider.calls == http_port.calls
    )
    return {
        "schema_version": (
            "nac.business-case-type-graph-write-composition-smoke/v0.1"
        ),
        "status": S4C_COMPOSITION_READY_OFFLINE if ready else "BLOCKED",
        "data_classification": "synthetic",
        "operations": results,
        "summary": {
            "operations_expected": len(_OPERATIONS),
            "operations_applied": statuses.count("APPLIED"),
            "synthetic_http_port_calls": http_port.calls,
            "synthetic_token_provider_calls": token_provider.calls,
            "socket_or_dns_calls": 0,
            "external_credential_store_reads": 0,
            "live_graph_calls": 0,
            "tenant_writes": 0,
            "automatic_retries": 0,
            "central_durability_claimed": False,
            "production_ready_claimed": False,
        },
    }


def format_business_case_type_write_composition_smoke(
    result: Mapping[str, Any],
) -> str:
    summary = result.get("summary", {})
    operations = result.get("operations", [])
    lines = [
        "BusinessCaseType Graph write composition S4c offline smoke",
        f"Status: {result.get('status', 'BLOCKED')}",
        (
            f"Operations: {summary.get('operations_applied', 0)}/"
            f"{summary.get('operations_expected', 0)} applied"
        ),
        (
            "Synthetic token-provider calls: "
            f"{summary.get('synthetic_token_provider_calls', 0)}"
        ),
        "Live Graph calls: 0",
        "Tenant writes: 0",
    ]
    for operation in operations if isinstance(operations, list) else []:
        if isinstance(operation, Mapping):
            lines.append(
                f"- {operation.get('operation', 'unknown')}: "
                f"{operation.get('status', 'BLOCKED')}"
            )
    return "\n".join(lines) + "\n"


def _target() -> BoundWriteTarget:
    return BoundWriteTarget(
        workspace_id="synthetic-workspace-01",
        site_id="synthetic.example,site-collection,site-01",
        akten_list_id="00000000-0000-4000-8000-000000000010",
        aufgaben_list_id="00000000-0000-4000-8000-000000000011",
        write_identity_id="synthetic-write-identity-01",
        bff_uami_identity_id="synthetic-bff-uami-read-01",
    )


def _authorization(target: BoundWriteTarget) -> MutationAuthorization:
    return MutationAuthorization(
        workspace_id=target.workspace_id,
        site_id=target.site_id,
        list_id=target.akten_list_id,
        actor_role="notary_clerk",
        purpose="matter_workflow",
        approval_ref="synthetic-approval-case-create-01",
        approved_operation="case_create",
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


def _authorization_for(
    base: MutationAuthorization,
    target: BoundWriteTarget,
    mutation: BusinessCaseTypeMutation,
) -> MutationAuthorization:
    task_operation = mutation.operation.startswith("task_")
    migration = mutation.operation == "business_case_type_backfill"
    return replace(
        base,
        list_id=(
            target.aufgaben_list_id if task_operation else target.akten_list_id
        ),
        actor_role="BackfillOperator" if migration else "notary_clerk",
        purpose=(
            "business_case_type_migration" if migration else "matter_workflow"
        ),
        approved_operation=mutation.operation,
        approval_ref=(
            f"synthetic-approval-{mutation.operation.replace('_', '-')}-01"
        ),
    )


def _mutations() -> list[BusinessCaseTypeMutation]:
    case_create = BusinessCaseTypeMutation.case_create(
        {
            "NacCaseId": "synthetic-s4c-case-01",
            "Aktenzeichen": "S4C-SYN-01",
            "Vorgangstyp": "immobilienkaufvertrag",
            "VorgangstypId": "immobilienkaufvertrag",
            "Status": "Entwurf",
            "NotarTeam": "NaC-Notar-01",
            "Vertraulichkeitsstufe": "Normal",
            "NacWorkflowVersion": "workflow-v1",
            "KgVersion": "kg-v1",
        }
    )
    case_update = BusinessCaseTypeMutation.case_status_update(
        item_id="17",
        expected_etag="synthetic-etag-17",
        fields={"Status": "Vollzug"},
    )
    task_create = BusinessCaseTypeMutation.task_create(
        {
            "NacTaskId": "synthetic-s4c-task-01",
            "NacCaseId": "synthetic-s4c-case-01",
            "BpmnStepCode": "draft-contract",
            "Status": "Offen",
            "RequiresNotaryApproval": True,
        }
    )
    task_update = BusinessCaseTypeMutation.task_update(
        item_id="23",
        expected_etag="synthetic-etag-23",
        fields={"Status": "Erledigt"},
    )
    operation = {
        "record_ref_hash": "b" * 64,
        "field": "VorgangstypId",
        "value": "immobilienkaufvertrag",
        "if_match": "synthetic-etag-backfill-01",
        "idempotency_key": (
            "30927974be4fd41f6c90c62be62aeab5a75abedd247762527afa92f0c77df060"
        ),
    }
    backfill = BusinessCaseTypeMutation.business_case_type_backfill(
        item_id="41",
        expected_etag=operation["if_match"],
        business_case_type_id=operation["value"],
        s5_binding=S5BackfillBinding(
            manifest_hash="a" * 64,
            record_ref_hash=operation["record_ref_hash"],
            operation_hash=canonical_hash(operation),
            idempotency_key=operation["idempotency_key"],
        ),
    )
    return [case_create, case_update, task_create, task_update, backfill]


def _responses(
    mutations: list[BusinessCaseTypeMutation],
) -> list[HttpTransportResponse]:
    responses: list[HttpTransportResponse] = []
    item_ids = ("81", "17", "82", "23", "41")
    for mutation, item_id in zip(
        mutations,
        item_ids[: len(mutations)],
        strict=True,
    ):
        etag = mutation.expected_etag or f"synthetic-etag-{item_id}"
        if mutation.operation in {"case_create", "task_create"}:
            responses.extend(
                [
                    _http_json(200, {"value": []}),
                    _http_json(201, {"id": item_id, "eTag": etag}),
                    _http_json(
                        200,
                        {
                            "id": item_id,
                            "eTag": etag,
                            "fields": dict(mutation.fields),
                        },
                    ),
                ]
            )
        else:
            responses.extend(
                [
                    _http_json(
                        200,
                        {
                            "id": item_id,
                            "eTag": etag,
                            "fields": dict(mutation.fields),
                        },
                    ),
                    _http_json(200, {}),
                    _http_json(
                        200,
                        {
                            "id": item_id,
                            "eTag": f"{etag}-after",
                            "fields": dict(mutation.fields),
                        },
                    ),
                ]
            )
    return responses


def _http_json(
    status_code: int,
    body: Mapping[str, Any],
) -> HttpTransportResponse:
    return HttpTransportResponse(
        status_code=status_code,
        body=json.dumps(
            body,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
    )
