from __future__ import annotations

import copy
import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "workflows/contracts/m365-mvp-test-environment.verification.contract.json"
)
LIVE_ATTESTATION_PATH = (
    ROOT
    / "workflows/verification-contracts/m365-mvp-test-environment-live.verification.json"
)
LIVE_EVIDENCE_PATH = (
    ROOT
    / "workflows/verification-contracts/evidence/"
    "m365-mvp-test-environment-deploy.redacted.json"
)
DE_TARGET_PLAN = (
    ROOT
    / "docs/de/superpowers/plans/2026-07-11-microsoft-first-onprem-target-architecture.md"
)
EN_TARGET_PLAN = (
    ROOT
    / "docs/en/superpowers/plans/2026-07-11-microsoft-first-onprem-target-architecture.md"
)
ROADMAP_GANTT = ROOT / "roadmap/GANTT.md"
WORKFLOWS_GANTT = ROOT / "workflows/GANTT.md"
DE_SPEC = (
    ROOT
    / "docs/de/superpowers/specs/2026-07-13-m365-mvp-test-environment-design.md"
)
EN_SPEC = (
    ROOT
    / "docs/en/superpowers/specs/2026-07-13-m365-mvp-test-environment-design.md"
)
DE_PLAN = (
    ROOT
    / "docs/de/superpowers/plans/2026-07-13-m365-mvp-test-environment.md"
)
EN_PLAN = (
    ROOT
    / "docs/en/superpowers/plans/2026-07-13-m365-mvp-test-environment.md"
)
ACCEPTANCE_IDS = [f"AC-620-{number:02d}" for number in range(1, 8)]
EXPECTED_LIVE_BINDING = {
    "source_evidence_sha256_exact": (
        "65f0276a248f533e95caf35b63bc3c402108226734bf3f939d85a7cddbc9c1ea"
    ),
    "correlation_reference_sha256_exact": (
        "71c65e747ecec83ce97879f44a84a5692da68730a6e614fce6fa7e4ab1bf3b50"
    ),
    "package_sha256_exact": (
        "0c83b65bad8c690387d116213cfeb41c40e2c8cc3ba7c9b7b8f8cdf3d8439989"
    ),
}
EXPECTED_VERIFIED_CLAIMS = [
    "site-scoped SPFx/Heft package and App Catalog deployment gate",
    "shared SharePoint and Teams package gate",
    "synthetic matter status, two tasks and UTC due date",
    "read-only bpmn-js viewer with BPMN instance binding",
    "raw Microsoft Graph REST v1.0 write and targeted readback",
    "assigned, valid-deputy and unauthorized role decisions",
    "run-owned cleanup",
    "no browser business logic, secrets, workflow timers or agentic runtime",
]
EXPECTED_NOT_VERIFIED = [
    "document pointer rendering",
    "bpmn-js lazy loading or code splitting",
    "live BFF activation",
    "live Entra token validation",
]


