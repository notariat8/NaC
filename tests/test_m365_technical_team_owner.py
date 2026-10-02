from __future__ import annotations

import copy
import unittest
from pathlib import Path

from tests.test_teams_sharepoint_graph_data_plane import (
    FakeGraphWriteClient,
    apply_privileged_change_path,
    build_application_owner_readiness,
    build_plan,
    load_privileged_applied_state,
    load_privileged_change_config,
    load_schema,
    validate_privileged_change_config,
    validate_schema,
    build_privileged_change_plan,
)
from nac_identity.customer_onboarding import build_customer_tenant_plan


OWNER_UPN = "funktion8@funktion8.de"


class OwnerClient(FakeGraphWriteClient):
    """Synthetic provider; no credentials, network or real tenant identifiers."""

    def __init__(self) -> None:
        super().__init__({"workspaces": [{
            "id": "notary_team_01", "team_id": "synthetic-team-01",
            "team_display_name": "Synthetic notary team", "site_id": "synthetic-site-01",
        }]})
        self.group_page = {"value": [{
            "@odata.type": "#microsoft.graph.user", "id": "technical-owner",
            "userPrincipalName": OWNER_UPN,
        }]}
        self.member_page = {"value": [{
            "@odata.type": "#microsoft.graph.aadUserConversationMember",
            "id": "synthetic-membership", "userId": "technical-owner", "roles": ["owner"],
        }, {
            "@odata.type": "#microsoft.graph.aadUserConversationMember",
            "id": "synthetic-person-membership", "userId": "synthetic-person", "roles": [],
        }]}

    def get(self, path: str) -> dict:
        if path.startswith("/groups/") and "/owners" in path:
            return copy.deepcopy(self.group_page)
        if path.startswith("/teams/") and "/members" in path:
            return copy.deepcopy(self.member_page)
        return super().get(path)


