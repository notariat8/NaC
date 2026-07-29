from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_business_case_type_graph_write_edge import (
    validate_domain_contract,
    validate_implementation,
    validate_verification_contract,
)


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeGraphWriteEdgeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.domain = json.loads(
            (
                ROOT
                / "workflows/contracts/business-case-type-graph-write-edge-s4b.contract.json"
            ).read_text(encoding="utf-8")
        )
        cls.verification = json.loads(
            (
                ROOT
                / "workflows/verification-contracts/business-case-type-graph-write-edge-s4b.verification.json"
            ).read_text(encoding="utf-8")
        )

    def test_contracts_and_implementation_pass_validator(self) -> None:
        self.assertEqual("implemented_offline", self.domain["status"])
        self.assertEqual("implemented_offline", self.verification["status"])
        self.assertEqual([], validate_domain_contract(copy.deepcopy(self.domain)))
        self.assertEqual(
            [], validate_verification_contract(copy.deepcopy(self.verification))
        )
        self.assertEqual([], validate_implementation())

    def test_offline_cli_contract_is_exact_and_bounded(self) -> None:
        self.assertEqual(
            {
                "command_exact": (
                    "nac m365 teams-sharepoint "
                    "business-case-type-write-dry-run"
                ),
                "operations_exact": [
                    "case_create",
                    "case_status_update",
                    "task_create",
                    "task_update",
                    "business_case_type_backfill",
                ],
                "synthetic_only": True,
                "redacted_output_only": True,
                "resource_identifiers_or_urls_in_output_allowed": False,
                "field_values_in_output_allowed": False,
                "live_factory_allowed": False,
                "credentials_allowed": False,
                "live_graph_calls_allowed": 0,
                "tenant_writes_allowed": 0,
            },
            self.domain["offline_cli"],
        )
        self.assertTrue(self.domain["offline_boundary"]["cli_changes_in_scope"])

    def test_offline_cli_contract_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["offline_cli"]["command_exact"] = (
            "nac m365 teams-sharepoint business-case-type-write"
        )
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["offline_cli"]["operations_exact"].remove("task_update")
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["offline_cli"]["live_graph_calls_allowed"] = 1
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["offline_cli"]["field_values_in_output_allowed"] = True
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["offline_boundary"]["cli_changes_in_scope"] = False
        self.assertTrue(validate_domain_contract(payload))

    def test_final_status_or_verification_adoption_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["status"] = "implemented_offline_pending_protected_pr"
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.verification)
        payload["status"] = "implemented_offline_pending_protected_pr"
        self.assertTrue(validate_verification_contract(payload))

        payload = copy.deepcopy(self.verification)
        payload["applies_when"]["paths"].remove("src/nac_cli/cli.py")
        self.assertTrue(validate_verification_contract(payload))

        payload = copy.deepcopy(self.verification)
        focused_check = next(
            check
            for check in payload["checks"]
            if check.startswith(
                "python3 -m unittest tests.test_business_case_type_graph_write_edge "
            )
        )
        payload["checks"].remove(focused_check)
        self.assertTrue(validate_verification_contract(payload))

    def test_review_safety_contract_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["evidence"]["persistent_state_key_exact"] = "mutation_id"
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["create_idempotency"][
            "dedupe_match_requires_fresh_item_readback_after_intent"
        ] = False
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["create_idempotency"][
            "http_409_requires_collection_dedupe_then_fresh_item_readback"
        ] = False
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["evidence"][
            "authorization_run_identity_components_exact"
        ] = ["approval_ref"]
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["evidence"][
            "retryable_same_execution_key_requires_distinct_authorization_run_identity"
        ] = False
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["error_handling"]["retryable_http_statuses_exact"].remove(429)
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["field_schema"]["boolean_as_text_or_integer_allowed"] = True
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["create_idempotency"]["dedupe_top_allowed"] = True
        self.assertTrue(validate_domain_contract(payload))

    def test_write_identity_cannot_drift_to_bff_read_identity(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["identity_boundary"]["write_site_grant_role_exact"] = "read"
        self.assertTrue(validate_domain_contract(payload))

    def test_graph_target_or_field_allowlist_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["operations"]["task_update"]["fields_allowed_exact"].append("Title")
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["operations"]["case_create"]["path_template"] = "/beta/sites/{site-id}"
        self.assertTrue(validate_domain_contract(payload))

    def test_etag_412_retry_or_s5_hash_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["concurrency"]["retry_on_412"] = True
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["s5_binding"]["operation_hash_required"] = False
        self.assertTrue(validate_domain_contract(payload))

    def test_evidence_order_or_offline_boundary_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["evidence"]["intent_before_write"] = False
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.verification)
        payload["thresholds"]["allowed_tenant_writes"] = 1
        self.assertTrue(validate_verification_contract(payload))

    def test_plan_integrity_or_paging_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["plan_integrity"]["canonical_revalidation_before_every_execute"] = False
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["create_idempotency"]["maximum_followed_pages"] = 1
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["binding"]["target_binding_hash_scope_fields_required_exact"].remove(
            "aufgaben_list_id"
        )
        self.assertTrue(validate_domain_contract(payload))

    def test_readback_persistence_or_error_redaction_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.domain)
        payload["readback"]["verified_not_applied_requires_valid_shape_and_actual_field_difference"] = False
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["evidence"]["authoritative_state_store_process_wide"] = False
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["evidence"]["reconciliation_clear_alone_sufficient"] = True
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["evidence"]["closure_proof_exact"] = "reconciliation_clear_only"
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["evidence"]["safe_start_intent_states_exact"].append("closed")
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["evidence"]["post_close_confirmation_failure_behavior"] = (
            "allow_fresh_process_replay"
        )
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["readback"]["patch_5xx_response_item_id_allowed"] = True
        self.assertTrue(validate_domain_contract(payload))

        payload = copy.deepcopy(self.domain)
        payload["error_handling"]["exception_type_message_url_body_or_headers_exposed"] = True
        self.assertTrue(validate_domain_contract(payload))

    def test_verification_safety_threshold_drift_is_rejected(self) -> None:
        payload = copy.deepcopy(self.verification)
        payload["thresholds"]["maximum_dedupe_pages_followed"] = 1
        self.assertTrue(validate_verification_contract(payload))

        payload = copy.deepcopy(self.verification)
        payload["failure_behavior"]["clear_with_open_intent"] = (
            "allow_when_reconciliation_is_clear"
        )
        self.assertTrue(validate_verification_contract(payload))

        payload = copy.deepcopy(self.verification)
        payload["failure_behavior"]["inactive_list_binding_drift"] = (
            "allow_for_inactive_list"
        )
        self.assertTrue(validate_verification_contract(payload))

        payload = copy.deepcopy(self.verification)
        payload["failure_behavior"]["post_close_confirmation_unavailable"] = (
            "allow_fresh_process_replay"
        )
        self.assertTrue(validate_verification_contract(payload))


if __name__ == "__main__":
    unittest.main()
