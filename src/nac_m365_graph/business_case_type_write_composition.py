from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from notary_kg.business_case_type_mutation import BusinessCaseTypeMutation

from .business_case_type_write_edge import (
    BusinessCaseTypeGraphWriteEdge,
    MutationExecutionResult,
)
from .business_case_type_write_plan import (
    GRAPH_BASE_URL,
    BoundWriteTarget,
    BusinessCaseTypeWritePlan,
    BusinessCaseTypeWritePlanBuilder,
    MutationAuthorization,
)
from .business_case_type_write_state import SqliteMutationEvidenceHook
from .business_case_type_write_transport import (
    GraphRestV1WriteTransport,
    GraphWriteAccessTokenProvider,
    HttpTransportPort,
)


@dataclass(frozen=True, slots=True)
class BusinessCaseTypeWriteComposition:
    """Local S4c composition without credential discovery or live factories."""

    target: BoundWriteTarget
    plan_builder: BusinessCaseTypeWritePlanBuilder
    state: SqliteMutationEvidenceHook
    edge: BusinessCaseTypeGraphWriteEdge

    def build_plan(
        self,
        mutation: BusinessCaseTypeMutation,
        authorization: MutationAuthorization,
    ) -> BusinessCaseTypeWritePlan:
        return self.plan_builder.build(mutation, authorization)

    def execute(
        self,
        mutation: BusinessCaseTypeMutation,
        authorization: MutationAuthorization,
    ) -> MutationExecutionResult:
        plan = self.build_plan(mutation, authorization)
        return self.edge.execute(plan)


def build_offline_business_case_type_write_composition(
    *,
    target: BoundWriteTarget,
    database_path: Path,
    token_provider: GraphWriteAccessTokenProvider,
    http_port: HttpTransportPort,
) -> BusinessCaseTypeWriteComposition:
    """Compose injected ports; this function never discovers credentials."""

    builder = BusinessCaseTypeWritePlanBuilder(target)
    state = SqliteMutationEvidenceHook(database_path)
    transport = GraphRestV1WriteTransport(
        token_provider,
        http_port,
        allowed_collection_urls=_collection_urls(target),
    )
    edge = BusinessCaseTypeGraphWriteEdge(transport, state, builder)
    return BusinessCaseTypeWriteComposition(
        target=target,
        plan_builder=builder,
        state=state,
        edge=edge,
    )


def _collection_urls(target: BoundWriteTarget) -> tuple[str, str]:
    site = urllib.parse.quote(target.site_id, safe=",")
    akten = urllib.parse.quote(target.akten_list_id, safe="")
    aufgaben = urllib.parse.quote(target.aufgaben_list_id, safe="")
    return (
        f"{GRAPH_BASE_URL}/sites/{site}/lists/{akten}/items",
        f"{GRAPH_BASE_URL}/sites/{site}/lists/{aufgaben}/items",
    )
