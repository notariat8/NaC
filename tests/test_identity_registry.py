from __future__ import annotations

import json
import unittest

from scripts import validate_identity_registry


class IdentityRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(validate_identity_registry.REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_repository_registry_is_valid(self) -> None:
        self.assertEqual(validate_identity_registry.validate_registry(self.registry), [])
        self.assertEqual(
            validate_identity_registry.validate_public_registry_privacy(self.registry), []
        )

    def test_public_registry_rejects_non_synthetic_identity(self) -> None:
        registry = json.loads(json.dumps(self.registry))
        registry["accounts"][0]["login"] = "production-login"
        self.assertTrue(
            validate_identity_registry.validate_public_registry_privacy(registry)
        )

    def test_raw_login_is_not_a_governance_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "raw login"):
            validate_identity_registry.resolve_principal(
                self.registry, "owner-example-primary"
            )

    def test_different_github_accounts_resolve_to_same_principal(self) -> None:
        private = validate_identity_registry.resolve_principal(
            self.registry, "github:owner-example-primary"
        )
        professional = validate_identity_registry.resolve_principal(
            self.registry, "github:owner-example-secondary"
        )
        self.assertEqual(private["principal_id"], professional["principal_id"])

    def test_same_principal_never_satisfies_four_eyes(self) -> None:
        self.assertFalse(
            validate_identity_registry.satisfies_four_eyes(
                self.registry,
                "github:owner-example-primary",
                "github:owner-example-secondary",
            )
        )

    def test_solo_owner_is_allowed_without_external_two_person_requirement(self) -> None:
        result = validate_identity_registry.evaluate_approval_mode(
            self.registry, operator_account_id="github:owner-example-primary"
        )
        self.assertEqual(result["status"], "OWNER_SOLO_APPROVAL")
        self.assertEqual(result["four_eyes_satisfied"], "false")

    def test_external_two_person_requirement_blocks_single_principal(self) -> None:
        result = validate_identity_registry.evaluate_approval_mode(
            self.registry,
            operator_account_id="github:owner-example-secondary",
            external_two_person_required=True,
            requirement_citation="binding-policy:section-4",
        )
        self.assertEqual(result["status"], "BLOCKED_SINGLE_PRINCIPAL")

    def test_role_label_without_citation_does_not_create_two_person_gate(self) -> None:
        result = validate_identity_registry.evaluate_approval_mode(
            self.registry,
            operator_account_id="github:owner-example-primary",
            external_two_person_required=True,
            requirement_citation="",
        )
        self.assertEqual(result["status"], "BLOCKED_REQUIREMENT_CITATION_MISSING")

    def test_principal_qualifications_must_be_unique_nonempty_strings(self) -> None:
        for invalid in (
            "process_design",
            [],
            ["process_design", "process_design"],
            [""],
            [False],
        ):
            with self.subTest(invalid=invalid):
                registry = json.loads(json.dumps(self.registry))
                registry["principals"][0]["qualifications"] = invalid
                self.assertTrue(
                    validate_identity_registry.validate_registry(registry)
                )

    def test_unknown_registry_fields_are_rejected(self) -> None:
        registry = json.loads(json.dumps(self.registry))
        registry["principals"][0]["unexpected"] = True
        self.assertTrue(validate_identity_registry.validate_registry(registry))

    def test_different_principals_satisfy_four_eyes(self) -> None:
        registry = json.loads(json.dumps(self.registry))
        registry["principals"].append(
            {"principal_id": "person:second-reviewer", "technical_role_ids": ["freigabeverantwortung"], "active": True}
        )
        registry["accounts"].append(
            {"account_id": "github:second-reviewer", "provider": "github", "login": "second-reviewer", "principal_id": "person:second-reviewer", "active": True}
        )
        self.assertTrue(
            validate_identity_registry.satisfies_four_eyes(
                registry, "github:owner-example-primary", "github:second-reviewer"
            )
        )


if __name__ == "__main__":
    unittest.main()
