from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts import validate_m365_bff_failed_partial_safe_completion as validator


class M365BffFailedPartialSafeCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = validator.load_contract()

    def _production_fixture(self):
        if os.name == "nt":
            return None
        from tests.test_nac_bff_azure_function_deployment_reconciliation import (
            FunctionDeploymentReconciliationTests,
        )

        fixture = FunctionDeploymentReconciliationTests(
            methodName="test_inspection_is_local_read_only_and_double_reads"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_contract_maps_every_acceptance_id_to_platform_command_and_evidence(self) -> None:
        self.assertEqual(validator.validate_contract(self.contract), [])
        mapped = {
            acceptance_id
            for command in self.contract["commands"]
            for acceptance_id in command["acceptance_ids"]
        }
        for case_id in validator.REQUIRED_ACCEPTANCE_IDS:
            with self.subTest(case_id=case_id):
                self.assertIn(case_id, mapped)

    def test_provenance_roles_are_distinct_and_not_runtime_state(self) -> None:
        provenance = self.contract["provenance"]
        for case_id, expected_role in validator.REQUIRED_PROVENANCE.items():
            with self.subTest(case_id=case_id):
                self.assertEqual(provenance[case_id]["role"], expected_role)
                self.assertFalse(provenance[case_id]["runtime_state_source"])
        self.assertEqual(len({item["issue"] for item in provenance.values()}), 4)

    def test_approval_replay_matrix_blocks_before_mutation(self) -> None:
        cases = self.contract["approval_replay_cases"]
        for case_id in validator.REQUIRED_APPROVAL_REPLAY_CASES:
            with self.subTest(case_id=case_id):
                case = cases[case_id]
                self.assertEqual(case["expected_status"], "BLOCKED")
                self.assertEqual(case["mutation_count"], 0)

    def test_registry_approval_mode_is_source_bound_before_release(self) -> None:
        cases = self.contract["identity_gate_cases"]
        self.assertEqual(
            self.contract["identity_gate"]["separation_key"], "principal_id"
        )
        self.assertFalse(
            self.contract["identity_gate"]["same_principal_accounts_satisfy_four_eyes"]
        )
        registry = {
            "version": 2,
            "principals": [
                {
                    "principal_id": "person:owner-example",
                    "technical_role_ids": ["prozessverantwortung", "freigabeverantwortung"],
                    "qualifications": ["process_design"],
                    "active": True,
                }
            ],
            "accounts": [
                {
                    "account_id": "github:owner-example-primary",
                    "provider": "github",
                    "login": "owner-example-primary",
                    "principal_id": "person:owner-example",
                    "active": True,
                },
                {
                    "account_id": "github:owner-example-secondary",
                    "provider": "github",
                    "login": "owner-example-secondary",
                    "principal_id": "person:owner-example",
                    "active": True,
                },
            ],
        }
        final_head = "a" * 40
        resolver_sha256 = "d" * 64
        operator_account_id = "github:owner-example-primary"
        operator_account_sha256 = validator.identity_binding_sha256(
            "account-id", operator_account_id
        )
        operator_principal_sha256 = validator.identity_binding_sha256(
            "principal-id", "person:owner-example"
        )
        canonical_body = (
            "OWNER_SOLO_APPROVAL\nissue=746\npr=747\n"
            f"head_sha={final_head}\naccount_id_sha256={operator_account_sha256}\n"
            f"principal_id_sha256={operator_principal_sha256}\n"
            f"identity_resolver_sha256={resolver_sha256}\n"
            "four_eyes_satisfied=false"
        )
        same_principal_review = {
            "headRefOid": final_head,
            "reviewDecision": "",
            "latestReviews": [
                {"state": "APPROVED", "author": {"login": "owner-example-secondary"}}
            ],
            "ownerSoloApproval": {
                "issue": 746,
                "pr": 747,
                "head_sha": final_head,
                "account_id_sha256": operator_account_sha256,
                "principal_id_sha256": operator_principal_sha256,
                "identity_resolver_sha256": resolver_sha256,
                "approval_mode": "OWNER_SOLO_APPROVAL",
                "four_eyes_satisfied": False,
                "author_association": "OWNER",
                "approval_reference": "https://github.com/notariat8/NaC/issues/746#issuecomment-123456",
                "approval_body_sha256": hashlib.sha256(canonical_body.encode("utf-8")).hexdigest(),
            },
        }
        self.assertEqual(
            validator.validate_acceptance_roles(
                same_principal_review,
                registry,
                operator_account_id,
                self.contract["identity_gate"],
            ),
            [],
        )
        self.assertEqual(cases["no_external_requirement_single_principal"]["expected_status"], "OWNER_SOLO_APPROVAL")
        self.assertFalse(cases["no_external_requirement_single_principal"]["four_eyes_satisfied"])
        self.assertEqual(cases["binding_external_requirement_single_principal"]["expected_status"], "BLOCKED_SINGLE_PRINCIPAL")
        self.assertEqual(cases["binding_external_requirement_same_principal_accounts"]["expected_status"], "BLOCKED_SINGLE_PRINCIPAL")
        self.assertEqual(cases["incomplete_requirement_assessment"]["expected_status"], "BLOCKED_REQUIREMENT_ASSESSMENT_INVALID")
        distinct = copy.deepcopy(registry)
        distinct["principals"].append(
            {
                "principal_id": "person:second-reviewer",
                "technical_role_ids": ["freigabeverantwortung"],
                "active": True,
            }
        )
        distinct["accounts"].append(
            {
                "account_id": "github:second-reviewer",
                "provider": "github",
                "login": "second-reviewer",
                "principal_id": "person:second-reviewer",
                "active": True,
            }
        )
        distinct_review = {
            "headRefOid": final_head,
            "reviewDecision": "APPROVED",
            "latestReviews": [
                {
                    "state": "APPROVED",
                    "author": {"login": "second-reviewer"},
                    "commit": {"oid": final_head},
                }
            ]
        }
        bound_gate = copy.deepcopy(self.contract["identity_gate"])
        bound_gate["selected_approval_status"] = "FOUR_EYES_APPROVAL"
        bound_gate["external_two_person_requirement"] = {
            "applies": True,
            "applicable": True,
            "active": True,
            "requires_distinct_natural_persons": True,
            "source_type": "security_binding",
            "source_id": "security-policy:synthetic-control-4",
            "citation": "urn:nac:synthetic:security-policy:control-4",
            "version": "synthetic-v1",
            "canonical_digest": "sha256:" + "a" * 64,
            "scope": "issue-746-safe-completion",
        }
        self.assertEqual(
            validator.validate_acceptance_roles(
                distinct_review, distinct, "github:owner-example-primary", bound_gate
            ), []
        )
        stale_head_review = copy.deepcopy(distinct_review)
        stale_head_review["latestReviews"][0]["commit"]["oid"] = "b" * 40
        self.assertTrue(
            validator.validate_acceptance_roles(
                stale_head_review,
                distinct,
                "github:owner-example-primary",
                bound_gate,
            )
        )
        self.assertTrue(
            validator.validate_acceptance_roles(
                distinct_review, distinct, "github:missing-operator", bound_gate
            )
        )

        same_principal_bound = {
            "headRefOid": final_head,
            "reviewDecision": "APPROVED",
            "latestReviews": [
                {
                    "state": "APPROVED",
                    "author": {"login": "owner-example-secondary"},
                    "commit": {"oid": final_head},
                }
            ],
        }
        self.assertTrue(
            validator.validate_acceptance_roles(
                same_principal_bound, registry, "github:owner-example-primary", bound_gate
            )
        )

        missing_evidence = copy.deepcopy(same_principal_review)
        del missing_evidence["ownerSoloApproval"]
        self.assertTrue(
            validator.validate_acceptance_roles(
                missing_evidence, registry, "github:owner-example-primary", self.contract["identity_gate"]
            )
        )
        stale_evidence = copy.deepcopy(same_principal_review)
        stale_evidence["ownerSoloApproval"]["head_sha"] = "b" * 40
        self.assertTrue(
            validator.validate_acceptance_roles(
                stale_evidence, registry, "github:owner-example-primary", self.contract["identity_gate"]
            )
        )
        for field, value in (
            ("issue", 739),
            ("pr", 746),
            ("account_id_sha256", "0" * 64),
            ("principal_id_sha256", "0" * 64),
            ("identity_resolver_sha256", "0" * 64),
            ("author_association", "MEMBER"),
            ("approval_reference", "https://github.com/notariat8/NaC/issues/739#issuecomment-123456"),
            ("approval_body_sha256", "0" * 64),
        ):
            changed = copy.deepcopy(same_principal_review)
            changed["ownerSoloApproval"][field] = value
            with self.subTest(field=field):
                self.assertTrue(
                    validator.validate_acceptance_roles(
                        changed,
                        registry,
                        "github:owner-example-primary",
                        self.contract["identity_gate"],
                    )
                )

        invalid_solo_registries = []
        missing_role = copy.deepcopy(registry)
        missing_role["principals"][0]["technical_role_ids"] = ["mitarbeiter"]
        invalid_solo_registries.append(missing_role)
        missing_qualification = copy.deepcopy(registry)
        missing_qualification["principals"][0]["qualifications"] = []
        invalid_solo_registries.append(missing_qualification)
        inactive = copy.deepcopy(registry)
        inactive["principals"][0]["active"] = False
        invalid_solo_registries.append(inactive)
        for invalid_registry in invalid_solo_registries:
            with self.subTest(case="invalid_solo_authority"):
                self.assertTrue(
                    validator.validate_acceptance_roles(
                        same_principal_review,
                        invalid_registry,
                        "github:owner-example-primary",
                        self.contract["identity_gate"],
                    )
                )

        for mutate in (
            lambda assessment: assessment.pop("citation"),
            lambda assessment: assessment.__setitem__("source_type", "role_label"),
            lambda assessment: assessment.__setitem__("active", False),
            lambda assessment: assessment.__setitem__("applicable", False),
        ):
            invalid_gate = copy.deepcopy(bound_gate)
            mutate(invalid_gate["external_two_person_requirement"])
            with self.subTest(case="invalid_bound_requirement"):
                self.assertTrue(
                    validator.validate_acceptance_roles(
                        distinct_review, distinct, "github:owner-example-primary", invalid_gate
                    )
                )

        missing_approver_role = copy.deepcopy(distinct)
        missing_approver_role["principals"][-1]["technical_role_ids"] = ["mitarbeiter"]
        self.assertTrue(
            validator.validate_acceptance_roles(
                distinct_review,
                missing_approver_role,
                "github:owner-example-primary",
                bound_gate,
            )
        )

    def test_protected_evidence_loader_binds_external_file_hash(self) -> None:
        payload = {"issue": 746, "approval_mode": "OWNER_SOLO_APPROVAL"}
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "owner-solo-approval.json")
            with open(path, "wb") as handle:
                handle.write(encoded)
            digest = hashlib.sha256(encoded).hexdigest()
            loaded, errors = validator.load_protected_json(
                os.path.abspath(path), digest, label="synthetic approval"
            )
            if os.name == "nt":
                self.assertIsNone(loaded)
                self.assertEqual(
                    errors,
                    ["synthetic approval requires the supported POSIX ownership and mode backend"],
                )
            else:
                os.chmod(path, 0o600)
                loaded, errors = validator.load_protected_json(
                    os.path.abspath(path), digest, label="synthetic approval"
                )
                self.assertEqual(errors, [])
                self.assertEqual(loaded, payload)
                loaded, errors = validator.load_protected_json(
                    os.path.abspath(path), "0" * 64, label="synthetic approval"
                )
                self.assertIsNone(loaded)
                self.assertEqual(errors, ["synthetic approval sha256 mismatch"])

        loaded, errors = validator.load_protected_json(
            str(validator.IDENTITY_REGISTRY_PATH.resolve()),
            hashlib.sha256(validator.IDENTITY_REGISTRY_PATH.read_bytes()).hexdigest(),
            label="synthetic approval",
        )
        self.assertIsNone(loaded)
        if os.name == "nt":
            self.assertEqual(
                errors,
                ["synthetic approval requires the supported POSIX ownership and mode backend"],
            )
        else:
            self.assertEqual(errors, ["synthetic approval must be stored outside the repository"])

    @unittest.skipIf(os.name == "nt", "POSIX protected-file invariants")
    def test_protected_evidence_loader_rejects_unsafe_posix_inputs(self) -> None:
        def write_payload(path: str, content: bytes, mode: int = 0o600) -> str:
            with open(path, "wb") as handle:
                handle.write(content)
            os.chmod(path, mode)
            return hashlib.sha256(content).hexdigest()

        with tempfile.TemporaryDirectory() as directory:
            valid = os.path.join(directory, "valid.json")
            valid_bytes = b'{"safe":true}'
            valid_digest = write_payload(valid, valid_bytes)

            for mode in (0o400, 0o640, 0o700):
                os.chmod(valid, mode)
                loaded, errors = validator.load_protected_json(
                    valid, valid_digest, label="synthetic approval"
                )
                with self.subTest(mode=oct(mode)):
                    self.assertIsNone(loaded)
                    self.assertEqual(
                        errors,
                        ["synthetic approval must be owned by the current user with mode 0600"],
                    )
            os.chmod(valid, 0o600)

            unsafe_payloads = (
                ("oversized.json", b"x" * 131073, "exceeds the bounded resolver size"),
                ("duplicate.json", b'{"key":1,"key":2}', "must be UTF-8 JSON"),
                ("non-object.json", b"[]", "must contain a JSON object"),
                ("invalid-utf8.json", b"\xff", "must be UTF-8 JSON"),
            )
            for filename, content, expected in unsafe_payloads:
                path = os.path.join(directory, filename)
                digest = write_payload(path, content)
                loaded, errors = validator.load_protected_json(
                    path, digest, label="synthetic approval"
                )
                with self.subTest(filename=filename):
                    self.assertIsNone(loaded)
                    self.assertEqual(errors, [f"synthetic approval {expected}"])

            leaf_link = os.path.join(directory, "leaf-link.json")
            os.symlink(valid, leaf_link)
            loaded, errors = validator.load_protected_json(
                leaf_link, valid_digest, label="synthetic approval"
            )
            self.assertIsNone(loaded)
            self.assertEqual(errors, ["synthetic approval secure open failed"])

            real_parent = os.path.join(directory, "real-parent")
            os.mkdir(real_parent)
            nested = os.path.join(real_parent, "nested.json")
            nested_digest = write_payload(nested, valid_bytes)
            linked_parent = os.path.join(directory, "linked-parent")
            os.symlink(real_parent, linked_parent, target_is_directory=True)
            loaded, errors = validator.load_protected_json(
                os.path.join(linked_parent, "nested.json"),
                nested_digest,
                label="synthetic approval",
            )
            self.assertIsNone(loaded)
            self.assertEqual(errors, ["synthetic approval secure open failed"])

            race_parent = os.path.join(directory, "race-parent")
            attacker_parent = os.path.join(directory, "attacker-parent")
            preserved_parent = os.path.join(directory, "preserved-parent")
            os.mkdir(race_parent)
            os.mkdir(attacker_parent)
            race_file = os.path.join(race_parent, "resolver.json")
            race_digest = write_payload(race_file, valid_bytes)
            write_payload(
                os.path.join(attacker_parent, "resolver.json"), b'{"attacker":true}'
            )
            real_open = validator.os.open
            swapped = False

            def swap_parent_before_leaf_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if path == "resolver.json" and kwargs.get("dir_fd") is not None and not swapped:
                    os.rename(race_parent, preserved_parent)
                    os.rename(attacker_parent, race_parent)
                    swapped = True
                return real_open(path, flags, *args, **kwargs)

            with patch.object(
                validator.os, "open", side_effect=swap_parent_before_leaf_open
            ):
                loaded, errors = validator.load_protected_json(
                    race_file, race_digest, label="synthetic approval"
                )
            self.assertEqual(errors, [])
            self.assertEqual(loaded, {"safe": True})

            with patch.object(validator.os, "open", side_effect=OSError("sentinel")):
                loaded, errors = validator.load_protected_json(
                    valid, valid_digest, label="synthetic approval"
                )
            self.assertIsNone(loaded)
            self.assertEqual(errors, ["synthetic approval secure open failed"])

    def test_protected_identity_resolver_requires_three_same_principal_accounts(self) -> None:
        accounts = [
            {
                "account_id": f"{provider}:{login}",
                "provider": provider,
                "login": login,
                "principal_id": "person:owner-example",
                "active": True,
            }
            for provider, login in (
                ("github", "owner-example-primary"),
                ("github", "owner-example-secondary"),
                ("nvidia-gitlab", "owner-example"),
            )
        ]
        resolver = {
            "schema_version": "nac.protected-identity-resolver/v1",
            "contract_id": "issue-746-owner-account-principal-resolution",
            "known_owner_account_count": 3,
            "all_known_accounts_same_principal": True,
            "registry": {
                "version": 2,
                "principals": [
                    {
                        "principal_id": "person:owner-example",
                        "technical_role_ids": ["prozessverantwortung"],
                        "qualifications": ["process_design"],
                        "active": True,
                    }
                ],
                "accounts": accounts,
            },
        }
        operator, errors = validator.validate_protected_identity_resolver(
            resolver, "github:owner-example-primary"
        )
        self.assertEqual(errors, [])
        self.assertEqual(operator["principal_id"], "person:owner-example")

        wrong_principal = copy.deepcopy(resolver)
        wrong_principal["registry"]["principals"].append(
            {
                "principal_id": "person:other-example",
                "technical_role_ids": ["prozessverantwortung"],
                "qualifications": ["process_design"],
                "active": True,
            }
        )
        wrong_principal["registry"]["accounts"][1]["principal_id"] = (
            "person:other-example"
        )
        self.assertTrue(
            validator.validate_protected_identity_resolver(
                wrong_principal, "github:owner-example-primary"
            )[1]
        )

        wrong_count = copy.deepcopy(resolver)
        wrong_count["registry"]["accounts"].pop()
        self.assertTrue(
            validator.validate_protected_identity_resolver(
                wrong_count, "github:owner-example-primary"
            )[1]
        )

        inactive_extra = copy.deepcopy(resolver)
        inactive_extra["registry"]["accounts"].append(
            {
                "account_id": "github:inactive-example",
                "provider": "github",
                "login": "inactive-example",
                "principal_id": "person:owner-example",
                "active": False,
            }
        )
        self.assertTrue(
            validator.validate_protected_identity_resolver(
                inactive_extra, "github:owner-example-primary"
            )[1]
        )

        inactive_known = copy.deepcopy(resolver)
        inactive_known["registry"]["accounts"][2]["active"] = False
        self.assertTrue(
            validator.validate_protected_identity_resolver(
                inactive_known, "github:owner-example-primary"
            )[1]
        )

        declared_count_drift = copy.deepcopy(resolver)
        declared_count_drift["known_owner_account_count"] = 4
        self.assertTrue(
            validator.validate_protected_identity_resolver(
                declared_count_drift, "github:owner-example-primary"
            )[1]
        )

    def test_owner_comment_loader_verifies_live_canonical_provenance(self) -> None:
        head = "a" * 40
        account_id = "github:owner-example-primary"
        account_id_sha256 = validator.identity_binding_sha256("account-id", account_id)
        principal_id = "person:owner-example"
        principal_id_sha256 = validator.identity_binding_sha256(
            "principal-id", principal_id
        )
        resolver_sha256 = "d" * 64
        reference = "https://github.com/notariat8/NaC/issues/746#issuecomment-123456"
        body = (
            "OWNER_SOLO_APPROVAL\n"
            "issue=746\n"
            "pr=747\n"
            f"head_sha={head}\n"
            f"account_id_sha256={account_id_sha256}\n"
            f"principal_id_sha256={principal_id_sha256}\n"
            f"identity_resolver_sha256={resolver_sha256}\n"
            "four_eyes_satisfied=false"
        )
        valid_comment = {
            "html_url": reference,
            "author_association": "OWNER",
            "user": {"login": "owner-example-primary"},
            "body": body,
        }

        def fetch(comment: dict):
            return patch.object(
                validator.subprocess,
                "run",
                return_value=SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps(comment),
                    stderr="",
                ),
            )

        with fetch(valid_comment):
            approval, errors = validator.fetch_owner_solo_approval(
                reference,
                expected_head=head,
                operator_account_id=account_id,
                operator_principal_id=principal_id,
                identity_resolver_sha256=resolver_sha256,
            )
        self.assertEqual(errors, [])
        self.assertEqual(approval["head_sha"], head)
        self.assertEqual(approval["author_association"], "OWNER")

        mutations = (
            ("body", body + "\nchanged=true"),
            ("author_association", "MEMBER"),
            ("html_url", "https://github.com/notariat8/NaC/issues/739#issuecomment-123456"),
        )
        for field, value in mutations:
            changed = copy.deepcopy(valid_comment)
            changed[field] = value
            with self.subTest(field=field), fetch(changed):
                approval, errors = validator.fetch_owner_solo_approval(
                    reference,
                    expected_head=head,
                    operator_account_id=account_id,
                    operator_principal_id=principal_id,
                    identity_resolver_sha256=resolver_sha256,
                )
                self.assertIsNone(approval)
                self.assertTrue(errors)

    def test_preflight_binding_drift_matrix_blocks_before_provider(self) -> None:
        cases = self.contract["preflight_binding_cases"]
        for case_id in validator.REQUIRED_PREFLIGHT_CASES:
            with self.subTest(case_id=case_id):
                self.assertEqual(cases[case_id]["expected_status"], "BLOCKED")
                self.assertEqual(cases[case_id]["provider_read_snapshot_count"], 0)
                self.assertEqual(cases[case_id]["total_write_count"], 0)

        fixture = self._production_fixture()
        if fixture is None:
            self.skipTest("POSIX production fixture required for runtime drift checks")
        from tests.test_nac_bff_azure_function_deployment_reconciliation import (
            _ObservationPort,
        )

        mutations = {
            "reconciler_commit": {"approved_commit": "0" * 40},
            "reconciler_tree": {"approved_tree": "0" * 40},
            "reconciler_toolchain_sha256": {"toolchain_sha256": "0" * 64},
            "required_owner_login": {"required_owner_login": "wrong-owner"},
        }
        original = fixture.binding
        for case_id, changes in mutations.items():
            port = _ObservationPort()
            fixture.binding = replace(original, **changes)
            with self.subTest(runtime_case=case_id):
                result = fixture._inspect(port)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(port.calls, [])
        fixture.binding = original

    def test_double_snapshot_accepts_only_stable_not_applied(self) -> None:
        with self.subTest(case_id="stable_not_applied"):
            decision = validator.classify_provider_observation(
                [{"classification": "FUNCTION_DEPLOYMENT_NOT_APPLIED"}] * 2
            )
            self.assertEqual(decision, "FUNCTION_DEPLOYMENT_NOT_APPLIED")

    def test_provider_decision_block_matrix_has_zero_writes(self) -> None:
        cases = self.contract["provider_decision_cases"]
        for case_id in validator.REQUIRED_PROVIDER_BLOCK_CASES:
            with self.subTest(case_id=case_id):
                self.assertEqual(cases[case_id]["expected_status"], "BLOCKED")
                self.assertEqual(cases[case_id]["provider_write_count"], 0)
                self.assertEqual(cases[case_id]["tenant_write_count"], 0)
                self.assertEqual(cases[case_id]["credential_write_count"], 0)

    def test_redaction_sentinel_matrix_never_reaches_any_sink(self) -> None:
        matrix = self.contract["redaction_sentinel_cases"]
        for sink in validator.REQUIRED_REDACTION_SINKS:
            with self.subTest(sink=sink):
                self.assertEqual(matrix[sink]["sentinel_reaches_sink"], False)
                self.assertEqual(matrix[sink]["unknown_field_status"], "BLOCKED")

    def test_credential_config_boundary_blocks_refresh_and_preserves_host_state(self) -> None:
        matrix = self.contract["credential_boundary_cases"]
        for case_id in validator.REQUIRED_CREDENTIAL_CASES:
            with self.subTest(case_id=case_id):
                self.assertEqual(matrix[case_id]["expected_status"], "BLOCKED")
                self.assertEqual(matrix[case_id]["credential_write_count"], 0)
                self.assertTrue(matrix[case_id]["host_state_unchanged"])

    def test_status_error_counter_and_hash_matrix_is_exact(self) -> None:
        status = self.contract["status_counter_hash_cases"]
        for case_id in validator.REQUIRED_STATUS_COUNTER_HASH_CASES:
            with self.subTest(case_id=case_id):
                self.assertIn(case_id, status)
        self.assertEqual(
            set(self.contract["stable_error_codes_exact"]),
            validator.required_stable_error_codes(),
        )

    def test_windows_matrix_blocks_before_every_side_effect_edge(self) -> None:
        matrix = self.contract["windows_fail_closed_matrix"]
        for edge in validator.REQUIRED_WINDOWS_EDGES:
            for side_effect in validator.REQUIRED_WINDOWS_SIDE_EFFECTS:
                with self.subTest(edge=edge, side_effect=side_effect):
                    case = matrix[edge][side_effect]
                    self.assertEqual(case["status"], "BLOCKED")
                    self.assertEqual(
                        case["error_code"], "PLATFORM_SECURITY_BACKEND_UNAVAILABLE"
                    )
                    self.assertFalse(case["reached"])

    def test_crash_before_first_append_keeps_all_journals_held(self) -> None:
        with self.subTest(case_id="before_first_append"):
            case = self.contract["journal_crash_cases"]["before_first_append"]
            self.assertEqual(case["journal_states"], ["HELD", "HELD", "HELD"])
            self.assertEqual(case["expected_status"], "BLOCKED")
        fixture = self._production_fixture()
        if fixture is None:
            self.skipTest("POSIX production fixture required for crash-window checks")
        inspection = fixture._inspect()

        def crash_before_first_append(point: str) -> None:
            if point == "marker:AUTHORIZED":
                raise RuntimeError("synthetic crash before first journal append")

        result = fixture._release(
            inspection, fault_injector=crash_before_first_append
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            [fixture._lock_marker(path)["status"] for path in fixture._lock_paths()],
            ["HELD", "HELD", "HELD"],
        )

    def test_crash_after_true_prefix_completes_only_with_same_approval(self) -> None:
        cases = self.contract["journal_crash_cases"]
        for case_id in (
            "after_first_append",
            "after_second_append",
            "changed_approval",
            "unknown_tail",
            "wrong_order",
        ):
            with self.subTest(case_id=case_id):
                self.assertIn(case_id, cases)
        self.assertTrue(cases["after_first_append"]["same_approval_may_resume"])
        self.assertTrue(cases["after_second_append"]["same_approval_may_resume"])
        for case_id in ("changed_approval", "unknown_tail", "wrong_order"):
            self.assertFalse(cases[case_id]["same_approval_may_resume"])
        fixture = self._production_fixture()
        if fixture is None:
            self.skipTest("POSIX production fixture required for crash-replay checks")
        inspection = fixture._inspect()

        def crash_after_second(point: str) -> None:
            if point == "lock:legacy":
                raise RuntimeError("synthetic crash after second journal append")

        first = fixture._release(inspection, fault_injector=crash_after_second)
        self.assertEqual(first["status"], "BLOCKED")
        self.assertEqual(
            [fixture._lock_marker(path)["status"] for path in fixture._lock_paths()],
            ["RELEASED", "RELEASED", "HELD"],
        )
        wrong = fixture._approval(
            inspection, provider_observation_sha256="0" * 64
        )
        blocked = fixture._release(inspection, approval=wrong)
        self.assertEqual(blocked["status"], "BLOCKED")
        completed = fixture._release(inspection)
        self.assertEqual(
            completed["status"], "FUNCTION_DEPLOYMENT_QUARANTINE_RELEASED"
        )

    def test_crash_after_all_appends_returns_idempotent_release(self) -> None:
        cases = self.contract["journal_crash_cases"]
        for case_id in ("after_third_append_before_return", "same_approval_replay"):
            with self.subTest(case_id=case_id):
                self.assertEqual(
                    cases[case_id]["expected_status"], "LOCK_JOURNALS_RELEASED"
                )
                self.assertEqual(
                    cases[case_id]["journal_states"],
                    ["RELEASED", "RELEASED", "RELEASED"],
                )
        fixture = self._production_fixture()
        if fixture is None:
            self.skipTest("POSIX production fixture required for idempotent replay checks")
        inspection = fixture._inspect()

        def crash_after_third(point: str) -> None:
            if point == "lock:legacy_host":
                raise RuntimeError("synthetic crash after third journal append")

        first = fixture._release(inspection, fault_injector=crash_after_third)
        self.assertEqual(first["status"], "BLOCKED")
        self.assertEqual(
            [fixture._lock_marker(path)["status"] for path in fixture._lock_paths()],
            ["RELEASED", "RELEASED", "RELEASED"],
        )
        completed = fixture._release(inspection)
        self.assertEqual(
            completed["status"], "FUNCTION_DEPLOYMENT_QUARANTINE_RELEASED"
        )
        replay = fixture._release(inspection)
        self.assertEqual(
            replay["status"], "FUNCTION_DEPLOYMENT_QUARANTINE_RELEASED"
        )

    def test_unknown_tail_and_wrong_order_block_without_further_release(self) -> None:
        fixture = self._production_fixture()
        if fixture is None:
            self.skipTest("POSIX production fixture required for journal corruption checks")

        inspection = fixture._inspect()

        def crash_after_target(point: str) -> None:
            if point == "lock:target":
                raise RuntimeError("synthetic crash after target release")

        first = fixture._release(inspection, fault_injector=crash_after_target)
        self.assertEqual(first["status"], "BLOCKED")
        paths = fixture._lock_paths()
        with open(paths[0], "ab") as handle:
            handle.write(b'{"activation_hash":"' + (b"a" * 64) + b'","status":"HELD"}\n')
        before_corrupt_retry = {
            path: path.read_bytes() for path in fixture.root.rglob("*") if path.is_file()
        }
        corrupted = fixture._release(inspection)
        self.assertEqual(corrupted["status"], "BLOCKED")
        self.assertEqual(
            before_corrupt_retry,
            {path: path.read_bytes() for path in fixture.root.rglob("*") if path.is_file()},
        )
        self.assertEqual(fixture._lock_marker(paths[1])["status"], "HELD")
        self.assertEqual(fixture._lock_marker(paths[2])["status"], "HELD")

        second_fixture = self._production_fixture()
        if second_fixture is None:
            return
        second_inspection = second_fixture._inspect()
        second_paths = second_fixture._lock_paths()
        released = json.dumps(
            {
                "activation_hash": "a" * 64,
                "status": "RELEASED",
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii") + b"\n"
        with open(second_paths[1], "ab") as handle:
            handle.write(released)
        before_wrong_order_retry = {
            path: path.read_bytes()
            for path in second_fixture.root.rglob("*")
            if path.is_file()
        }
        wrong_order = second_fixture._release(second_inspection)
        self.assertEqual(wrong_order["status"], "BLOCKED")
        self.assertEqual(
            before_wrong_order_retry,
            {
                path: path.read_bytes()
                for path in second_fixture.root.rglob("*")
                if path.is_file()
            },
        )
        self.assertEqual(second_fixture._lock_marker(second_paths[0])["status"], "HELD")
        self.assertEqual(second_fixture._lock_marker(second_paths[2])["status"], "HELD")

    def test_required_remote_checks_match_exact_context_names(self) -> None:
        valid = [
            {"workflowName": context.split(" / ", 1)[0], "name": context.split(" / ", 1)[1], "conclusion": "SUCCESS"}
            for context in validator.REQUIRED_REMOTE_CONTEXTS
        ]
        self.assertEqual(validator.validate_check_rollup(valid), [])
        payload = {"number": 747, "headRefOid": "a" * 40, "statusCheckRollup": valid}
        self.assertEqual(
            validator.validate_pr_payload(payload, expected_pr=747, expected_head="a" * 40),
            [],
        )
        positive_cases = {
            "pr_747": payload["number"] == 747,
            "local_head_source": payload["headRefOid"] == "a" * 40,
            "secret_scan": any(item["name"] == "secret-scan" for item in valid),
            "privacy_lint": any(item["name"] == "privacy-lint" for item in valid),
            "quality_gate": any(item["name"] == "quality-gate" for item in valid),
            "windows_offline_cli": any(item["name"] == "windows-offline-cli" for item in valid),
        }
        for case_id, result in positive_cases.items():
            with self.subTest(case_id=case_id):
                self.assertTrue(result)
        wrong_head = copy.deepcopy(payload)
        wrong_head["headRefOid"] = "b" * 40
        with self.subTest(case_id="wrong_local_head"):
            self.assertTrue(
                validator.validate_pr_payload(
                    wrong_head, expected_pr=747, expected_head="a" * 40
                )
            )
        for case_id, mutated in validator.remote_check_negative_cases(valid).items():
            with self.subTest(case_id=case_id):
                self.assertTrue(validator.validate_check_rollup(mutated))

    def test_remote_verifier_errors_are_stable_and_redacted(self) -> None:
        sentinel = "SENSITIVE_PROVIDER_DIAGNOSTIC"
        ok_head = SimpleNamespace(returncode=0, stdout="a" * 40 + "\n", stderr="")
        ok_diff = SimpleNamespace(
            returncode=0,
            stdout="\n".join(sorted(validator.EXPECTED_PR_FILES)) + "\n",
            stderr="",
        )
        failures = (
            (
                [SimpleNamespace(returncode=1, stdout="", stderr=sentinel)],
                "FINAL_HEAD_RESOLUTION_FAILED",
            ),
            (
                [ok_head, SimpleNamespace(returncode=1, stdout="", stderr=sentinel)],
                "PR_SCOPE_RESOLUTION_FAILED",
            ),
            (
                [ok_head, ok_diff, SimpleNamespace(returncode=1, stdout="", stderr=sentinel)],
                "GITHUB_PR_READ_FAILED",
            ),
            (
                [ok_head, ok_diff, SimpleNamespace(returncode=0, stdout=sentinel, stderr="")],
                "GITHUB_PR_RESPONSE_INVALID",
            ),
            (
                [ok_head, ok_diff, SimpleNamespace(returncode=0, stdout="[]", stderr="")],
                "GITHUB_PR_RESPONSE_INVALID",
            ),
        )
        for results, expected_code in failures:
            with self.subTest(expected_code=expected_code), patch.object(
                validator.subprocess, "run", side_effect=results
            ):
                errors = validator.verify_pr_checks(
                    expected_pr=747,
                    expected_head_ref="HEAD",
                    protected_identity_resolver_file="C:/protected/resolver.json",
                    protected_identity_resolver_sha256="d" * 64,
                    operator_account_id="github:owner-example-primary",
                    owner_solo_approval_reference=None,
                )
            self.assertEqual(errors, [expected_code])
            self.assertNotIn(sentinel, "\n".join(errors))

    def test_verify_pr_checks_cli_requires_and_forwards_all_identity_inputs(self) -> None:
        required = {
            "--protected-identity-resolver-file": "C:/protected/resolver.json",
            "--protected-identity-resolver-sha256": "d" * 64,
            "--operator-account-id": "github:owner-example-primary",
            "--owner-solo-approval-reference": (
                "https://github.com/notariat8/NaC/issues/746#issuecomment-123456"
            ),
        }
        with patch.object(validator, "validate_contract", side_effect=lambda _contract: []):
            for omitted in required:
                argv = ["validator", "--verify-pr-checks"]
                for option, value in required.items():
                    if option != omitted:
                        argv.extend((option, value))
                with self.subTest(omitted=omitted), patch.object(sys, "argv", list(argv)), patch.object(
                    validator, "verify_pr_checks"
                ) as verify, patch("builtins.print"):
                    self.assertEqual(validator.main(), 1)
                    verify.assert_not_called()

            argv = ["validator", "--verify-pr-checks"]
            for option, value in required.items():
                argv.extend((option, value))
            with patch.object(sys, "argv", list(argv)), patch.object(
                validator, "verify_pr_checks", return_value=[]
            ) as verify, patch("builtins.print") as output:
                result = validator.main()
            self.assertEqual(result, 0, output.call_args_list)
            verify.assert_called_once_with(
                747,
                "HEAD",
                required["--protected-identity-resolver-file"],
                required["--protected-identity-resolver-sha256"],
                required["--operator-account-id"],
                required["--owner-solo-approval-reference"],
            )

    def test_ai_sbom_registers_issue746_agentic_contract_without_release_export(self) -> None:
        sbom = json.loads(validator.AI_SBOM_PATH.read_text(encoding="utf-8"))
        mapping = json.loads(validator.AI_SBOM_MAPPING_PATH.read_text(encoding="utf-8"))
        entries = {
            item["id"]: item
            for item in sbom["clusters"]["system_level_properties"]
        }
        entry = entries["m365-bff-failed-partial-safe-completion-contract"]
        for case_id in (
            "human_review_owner",
            "approval_mode",
            "four_eyes_satisfied",
            "external_two_person_requirement",
            "provider_boundary",
            "evidence_binding",
            "privacy_boundary",
        ):
            with self.subTest(case_id=case_id):
                self.assertIn(case_id, entry)
        self.assertEqual(entry["human_review_owner"], "owner_solo_approval_source_bound")
        self.assertEqual(entry["approval_mode"], "OWNER_SOLO_APPROVAL")
        self.assertFalse(entry["four_eyes_satisfied"])
        self.assertEqual(
            entry["external_two_person_requirement"],
            "not_applicable_no_cited_source_for_issue_746",
        )
        self.assertFalse(mapping["scope"]["release_export_enabled"])

    def test_contract_mutations_are_rejected(self) -> None:
        mutations = {
            "missing_ac": lambda data: data.__setitem__("acceptance_ids", data["acceptance_ids"][:-1]),
            "merged_gate": lambda data: data["gates"].__setitem__("ISSUE_739_QUARANTINE_RELEASE", data["gates"]["SPEC_746_APPROVAL"]),
            "issue_is_runtime": lambda data: data["provenance"]["issue739_current_trail"].__setitem__("runtime_state_source", True),
            "windows_live_reached": lambda data: data["windows_fail_closed_matrix"]["live"]["provider"].__setitem__("reached", True),
            "solo_claims_four_eyes": lambda data: data["identity_gate"].__setitem__("owner_solo_recorded_as_four_eyes", True),
            "role_label_creates_requirement": lambda data: data["identity_gate"].__setitem__("role_name_alone_proves_two_person_requirement", True),
            "uncited_second_principal_requirement": lambda data: data["identity_gate"].__setitem__("acceptance_requires_second_qualified_principal", True),
            "external_requirement_without_source": lambda data: data["identity_gate"]["external_two_person_requirement"].__setitem__("applies", True),
            "spec_gate_releases_quarantine": lambda data: data["gates"]["SPEC_746_APPROVAL"].__setitem__("authorizes", "three_local_append_only_release_records_only"),
            "spec_gate_runs_live": lambda data: data["gates"]["SPEC_746_APPROVAL"].__setitem__("authorizes", "one_separately_hash_bound_live_run_only"),
            "release_gate_runs_live": lambda data: data["gates"]["ISSUE_739_QUARANTINE_RELEASE"].__setitem__("authorizes", "one_separately_hash_bound_live_run_only"),
            "live_gate_releases_local": lambda data: data["gates"]["ISSUE_632_NEW_LIVE_RUN"].__setitem__("authorizes", "three_local_append_only_release_records_only"),
            "missing_gate_authorization": lambda data: data["gates"]["SPEC_746_APPROVAL"].pop("authorizes"),
            "unknown_gate_authorization": lambda data: data["gates"]["SPEC_746_APPROVAL"].__setitem__("authorizes", "unknown"),
        }
        for case_id, mutate in mutations.items():
            with self.subTest(case_id=case_id):
                changed = copy.deepcopy(self.contract)
                mutate(changed)
                self.assertTrue(validator.validate_contract(changed))


if __name__ == "__main__":
    unittest.main()