class TechnicalTeamOwnerTests(unittest.TestCase):
    def test_localized_documentation_links_policy_without_real_account_address(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for language in ("de", "en"):
            for relative in ("START_HERE.md", "architecture/teams-sharepoint-graph-data-plane.md",
                             "superpowers/specs/2026-10-02-technical-team-owner-design.md"):
                with self.subTest(language=language, relative=relative):
                    text = (root / "docs" / language / relative).read_text(encoding="utf-8")
                    self.assertFalse(OWNER_UPN in text, "Account address must remain in the canonical policy binding")
                    self.assertIn("policies/m365-team-ownership-policy.json", text)

    def setUp(self) -> None:
        self.config = load_privileged_change_config()

    def assert_blocked_before_write(self, client: OwnerClient, state: dict | None = None) -> None:
        with self.assertRaises(RuntimeError):
            apply_privileged_change_path(client, self.config, state or client.provisioned_state)
        self.assertEqual(client.posts, [])
        self.assertEqual(client.patches, [])

    def test_exact_technical_owner_passes_with_personal_member(self) -> None:
        client = OwnerClient()
        result = apply_privileged_change_path(client, self.config, client.provisioned_state)
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["teamOwnerChecks"][0]["technicalOwnerOnly"], True)

    def test_nonconforming_group_owner_sets_stop_before_write(self) -> None:
        extra = {"@odata.type": "#microsoft.graph.user", "id": "synthetic-person",
                 "userPrincipalName": "person@example.test"}
        for value in ([], [extra], [OwnerClient().group_page["value"][0], extra],
                      [OwnerClient().group_page["value"][0]] * 2,
                      [None], [{"id": "technical-owner"}],
                      [{"@odata.type": "#microsoft.graph.servicePrincipal", "id": "technical-owner",
                        "userPrincipalName": OWNER_UPN}]):
            with self.subTest(value=value):
                client = OwnerClient()
                client.group_page = {"value": value}
                self.assert_blocked_before_write(client)

    def test_nonconforming_team_roles_stop_before_write(self) -> None:
        for mutation in ("extra_owner", "missing_owner", "wrong_owner", "malformed_roles",
                         "duplicate_member", "non_user", "missing_user_id"):
            with self.subTest(mutation=mutation):
                client = OwnerClient()
                members = client.member_page["value"]
                if mutation == "extra_owner":
                    members[1]["roles"] = ["owner"]
                elif mutation == "missing_owner":
                    members[0]["roles"] = []
                elif mutation == "wrong_owner":
                    members[0]["userId"] = "synthetic-other"
                elif mutation == "malformed_roles":
                    members[1]["roles"] = "owner"
                elif mutation == "duplicate_member":
                    members.append(copy.deepcopy(members[0]))
                elif mutation == "non_user":
                    members[0]["@odata.type"] = "#microsoft.graph.conversationMember"
                else:
                    del members[0]["userId"]
                self.assert_blocked_before_write(client)

    def test_incomplete_or_paginated_owner_responses_fail_closed(self) -> None:
        for page in ({}, {"value": "malformed"},
                     {"value": [], "@odata.nextLink": "https://example.test/owners"},
                     {"value": [], "@odata.nextLink": "/groups/synthetic-team-01/owners"}):
            with self.subTest(page=page):
                client = OwnerClient()
                client.group_page = page
                self.assert_blocked_before_write(client)

    def test_incomplete_team_member_evidence_stops_before_write(self) -> None:
        for page in ({}, {"value": None}, {"value": [None]},
                     {"value": [], "@odata.nextLink": "https://example.test/members"}):
            with self.subTest(page=page):
                client = OwnerClient()
                client.member_page = page
                self.assert_blocked_before_write(client)

    def test_second_target_failure_precedes_all_writes(self) -> None:
        client = OwnerClient()
        second = {**client.provisioned_state["workspaces"][0], "id": "notary_team_02",
                  "team_id": "synthetic-team-02", "site_id": "synthetic-site-02"}
        client.provisioned_state["workspaces"].append(second)
        original_get = client.get

        def second_target_failure(path: str) -> dict:
            if path.startswith("/teams/synthetic-team-02/members"):
                return {"value": []}
            return original_get(path)

        client.get = second_target_failure
        self.assert_blocked_before_write(client)

    def test_missing_or_duplicate_target_teams_fail_closed(self) -> None:
        for workspaces in ([], [None], [{"id": "notary_team_01"}],
                           OwnerClient().provisioned_state["workspaces"] * 2):
            with self.subTest(workspaces=workspaces):
                self.assert_blocked_before_write(OwnerClient(), {"workspaces": workspaces})

    def test_returned_technical_user_upn_is_bound(self) -> None:
        client = OwnerClient()
        original_get = client.get

        def spoofed_user(path: str) -> dict:
            if path.startswith("/users?"):
                return {"value": [{"id": "technical-owner", "userPrincipalName": "other@example.test"}]}
            return original_get(path)

        client.get = spoofed_user
        self.assert_blocked_before_write(client)

    def test_malformed_owner_license_metadata_stops_before_write(self) -> None:
        for licenses in (None, 5, "m365", [None], ["m365"]):
            with self.subTest(licenses=licenses):
                client = OwnerClient()
                original_get = client.get

                def malformed_user(path: str) -> dict:
                    if path.startswith("/users?"):
                        return {"value": [{"id": "technical-owner", "userPrincipalName": OWNER_UPN,
                                           "assignedLicenses": licenses}]}
                    return original_get(path)

                client.get = malformed_user
                self.assert_blocked_before_write(client)

    def test_creation_plan_binds_only_the_technical_owner(self) -> None:
        teams = [op for op in build_plan(load_schema()) if op.action == "ensure_team"]
        for operation in teams:
            self.assertEqual(operation.payload["members"], [{
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{OWNER_UPN}')",
            }])

    def test_creation_schema_rejects_personal_or_implicit_owners(self) -> None:
        for value in (None, {}, {"technical_owner_user_principal_name": "person@example.test"},
                      {"sole_team_owner_required": 1}):
            with self.subTest(value=value):
                schema = load_schema()
                schema["team_ownership"] = value
                self.assertTrue(validate_schema(schema))
                with self.assertRaises(ValueError):
                    build_plan(schema)

    def test_privileged_plan_checks_all_owners_before_first_write(self) -> None:
        operations = build_privileged_change_plan(self.config, OwnerClient().provisioned_state)
        first_write = next(i for i, op in enumerate(operations) if op.graph_method != "GET")
        self.assertEqual({op.action for op in operations[:first_write]}, {
            "resolve_technical_owner_user", "verify_delegated_technical_owner",
            "verify_technical_group_owner", "verify_technical_team_owner",
        })

    def test_customer_plan_does_not_promote_admin_to_team_owner(self) -> None:
        plan = build_customer_tenant_plan(domain="example.test", tenant_slug="synthetic-notary",
                                         admin_email="admin@example.test", saas_admin_email="saas@example.test")
        self.assertEqual(plan["m365"]["workspace"]["technical_owner_user_principal_name"], OWNER_UPN)
        self.assertEqual(plan["m365"]["workspace"]["standard_user_team_role"], "member")

    def test_conflicting_old_owner_policy_is_rejected(self) -> None:
        config = copy.deepcopy(self.config)
        config["team_owner_policy"]["licensed_human_team_owner_required"] = True
        self.assertTrue(validate_privileged_change_config(config))

    def test_historical_owner_evidence_cannot_prove_current_readiness(self) -> None:
        result = build_application_owner_readiness(self.config, load_privileged_applied_state())
        self.assertFalse(result["summary"]["historical_applied_state_operationally_accepted"])
        check = next(c for c in result["checks"] if c["id"] == "current_team_ownership_unverified")
        self.assertEqual(check["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_historical_license_count_does_not_prove_terms_review(self) -> None:
        state = load_privileged_applied_state()
        state["technical_owner_user"]["assigned_license_count"] = 1
        result = build_application_owner_readiness(self.config, state)
        check = next(c for c in result["checks"] if c["id"] == "technical_owner_license_terms_review")
        self.assertEqual(check["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
