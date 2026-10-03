from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from nac_bff.team_membership import FixedTeamMembership, TEAM_ID
from nac_bff.synthetic_workspace_graph import SYNTHETIC_SITE_ID, _validate_relative_graph_path
from nac_bff.team_membership import MEMBERSHIP_PATHS
from nac_bff.live_access_decision import TeamReadAccessDecisionAdapter
from nac_bff.test_environment import ALLOWED_WORKSPACE_ID, ALLOWED_MATTER_ID, ALLOWED_PURPOSE

ACTOR = "11111111-1111-4111-8111-111111111111"


class Client:
    base_url = "https://graph.microsoft.com/v1.0"
    redirects_allowed = False
    retains_error_body = False

    def __init__(self):
        self.responses = [
            {"id": TEAM_ID, "groupTypes": ["Unified"], "resourceProvisioningOptions": ["Team"]},
            {"id": SYNTHETIC_SITE_ID, "webUrl": "https://funktion8.sharepoint.com/sites/NaC-Notar-01"},
            {"value": [{"id": ACTOR}]},
        ]
        self.calls = []

    def get(self, path):
        self.calls.append(path)
        return copy.deepcopy(self.responses[len(self.calls) - 1])


class TeamMembershipTests(unittest.TestCase):
    def test_versioned_contract_does_not_claim_live_acceptance(self):
        contract = json.loads((Path(__file__).resolve().parents[1] /
            "workflows/contracts/m365-team-matter-read.contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["team_id"], TEAM_ID)
        self.assertEqual(contract["access_mode"], "team_member")
        self.assertEqual(contract["role"], "team_reader")
        self.assertEqual(contract["live_acceptance"]["status"], "NOT_EXECUTED")
        self.assertTrue(contract["live_acceptance"]["current_nonmember_denial_required"])
        for key in ("individual_assignment_required", "positive_membership_cache_allowed",
                    "membership_grants_professional_role", "membership_grants_write_approval_or_deputy",
                    "cross_team_access_allowed", "pagination_allowed"):
            self.assertIs(contract[key], False)

    def test_transport_only_accepts_three_fixed_membership_edges(self):
        for path in MEMBERSHIP_PATHS:
            _validate_relative_graph_path(path)
        for path in ("/groups/other", "/users", *[p + "&extra=true" for p in MEMBERSHIP_PATHS]):
            with self.subTest(path=path), self.assertRaises(ValueError):
                _validate_relative_graph_path(path)

    def test_member_request_does_not_use_advanced_eventual_index(self):
        client = Client()
        self.assertTrue(FixedTeamMembership(client).contains(ACTOR))
        self.assertIn("/members?", client.calls[-1])
        self.assertNotIn("microsoft.graph.user", client.calls[-1])
        self.assertNotIn("count", client.calls[-1])

    def test_scope_mismatch_stops_before_provider(self):
        arguments = dict(actor_id=ACTOR, tenant_id="tenant:test", workspace_id=ALLOWED_WORKSPACE_ID,
                         matter_id=ALLOWED_MATTER_ID, purpose=ALLOWED_PURPOSE)
        for field in ("workspace_id", "matter_id", "purpose"):
            client = Client()
            decision = TeamReadAccessDecisionAdapter(client, expected_tenant_id="tenant:test").decide(
                **dict(arguments, **{field: "other"}))
            self.assertEqual(decision.mode.value, "deny")
            self.assertEqual(client.calls, [])

    def test_member_cannot_read_a_case_of_another_team(self):
        client = Client()
        client.responses.append({"value": [{"id": "1", "fields": {
            "NacCaseId": ALLOWED_MATTER_ID, "NotarTeam": "NaC-Notar-02"}}]})
        decision = TeamReadAccessDecisionAdapter(client, expected_tenant_id="tenant:test").decide(
            actor_id=ACTOR, tenant_id="tenant:test", workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID, purpose=ALLOWED_PURPOSE)
        self.assertEqual(decision.mode.value, "deny")

    def test_read_access_needs_no_person_mapping_or_assignment(self):
        client = Client()
        client.responses.append({"value": [{"id": "1", "fields": {"NacCaseId": ALLOWED_MATTER_ID, "NotarTeam": "NaC-Notar-01"}}]})
        port = TeamReadAccessDecisionAdapter(client, expected_tenant_id="tenant:test", reference_time="2026-10-03T10:00:00Z")
        decision = port.decide(actor_id=ACTOR, tenant_id="tenant:test", workspace_id=ALLOWED_WORKSPACE_ID, matter_id=ALLOWED_MATTER_ID, purpose=ALLOWED_PURPOSE)
        self.assertEqual(decision.mode.value, "team_member")
        self.assertEqual(decision.role, "team_reader")
        self.assertFalse(decision.active_approved_grant)

    def test_wrong_tenant_needs_no_provider_read(self):
        client = Client()
        decision = TeamReadAccessDecisionAdapter(client, expected_tenant_id="tenant:test").decide(actor_id=ACTOR, tenant_id="tenant:other", workspace_id=ALLOWED_WORKSPACE_ID, matter_id=ALLOWED_MATTER_ID, purpose=ALLOWED_PURPOSE)
        self.assertEqual(decision.mode.value, "deny")
        self.assertEqual(client.calls, [])

    def test_member_requires_exact_group_and_site(self):
        client = Client()
        self.assertTrue(FixedTeamMembership(client).contains(ACTOR))
        self.assertEqual(len(client.calls), 3)

    def test_nonmember_denied(self):
        client = Client()
        client.responses[2] = {"value": []}
        self.assertFalse(FixedTeamMembership(client).contains(ACTOR))

    def test_malformed_and_partial_evidence_denied(self):
        changes = [
            (0, {"id": ACTOR, "groupTypes": ["Unified"], "resourceProvisioningOptions": ["Team"]}),
            (1, {"id": "other", "webUrl": "https://funktion8.sharepoint.com/sites/NaC-Notar-01"}),
            (2, {"value": [{"id": ACTOR}], "@odata.nextLink": "https://graph.microsoft.com/v1.0/other"}),
            (2, {"value": [{"id": ACTOR}, {"id": ACTOR}]}),
            (2, {"value": [{"id": "invalid"}]}),
        ]
        for index, response in changes:
            with self.subTest(response=response):
                client = Client()
                client.responses[index] = response
                self.assertFalse(FixedTeamMembership(client).contains(ACTOR))

    def test_invalid_subject_makes_no_request(self):
        for subject in ("", "actor:browser", "../../users", None):
            client = Client()
            self.assertFalse(FixedTeamMembership(client).contains(subject))
            self.assertEqual(client.calls, [])

    def test_removal_is_not_cached(self):
        client = Client()
        port = FixedTeamMembership(client)
        self.assertTrue(port.contains(ACTOR))
        client.calls.clear()
        client.responses[2] = {"value": []}
        self.assertFalse(port.contains(ACTOR))


if __name__ == "__main__":
    unittest.main()