def validate_live_attestation(
    attestation: dict[str, object], contract: dict[str, object]
) -> list[str]:
    errors: list[str] = []
    live = contract.get("live_verification")
    if not isinstance(live, dict):
        return ["contract live_verification must be an object"]

    expected_top_level = {
        "schema_version": "nac.verification-contract/v0.1",
        "contract_id": "verification.m365_mvp_test_environment_live_attestation",
        "domain_contract_id": "verification.m365_mvp_test_environment",
        "artifact_kind": "redacted_live_attestation",
        "attestation_version": "1.0.0",
        "status": "PASSED",
        "leading_issue": "https://github.com/notariat8/NaC/issues/620",
        "source_contract_path": (
            "workflows/contracts/"
            "m365-mvp-test-environment.verification.contract.json"
        ),
    }
    for key, expected in expected_top_level.items():
        if attestation.get(key) != expected:
            errors.append(f"attestation {key} must equal {expected!r}")

    expected_scope = {
        "execution_mode_exact": "Live-One-Shot",
        "workspace_id_exact": "notary_team_01",
        "data_class_exact": "synthetic_only",
        "source_evidence_retained_in_repo": True,
        "source_evidence_path_exact": (
            "workflows/verification-contracts/evidence/"
            "m365-mvp-test-environment-deploy.redacted.json"
        ),
    }
    if attestation.get("verification_scope") != expected_scope:
        errors.append("attestation verification_scope must match the reviewed scope")
    if attestation.get("verified_claims_exact") != EXPECTED_VERIFIED_CLAIMS:
        errors.append("attestation verified_claims_exact must match reviewed claims")
    if attestation.get("explicitly_not_verified_exact") != EXPECTED_NOT_VERIFIED:
        errors.append("attestation explicitly_not_verified_exact must remain exact")
    if live.get("workspace_id_exact") != expected_scope["workspace_id_exact"]:
        errors.append("contract workspace_id_exact must match the reviewed scope")
    if live.get("verified_capabilities_exact") != EXPECTED_VERIFIED_CLAIMS:
        errors.append("contract verified_capabilities_exact must match reviewed claims")
    if live.get("not_verified_exact") != EXPECTED_NOT_VERIFIED:
        errors.append("contract not_verified_exact must remain exact")

    result_binding = attestation.get("result_binding")
    if not isinstance(result_binding, dict):
        errors.append("attestation result_binding must be an object")
        return errors
    if result_binding.get("result_exact") != "PASSED":
        errors.append("attestation result_binding.result_exact must be PASSED")

    sha256_pattern = re.compile(r"^[0-9a-f]{64}$")
    for key, expected in EXPECTED_LIVE_BINDING.items():
        attested_value = result_binding.get(key)
        if attested_value != expected:
            errors.append(f"attestation {key} does not match the reviewed value")
        if not isinstance(attested_value, str) or not sha256_pattern.fullmatch(
            attested_value
        ):
            errors.append(f"attestation {key} must be lowercase SHA-256")
        if live.get(key) != attested_value:
            errors.append(f"contract and attestation disagree on {key}")

    expected_pull_request = {
        "number_exact": 628,
        "url_exact": "https://github.com/notariat8/NaC/pull/628",
        "state_exact": "MERGED",
        "merge_commit_sha_exact": "5092999768bd7e0fde575a7fe40cc1c198ec1e6c",
    }
    if result_binding.get("pull_request") != expected_pull_request:
        errors.append("attestation must bind PASSED to merged PR #628")
    if live.get("pull_request_number_exact") != 628:
        errors.append("contract must bind live verification to PR #628")
    if live.get("pull_request_url_exact") != expected_pull_request["url_exact"]:
        errors.append("contract must bind live verification to the PR #628 URL")

    expected_attestation_path = (
        "workflows/verification-contracts/"
        "m365-mvp-test-environment-live.verification.json"
    )
    if live.get("attestation_path_exact") != expected_attestation_path:
        errors.append("contract must reference the versioned live attestation")
    if live.get("attestation_version_exact") != attestation.get(
        "attestation_version"
    ):
        errors.append("contract and attestation versions must match")
    if live.get("result_exact") != attestation.get("status"):
        errors.append("contract PASSED result must be bound to attestation status")

    required_redaction = {
        "redacted": True,
        "hashes_only_for_source_evidence_and_correlation_reference": True,
        "raw_source_evidence_included": False,
        "raw_correlation_reference_included": False,
        "raw_graph_responses_included": False,
        "tokens_credentials_or_private_keys_included": False,
        "mandate_or_production_data_included": False,
    }
    if attestation.get("redaction") != required_redaction:
        errors.append("attestation redaction boundary is incomplete")

    pass_condition = attestation.get("pass_condition")
    if not isinstance(pass_condition, dict):
        errors.append("attestation pass_condition must be an object")
    else:
        for key in (
            "result_bound_to_all_three_sha256_values",
            "result_bound_to_merged_pull_request_628",
            "all_evidence_references_redacted",
            "bff_activation_remains_deferred",
            "live_entra_token_validation_remains_deferred",
        ):
            if pass_condition.get(key) is not True:
                errors.append(f"attestation pass_condition.{key} must be true")

    return errors


class M365MvpTestEnvironmentVerificationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.live_attestation = json.loads(
            LIVE_ATTESTATION_PATH.read_text(encoding="utf-8")
        )

    def test_live_attestation_validator_binds_passed_to_hashes_and_pr(self) -> None:
        self.assertEqual(
            validate_live_attestation(self.live_attestation, self.contract),
            [],
        )

    def test_versioned_live_evidence_rehashes_to_attested_sha256(self) -> None:
        self.assertTrue(LIVE_EVIDENCE_PATH.is_file())
        evidence_sha256 = hashlib.sha256(LIVE_EVIDENCE_PATH.read_bytes()).hexdigest()
        self.assertEqual(
            evidence_sha256,
            EXPECTED_LIVE_BINDING["source_evidence_sha256_exact"],
        )

    def test_live_attestation_rejects_scope_and_bff_claim_mutations(self) -> None:
        wrong_workspace = copy.deepcopy(self.live_attestation)
        wrong_workspace["verification_scope"]["workspace_id_exact"] = "other"
        self.assertNotEqual(validate_live_attestation(wrong_workspace, self.contract), [])

        false_bff_claim = copy.deepcopy(self.live_attestation)
        false_bff_claim["verified_claims_exact"].append("live BFF activation")
        false_bff_claim["explicitly_not_verified_exact"].remove(
            "live BFF activation"
        )
        self.assertNotEqual(validate_live_attestation(false_bff_claim, self.contract), [])

        wrong_contract = copy.deepcopy(self.contract)
        wrong_contract["live_verification"]["workspace_id_exact"] = "other"
        self.assertNotEqual(
            validate_live_attestation(self.live_attestation, wrong_contract), []
        )

        false_contract_bff_claim = copy.deepcopy(self.contract)
        false_contract_bff_claim["live_verification"][
            "verified_capabilities_exact"
        ].append("live BFF activation")
        false_contract_bff_claim["live_verification"]["not_verified_exact"].remove(
            "live BFF activation"
        )
        self.assertNotEqual(
            validate_live_attestation(self.live_attestation, false_contract_bff_claim),
            [],
        )

    def test_live_attestation_keeps_bff_and_token_validation_deferred(self) -> None:
        self.assertEqual(
            self.contract["bff_boundary"]["live_activation_status_exact"],
            "DEFERRED",
        )
        self.assertEqual(
            self.live_attestation["explicitly_not_verified_exact"][-2:],
            ["live BFF activation", "live Entra token validation"],
        )

    def test_slice_3_links_issue_contract_and_live_attestation(self) -> None:
        required_links = (
            "https://github.com/notariat8/NaC/issues/620",
            "../../../../workflows/contracts/"
            "m365-mvp-test-environment.verification.contract.json",
            "../../../../workflows/verification-contracts/"
            "m365-mvp-test-environment-live.verification.json",
        )
        for path in (DE_TARGET_PLAN, EN_TARGET_PLAN):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for link in required_links:
                    self.assertIn(link, text)

    def test_bff_deferred_state_is_not_auto_scheduled_in_gantts(self) -> None:
        gantt_row = re.compile(
            r"^\s+NaC-BFF-Live-Aktivierung DEFERRED\s+:",
            flags=re.MULTILINE,
        )
        for path in (ROADMAP_GANTT, WORKFLOWS_GANTT):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, gantt_row)
                self.assertIn("DEFERRED", text)

    def test_contract_binds_issue_scope_and_all_acceptance_ids(self) -> None:
        self.assertEqual(
            self.contract["leading_issue"],
            "https://github.com/notariat8/NaC/issues/620",
        )
        self.assertEqual(self.contract["spec_id"], "m365-mvp-test-environment")
        self.assertEqual(self.contract["acceptance_ids"], ACCEPTANCE_IDS)
        self.assertEqual(
            [item["id"] for item in self.contract["acceptance_criteria"]],
            ACCEPTANCE_IDS,
        )
        self.assertEqual(
            self.contract["target_boundary"]["workspace_id_exact"],
            "notary_team_01",
        )
        self.assertFalse(
            self.contract["target_boundary"]["other_workspaces_allowed"]
        )
        self.assertFalse(
            self.contract["target_boundary"]["production_data_allowed"]
        )

    def test_synthetic_fixture_uses_only_canonical_bpmn_and_kg_assets(self) -> None:
        fixture = self.contract["synthetic_fixture"]
        self.assertEqual(
            fixture["canonical_bpmn_source_path_exact"],
            "bpmn/immobilienkaufvertrag.bpmn",
        )
        self.assertEqual(
            fixture["canonical_bpmn_process_id_exact"],
            "Process_immobilienkaufvertrag",
        )
        self.assertEqual(
            fixture["canonical_bpmn_sha256_exact"],
            "02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0",
        )
        self.assertFalse(fixture["embedded_bpmn_allowed"])
        self.assertEqual(
            fixture["knowledge_graph_source_path_exact"],
            "usecases/immobilienkaufvertrag/knowledge-graph.graph.json",
        )
        self.assertEqual(
            fixture["knowledge_graph_schema_version_exact"],
            "nac.knowledge-graph/v0.1",
        )
        self.assertEqual(
            fixture["knowledge_graph_sha256_exact"],
            "3bd379066a3c9656046e930efca8d3c7690cdcbe5a7279f7aec12109e777e019",
        )
        self.assertTrue(fixture["task_bpmn_element_membership_required"])

    def test_issue_681_hardening_is_explicitly_traceable(self) -> None:
        self.assertEqual(
            self.contract["hardening_issues"],
            ["https://github.com/notariat8/NaC/issues/681"],
        )
        criteria = self.contract["hardening_acceptance_criteria"]
        self.assertEqual(
            [item["id"] for item in criteria],
            ["AC-681-01", "AC-681-02", "AC-681-03"],
        )
        requirements = " ".join(item["requirement"] for item in criteria)
        for phrase in (
            "no embedded BPMN",
            "canonical repository BPMN source, process, profile and SHA-256",
            "resolves exactly once",
            "nac:kgRef",
            "offline-only",
            "no tenant writes",
        ):
            self.assertIn(phrase, requirements)

    def test_acceptance_requirements_match_issue_620_semantics(self) -> None:
        requirements = {
            item["id"]: item["requirement"]
            for item in self.contract["acceptance_criteria"]
        }
        essential_phrases = {
            "AC-620-01": (
                "site-scoped and installable SPFx package",
                "SharePointWebPart and TeamsTab",
                "skipFeatureDeployment=false",
            ),
            "AC-620-02": (
                "never requests Microsoft Graph permissions",
                "delegated NaC BFF scope",
                "activation remains DEFERRED",
            ),
            "AC-620-03": (
                "validated Entra access token",
                "server-side allowlist",
                "live token validation remains DEFERRED",
            ),
            "AC-620-04": (
                "assigned user",
                "redacted projection",
                "status, tasks, due date and BPMN",
                "live BFF delivery path remains DEFERRED",
            ),
            "AC-620-05": (
                "Unassigned users",
                "workspace, matter, purpose or filter",
                "fail closed",
                "without revealing whether the matter exists",
            ),
            "AC-620-06": (
                "Site-scoped SharePoint and optional Teams deployment",
                "Graph REST v1.0 write/readback",
                "run-owned cleanup",
                "reproducible and redacted",
            ),
            "AC-620-07": (
                "no credential or permission",
                "no production data",
                "no operation in any workspace other than notary_team_01",
            ),
        }
        for acceptance_id, phrases in essential_phrases.items():
            with self.subTest(acceptance_id=acceptance_id):
                for phrase in phrases:
                    self.assertIn(phrase, requirements[acceptance_id])

    def test_contract_checks_cover_one_shot_deploy_and_runtime_bootstrap(self) -> None:
        checks = "\n".join(self.contract["checks"])
        self.assertIn("tests.test_m365_mvp_test_environment_deploy", checks)
        self.assertIn("tests.test_m365_runtime_env_bootstrap", checks)

    def test_spfx_is_site_scoped_graph_free_and_teams_capable(self) -> None:
        package = self.contract["ui_package"]
        self.assertEqual(package["framework_version_exact"], "1.23.2")
        self.assertEqual(package["deployment_scope_exact"], "site")
        self.assertFalse(package["skip_feature_deployment_exact"])
        self.assertEqual(package["graph_permission_requests_exact"], 0)
        self.assertFalse(package["direct_graph_from_spfx_allowed"])
        self.assertEqual(package["delegated_api_target_exact"], "NaC BFF")
        self.assertEqual(
            package["delegated_api_activation_status_exact"], "DEFERRED"
        )
        self.assertFalse(package["legacy_sharepoint_api_or_sdk_allowed"])
        self.assertEqual(
            set(package["hosts_required"]),
            {
                "SharePointWebPart",
                "SharePointFullPage",
                "TeamsTab",
                "TeamsPersonalApp",
            },
        )

    def test_graph_data_plane_fixture_and_cleanup_are_exact(self) -> None:
        data_plane = self.contract["data_plane"]
        fixture = self.contract["synthetic_fixture"]
        self.assertFalse(data_plane["browser_graph_calls_allowed"])
        self.assertEqual(
            data_plane["data_api_exact"],
            "raw Microsoft Graph REST v1.0",
        )
        self.assertFalse(data_plane["graph_beta_allowed"])
        self.assertFalse(data_plane["legacy_api_allowed"])
        self.assertTrue(data_plane["targeted_readback_required"])
        self.assertTrue(data_plane["run_owned_cleanup_required"])
        self.assertFalse(data_plane["foreign_or_preexisting_item_deletion_allowed"])
        deployment = self.contract["deployment_control_plane"]
        self.assertEqual(deployment["tool_exact"], "Microsoft 365 CLI")
        self.assertEqual(
            deployment["allowed_operations_exact"],
            [
                "deploy_spfx_package_to_app_catalog",
                "install_or_upgrade_app_on_exact_site",
                "publish_dedicated_page_and_webpart",
                "publish_or_install_teams_package_in_exact_team",
            ],
        )
        self.assertFalse(
            deployment["sharepoint_list_or_item_data_operations_allowed"]
        )
        self.assertFalse(
            deployment["permission_scope_or_credential_changes_allowed"]
        )
        self.assertFalse(deployment["tenant_wide_deployment_allowed"])
        self.assertEqual(fixture["task_count_exact"], 2)
        self.assertGreaterEqual(fixture["minimum_explicit_due_dates"], 1)
        self.assertEqual(
            fixture["role_scenarios_exact"],
            [
                "assigned_allow",
                "valid_deputy_allow",
                "unauthorized_deny_without_existence_leak",
            ],
        )

    def test_bff_activation_is_deferred_without_permission_changes(self) -> None:
        bff = self.contract["bff_boundary"]
        self.assertEqual(
            bff["dynamic_path_exact"],
            "SPFx/Teams -> NaC BFF -> Microsoft Graph REST v1.0",
        )
        self.assertEqual(bff["live_activation_status_exact"], "DEFERRED")
        self.assertEqual(
            bff["identity_source_exact"], "validated Entra access token claims"
        )
        self.assertEqual(
            bff["workspace_site_list_resolution_exact"],
            "server-side allowlist",
        )
        self.assertEqual(
            bff["activation_prerequisites"],
            [
                "existing_public_https_endpoint",
                "existing_delegated_entra_scope",
            ],
        )
        self.assertFalse(
            bff["new_permission_scope_or_credential_change_allowed_in_slice"]
        )

    def test_bilingual_specs_and_plans_share_traceability(self) -> None:
        for path in (DE_SPEC, EN_SPEC, DE_PLAN, EN_PLAN):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("https://github.com/notariat8/NaC/issues/620", text)
                self.assertIn("notary_team_01", text)
                for acceptance_id in ACCEPTANCE_IDS:
                    self.assertIn(acceptance_id, text)

        for path in (DE_SPEC, EN_SPEC):
            text = path.read_text(encoding="utf-8")
            block = re.search(
                r"```nac-spec-traceability\n(?P<body>.*?)\n```",
                text,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(block)
            assert block is not None
            self.assertIn("spec_id: m365-mvp-test-environment", block.group("body"))
            self.assertIn("delivery_mode: Protected PR", block.group("body"))


if __name__ == "__main__":
    unittest.main()
