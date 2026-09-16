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

    def test_raw_login_is_not_a_governance_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "raw login"):
            validate_identity_registry.resolve_principal(self.registry, "ofunk")

    def test_different_github_accounts_resolve_to_same_principal(self) -> None:
        private = validate_identity_registry.resolve_principal(self.registry, "github:ofunk")
        professional = validate_identity_registry.resolve_principal(self.registry, "github:ofunk-nvidia")
        self.assertEqual(private["principal_id"], professional["principal_id"])

    def test_same_principal_never_satisfies_four_eyes(self) -> None:
        self.assertFalse(
            validate_identity_registry.satisfies_four_eyes(
                self.registry, "github:ofunk", "github:ofunk-nvidia"
            )
        )

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
                registry, "github:ofunk", "github:second-reviewer"
            )
        )


if __name__ == "__main__":
    unittest.main()
