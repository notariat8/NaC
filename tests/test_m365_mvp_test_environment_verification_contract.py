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
CURRENT_ACCEPTANCE_PATH = (
    ROOT / "workflows/verification-contracts/evidence/"
    "m365-mvp-current-state-acceptance.redacted.json"
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


CURRENT_REQUIRED_CHECKS = {
    "AC-620-01": ["package_manifest", "current_package_deployment_binding"],
    "AC-620-02": ["bff_only_package_scope", "installed_package_source_binding"],
    "AC-620-03": ["current_identity_allowlist", "current_deployment_implementation_binding"],
    "AC-620-04": ["current_assigned_projection_bpmn", "current_valid_deputy", "current_teams_render", "current_sharepoint_render"],
    "AC-620-05": ["current_authenticated_denial", "unassigned_prestate", "current_tamper_matrix"],
    "AC-620-06": ["historical_deployment_write_cleanup", "current_release_input_readbacks", "current_readonly_convergence"],
    "AC-620-07": ["current_exact_permission_boundary", "no_unapproved_mutations"],
}
CURRENT_MUTATION_GUARDS = (
    "new_login_allowed", "token_refresh_allowed", "provider_write_allowed",
    "deployment_allowed", "permission_or_assignment_write_allowed",
    "automatic_retry_allowed", "issue_739_reconstruction_allowed",
)


def validate_current_acceptance(
    evidence: dict[str, object], contract: dict[str, object]
) -> list[str]:
    """Validate a redacted acceptance record, never execute or authorize a live run."""
    if not isinstance(evidence, dict) or not isinstance(contract, dict):
        return ["current evidence and contract must be objects"]
    errors: list[str] = []
    final = contract.get("final_bff_live_verification")
    if not isinstance(final, dict):
        return ["current acceptance contract must be an object"]
    if final.get("required_checks_by_ac") != CURRENT_REQUIRED_CHECKS:
        errors.append("all reviewed acceptance checks must remain required")
    for key in CURRENT_MUTATION_GUARDS:
        if final.get(key) is not False:
            errors.append(f"current acceptance {key} must remain false")
    if contract.get("target_boundary", {}).get("exact_owner_gated_binding_create_or_reuse_allowed") is not False:
        errors.append("current target boundary must not permit binding creation")
    if contract.get("permission_boundary_supersession", {}).get("applies_to_exact") != "historical_issue_632_activation_only":
        errors.append("permission supersession must remain historical only")
    if final.get("issue_632_activation_required") is not False:
        errors.append("historical activation must not be required for current acceptance")
    historical = final.get("historical_activation", {})
    if not isinstance(historical, dict):
        return errors + ["historical activation must remain a separate object"]
    if historical.get("rerun_allowed") is not False or historical.get("issue_739_terminal_state_exact") != "FUNCTION_DEPLOYMENT_PROVENANCE_LOST":
        errors.append("terminal historical activation must not be replayed or reconstructed")

    expected_keys = {
        "schema_version", "leading_issue", "recorded_on", "status",
        "complete_mvp_acceptance", "scope", "sources", "criteria",
        "observation_limits", "redaction",
    }
    if set(evidence) != expected_keys:
        errors.append("current evidence must use the closed redacted schema")
    if evidence.get("schema_version") != "nac.m365-mvp-current-state-acceptance/v0.1":
        errors.append("current evidence schema version mismatch")
    if evidence.get("leading_issue") != contract.get("leading_issue"):
        errors.append("current evidence must bind the leading Issue #620")
    if evidence.get("scope") != {
        "workspace_id": "notary_team_01", "matter_id": "NAC-SYN-MATTER-001",
        "data_class": "synthetic_only", "mode": "current_state_read_only_reconciliation",
    }:
        errors.append("current evidence scope must remain exact")
    if type(evidence.get("status")) is not str or evidence.get("status") not in {"INCOMPLETE", "PASSED"} or evidence.get("status") != final.get("status_exact"):
        errors.append("current evidence and contract status must match")
    if type(evidence.get("complete_mvp_acceptance")) is not bool:
        errors.append("complete acceptance must be a boolean")
    if not isinstance(evidence.get("recorded_on"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", evidence["recorded_on"]):
        errors.append("current evidence requires a redacted record date")

    sources = evidence.get("sources")
    if not isinstance(sources, dict):
        return errors + ["current sources must be an object"]
    # These are reviewed source references, not arbitrary callback URLs or raw receipts.
    reviewed_sources = {
        "historical": ("historical_live_attestation", {"kind", "path", "sha256", "recorded_on"}),
        "implementation": ("repository_inspection", {"kind", "commit", "tree", "recorded_on"}),
        "package": ("local_package_inspection", {"kind", "sha256", "version", "not_a_live_upload_receipt", "recorded_on"}),
        "positive": ("current_live_receipt", {"kind", "url", "recorded_on"}),
        "negative": ("current_live_receipt", {"kind", "url", "recorded_on"}),
        "teams": ("current_host_observation", {"kind", "url", "recorded_on"}),
    }
    if set(sources) != set(reviewed_sources):
        errors.append("current evidence sources must remain reviewed and closed")
    invalid_source = False
    for source_id, (kind, keys) in reviewed_sources.items():
        source = sources.get(source_id)
        if not isinstance(source, dict) or set(source) != keys or source.get("kind") != kind:
            errors.append(f"invalid reviewed source {source_id}")
            invalid_source = True
            continue
        if not isinstance(source.get("recorded_on"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["recorded_on"]):
            errors.append(f"invalid source date {source_id}")
    if invalid_source:
        return errors
    old = sources.get("historical", {})
    if old.get("path") != LIVE_EVIDENCE_PATH.relative_to(ROOT).as_posix() or old.get("sha256") != EXPECTED_LIVE_BINDING["source_evidence_sha256_exact"]:
        errors.append("historical source must retain its original path and hash")
    for source_id, comment_id in (("positive", "5932777104"), ("negative", "5934493891"), ("teams", "5918874200")):
        if sources.get(source_id, {}).get("url") != f"https://github.com/notariat8/NaC/issues/620#issuecomment-{comment_id}":
            errors.append(f"current receipt URL mismatch for {source_id}")
    if sources.get("package", {}).get("not_a_live_upload_receipt") is not True:
        errors.append("local package inspection must not become a deployment receipt")
    if not re.fullmatch(r"[0-9a-f]{64}", str(sources.get("package", {}).get("sha256", ""))):
        errors.append("local package inspection requires a redacted exact SHA-256")
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", str(sources.get("package", {}).get("version", ""))):
        errors.append("local package version must be a closed version string")
    for key in ("commit", "tree"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(sources.get("implementation", {}).get(key, ""))):
            errors.append(f"repository source {key} must be an exact Git binding")
        if sources.get("implementation", {}).get(key) != final.get(f"observed_runtime_source_{key}_exact"):
            errors.append(f"repository source {key} must bind the observed runtime source")

    criteria = evidence.get("criteria")
    if not isinstance(criteria, list) or [item.get("id") if isinstance(item, dict) else None for item in criteria] != ACCEPTANCE_IDS:
        return errors + ["all seven ordered acceptance criteria must be present exactly once"]
    required_sources = {
        "package_manifest": {"implementation", "package"},
        "bff_only_package_scope": {"implementation", "package"},
        "current_identity_allowlist": {"positive", "implementation"},
        "current_assigned_projection_bpmn": {"positive"},
        "current_teams_render": {"teams"},
        "current_authenticated_denial": {"negative"},
        "current_tamper_matrix": {"positive"},
        "historical_deployment_write_cleanup": {"historical"},
        "no_unapproved_mutations": {"positive", "negative"},
    }
    has_open = False
    for item in criteria:
        if set(item) != {"id", "checks"} or not isinstance(item.get("checks"), dict):
            errors.append("each criterion must contain only id and closed checks")
            continue
        checks = item["checks"]
        if list(checks) != CURRENT_REQUIRED_CHECKS[item["id"]]:
            errors.append(f"missing, reordered or unexpected checks in {item['id']}")
        for check_id, check in checks.items():
            if not isinstance(check, dict) or set(check) != {"status", "sources"} or type(check.get("status")) is not str or check.get("status") not in {"VERIFIED", "OPEN"} or not isinstance(check.get("sources"), list):
                errors.append(f"invalid check {check_id}")
                continue
            if check["status"] == "OPEN":
                has_open = True
                if check["sources"]:
                    errors.append(f"open check {check_id} cannot claim evidence")
            elif check_id not in required_sources or any(not isinstance(value, str) for value in check["sources"]) or set(check["sources"]) != required_sources[check_id]:
                errors.append(f"unreviewed, historical or insufficient source for {check_id}")
    if has_open and (evidence.get("status") != "INCOMPLETE" or evidence.get("complete_mvp_acceptance") is not False):
        errors.append("open evidence must remain INCOMPLETE and cannot claim PASSED")
    if not has_open and (evidence.get("status") != "PASSED" or evidence.get("complete_mvp_acceptance") is not True):
        errors.append("complete evidence and result must agree")
    limits = evidence.get("observation_limits")
    expected_limits = {
        "authenticated_denial_does_not_prove_unassigned_prestate": True,
        "historical_deputy_does_not_prove_current_valid_deputy": True,
        "host_observation_requires_separate_release_version_binding": True,
        "local_package_hash_does_not_prove_live_upload": True,
        "offline_candidate_or_fixture_is_not_live_release_evidence": True,
        "sdk_timeout_does_not_prove_authentication_failure": True,
        "historical_activation_passthrough_or_reconstruction_allowed": False,
    }
    if limits != expected_limits or not isinstance(limits, dict) or any(type(value) is not bool for value in limits.values()):
        errors.append("observation limits must remain explicit and fail closed")
    redaction = evidence.get("redaction")
    if redaction != {
        "accounts_or_principal_ids_included": False, "tenant_or_user_ids_included": False,
        "authentication_contents_included": False, "raw_provider_responses_included": False,
        "personal_or_mandate_data_included": False,
    } or not isinstance(redaction, dict) or any(type(value) is not bool for value in redaction.values()):
        errors.append("current evidence redaction boundary must remain exact")
    return errors


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

    def test_current_acceptance_is_separate_from_historical_activation(self) -> None:
        final = self.contract["final_bff_live_verification"]
        self.assertEqual(final["status_exact"], "INCOMPLETE")
        self.assertEqual(final["leading_issue_exact"], self.contract["leading_issue"])
        self.assertEqual(
            final["runner_exact"],
            "bounded current-state read-only acceptance reconciliation",
        )
        self.assertFalse(final["issue_632_activation_required"])
        self.assertEqual(
            self.contract["failure_behavior"]["readback_or_role_mismatch"],
            "INCOMPLETE_without_cleanup_mutation",
        )
        self.assertFalse(
            self.contract["historical_data_plane_failure_behavior"]["grants_current_write_authority"]
        )
        self.assertEqual(
            self.contract["deployment_control_plane"]["applies_to_exact"],
            "historical_deployment_only_not_current_acceptance",
        )
        self.assertTrue(final["all_acceptance_checks_required"])
        self.assertFalse(final["remote_built_binary_digest_required"])
        self.assertTrue(final["causal_deployment_input_and_readbacks_required"])
        for key in (
            "new_login_allowed", "token_refresh_allowed", "provider_write_allowed",
            "deployment_allowed", "permission_or_assignment_write_allowed",
            "automatic_retry_allowed", "issue_739_reconstruction_allowed",
        ):
            self.assertIs(final[key], False)
        historical = final["historical_activation"]
        self.assertEqual(historical["latest_attempt_result_exact"], "FAILED_PARTIAL")
        self.assertFalse(historical["passed_attestation_present"])
        self.assertFalse(historical["rerun_allowed"])
        self.assertEqual(
            historical["issue_739_terminal_state_exact"],
            "FUNCTION_DEPLOYMENT_PROVENANCE_LOST",
        )

    def test_current_evidence_is_hash_bound_and_remains_incomplete(self) -> None:
        evidence = json.loads(CURRENT_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        final = self.contract["final_bff_live_verification"]
        self.assertEqual(
            hashlib.sha256(CURRENT_ACCEPTANCE_PATH.read_bytes()).hexdigest(),
            final["evidence_sha256_exact"],
        )
        self.assertEqual(validate_current_acceptance(evidence, self.contract), [])
        self.assertEqual(evidence["status"], "INCOMPLETE")
        self.assertFalse(evidence["complete_mvp_acceptance"])
        self.assertEqual([item["id"] for item in evidence["criteria"]], ACCEPTANCE_IDS)

    def test_current_acceptance_rejects_passed_with_open_or_missing_checks(self) -> None:
        evidence = json.loads(CURRENT_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda value: value.update(status="PASSED", complete_mvp_acceptance=True),
            lambda value: value["criteria"].pop(),
            lambda value: value["criteria"][0]["checks"].pop("package_manifest"),
            lambda value: value["criteria"][4]["checks"].update(
                unexpected_inventory={"status": "VERIFIED", "sources": ["negative"]}
            ),
        ):
            with self.subTest(mutation=mutate):
                altered = copy.deepcopy(evidence)
                mutate(altered)
                self.assertNotEqual(validate_current_acceptance(altered, self.contract), [])

    def test_current_acceptance_rejects_scope_source_and_redaction_drift(self) -> None:
        evidence = json.loads(CURRENT_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda value: value["scope"].update(workspace_id="other"),
            lambda value: value["sources"]["historical"].update(sha256="0" * 64),
            lambda value: value["sources"]["negative"].update(url="https://example.org"),
            lambda value: value.update(account="person@example.org"),
            lambda value: value["criteria"][3]["checks"]["current_valid_deputy"].update(
                status="VERIFIED", sources=["historical"]
            ),
            lambda value: value["criteria"][4]["checks"]["unassigned_prestate"].update(
                status="VERIFIED", sources=["negative"]
            ),
        ):
            with self.subTest(mutation=mutate):
                altered = copy.deepcopy(evidence)
                mutate(altered)
                self.assertNotEqual(validate_current_acceptance(altered, self.contract), [])

    def test_current_acceptance_requires_live_authority_not_an_sdk_timeout(self) -> None:
        evidence = json.loads(CURRENT_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        for key in ("provider_write_allowed", "token_refresh_allowed", "issue_739_reconstruction_allowed"):
            with self.subTest(key=key):
                altered_contract = copy.deepcopy(self.contract)
                altered_contract["final_bff_live_verification"][key] = True
                self.assertNotEqual(validate_current_acceptance(evidence, altered_contract), [])

    def test_current_acceptance_rejects_malformed_types_and_runtime_drift(self) -> None:
        evidence = json.loads(CURRENT_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda value: value.update(status=[]),
            lambda value: value["sources"].update(negative=[]),
            lambda value: value["sources"]["implementation"].update(commit="0" * 40),
            lambda value: value["sources"]["package"].update(version="person@example.org"),
            lambda value: value["redaction"].update(authentication_contents_included=0),
            lambda value: value["criteria"][0]["checks"]["package_manifest"].update(status=[]),
        ):
            with self.subTest(mutation=mutate):
                altered = copy.deepcopy(evidence)
                mutate(altered)
                self.assertNotEqual(validate_current_acceptance(altered, self.contract), [])

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

    def test_historical_live_attestation_excludes_bff_and_token_validation(self) -> None:
        self.assertEqual(
            self.contract["final_bff_live_verification"]["historical_activation"]["latest_attempt_result_exact"],
            "FAILED_PARTIAL",
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

    def test_mvp_plans_preserve_historical_632_and_current_incomplete_acceptance(self) -> None:
        for path in (DE_PLAN, EN_PLAN):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("DEFERRED", text)
                self.assertIn("#632", text)
                self.assertIn("INCOMPLETE", text)
                self.assertIn("FUNCTION_DEPLOYMENT_PROVENANCE_LOST", text)
                self.assertIn("m365-mvp-current-state-acceptance.redacted.json", text)

    def test_current_acceptance_does_not_authorize_historical_activation_steps(self) -> None:
        mutating_steps = (
            "register_azure_providers",
            "ensure_resource_group",
            "ensure_entra_api_application",
            "deploy_bicep_baseline",
            "assign_sites_selected",
            "grant_target_site_read",
            "deploy_function_package",
            "build_and_deploy_spfx",
            "approve_spfx_bff_scope",
            "seed_synthetic_workspace",
        )
        sections = (
            (DE_PLAN, "## Aktuelle Read-only-Abnahme"),
            (EN_PLAN, "## Current Read-only Acceptance"),
        )
        for path, start in sections:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                section = text.split(start, 1)[1].split("\n## ", 1)[0]
                self.assertIn("AC-620-01", text)
                for step in mutating_steps:
                    self.assertNotIn(f"(`{step}`)", section)
                self.assertIn("read-only", section.lower())

    def test_current_acceptance_is_visible_in_gantts_without_a_new_activation(self) -> None:
        for path in (ROADMAP_GANTT, WORKFLOWS_GANTT):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("BFF `DEFERRED`", text)
                self.assertIn("Read-only-Abnahme", text)
                self.assertNotIn("aktuellen zwölfstufigen Abschlusslauf", text)

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
                "read-only acceptance",
            ),
            "AC-620-03": (
                "validated Entra access token",
                "server-side allowlist",
                "current live token validation evidence",
            ),
            "AC-620-04": (
                "assigned user",
                "redacted projection",
                "status, tasks, due date and BPMN",
                "current valid-deputy decision",
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
                "no credential or unbounded permission",
                "bounded Issue #632 supersession",
                "historical only",
                "authorizes no create, approve, role or assignment write",
                "fails closed without in-place repair",
                "Matter.Read",
                "runtime Sites.Selected with site role read",
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
            package["delegated_api_activation_status_exact"],
            "CURRENT_READ_OBSERVED_ACCEPTANCE_INCOMPLETE",
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

    def test_current_acceptance_preserves_exact_permissions_without_mutations(self) -> None:
        bff = self.contract["bff_boundary"]
        self.assertEqual(
            bff["dynamic_path_exact"],
            "SPFx/Teams -> NaC BFF -> Microsoft Graph REST v1.0",
        )
        self.assertEqual(
            bff["live_activation_status_exact"], "CURRENT_READ_OBSERVED_ACCEPTANCE_INCOMPLETE"
        )
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
                "provisioned_public_https_endpoint",
                "provisioned_delegated_entra_scope",
            ],
        )
        self.assertFalse(
            bff["new_permission_scope_or_credential_change_allowed_in_slice"]
        )
        supersession = self.contract["permission_boundary_supersession"]
        self.assertEqual(supersession["applies_to_exact"], "historical_issue_632_activation_only")
        self.assertEqual(supersession["scope_exact"], "Matter.Read")
        self.assertEqual(
            supersession["runtime_graph_permission_exact"], "Sites.Selected"
        )
        self.assertEqual(supersession["runtime_site_role_exact"], "read")
        self.assertFalse(supersession["credential_change_allowed"])
        self.assertTrue(
            supersession[
                "exact_create_or_reuse_allowed_in_closure_run"
            ]
        )
        self.assertFalse(supersession["in_place_permission_repair_allowed"])
        target = self.contract["target_boundary"]
        self.assertFalse(target["credential_changes_allowed"])
        self.assertFalse(target["unbounded_permission_changes_allowed"])
        self.assertFalse(
            target["exact_owner_gated_binding_create_or_reuse_allowed"]
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
