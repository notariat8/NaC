from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_m365_graph.business_case_type_write_plan import (  # noqa: E402
    BoundWriteTarget,
    BusinessCaseTypeWritePlanBuilder,
    MutationAuthorization,
)
from notary_kg.business_case_type_mutation import BusinessCaseTypeMutation  # noqa: E402


class BusinessCaseTypeGraphQueryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target = BoundWriteTarget(
            workspace_id="notary-team-synthetic",
            site_id="synthetic.sharepoint.com,site-id,web-id",
            akten_list_id="00000000-0000-4000-8000-000000000010",
            aufgaben_list_id="00000000-0000-4000-8000-000000000011",
            write_identity_id="synthetic-write-identity",
            bff_uami_identity_id="synthetic-read-identity",
        )
        self.builder = BusinessCaseTypeWritePlanBuilder(self.target)

    def _authorization(self, operation: str, list_id: str) -> MutationAuthorization:
        return MutationAuthorization(
            workspace_id=self.target.workspace_id,
            site_id=self.target.site_id,
            list_id=list_id,
            actor_role="notary_clerk",
            purpose="matter_workflow",
            approval_ref=f"synthetic-approval-{operation}",
            approved_operation=operation,
            write_approved=True,
            write_identity_id=self.target.write_identity_id,
            write_identity_permission="Sites.Selected",
            write_site_grant_role="write",
            write_identity_site_id=self.target.site_id,
            bff_uami_identity_id=self.target.bff_uami_identity_id,
            bff_uami_permission="Sites.Selected",
            bff_uami_site_grant_role="read",
            bff_uami_site_id=self.target.site_id,
        )

    def test_case_create_uses_only_documented_list_query_options(self) -> None:
        mutation = BusinessCaseTypeMutation.case_create(
            {
                "NacCaseId": "synthetic-case-01",
                "Aktenzeichen": "SYN-01",
                "Vorgangstyp": "immobilienkaufvertrag",
                "VorgangstypId": "immobilienkaufvertrag",
                "Status": "Entwurf",
                "NotarTeam": "NaC-Notar-01",
                "Vertraulichkeitsstufe": "Normal",
                "NacWorkflowVersion": "synthetic-v1",
                "KgVersion": "synthetic-v1",
            }
        )
        plan = self.builder.build(
            mutation,
            self._authorization(mutation.operation, self.target.akten_list_id),
        )
        self._assert_documented_dedupe_query(plan.dedupe_request.url, "NacCaseId")

    def test_task_create_uses_only_documented_list_query_options(self) -> None:
        mutation = BusinessCaseTypeMutation.task_create(
            {
                "NacTaskId": "synthetic-task-01",
                "NacCaseId": "synthetic-case-01",
                "BpmnStepCode": "draft-contract",
                "Status": "Offen",
                "RequiresNotaryApproval": True,
            }
        )
        plan = self.builder.build(
            mutation,
            self._authorization(mutation.operation, self.target.aufgaben_list_id),
        )
        self._assert_documented_dedupe_query(plan.dedupe_request.url, "NacTaskId")

    def test_odata_literal_quotes_are_doubled_then_percent_encoded(self) -> None:
        mutation = BusinessCaseTypeMutation.task_create(
            {
                "NacTaskId": "synthetic-task-o'case",
                "NacCaseId": "synthetic-case-01",
                "BpmnStepCode": "draft-contract",
                "Status": "Offen",
                "RequiresNotaryApproval": False,
            }
        )
        plan = self.builder.build(
            mutation,
            self._authorization(mutation.operation, self.target.aufgaben_list_id),
        )
        self.assertIn("synthetic-task-o%27%27case", plan.dedupe_request.url)

    def _assert_documented_dedupe_query(self, url: str, field: str) -> None:
        self.assertIn("?expand=fields(select=", url)
        self.assertIn(f"&$filter=fields/{field}%20eq%20%27", url)
        self.assertNotIn("$select=", url)
        self.assertNotIn("$top=", url)
        self.assertNotIn("$expand=", url)
        self.assertNotIn("$skip", url)
        self.assertNotIn("$orderby", url)


if __name__ == "__main__":
    unittest.main()
