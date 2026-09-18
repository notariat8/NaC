from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

from nac_bff.issue746_reconciliation_gate import (
    GATE_CLOSED,
    Issue746ReconciliationAuthorization,
    Issue746ReconciliationGateError,
    identity_binding_sha256,
    resolve_authorized_operator,
    verify_issue746_readonly_reconciliation_gate,
)


HEAD = "a" * 40
TREE = "b" * 40
RESOLVER_SHA256 = "c" * 64
ACCOUNT_ID = "github:owner-primary"
PRINCIPAL_ID = "person:owner"
REFERENCE = "https://github.com/notariat8/NaC/issues/746#issuecomment-123"


def _resolver() -> dict:
    return {
        "schema_version": "nac.protected-identity-resolver/v1",
        "contract_id": "issue-746-owner-account-principal-resolution",
        "known_owner_account_count": 3,
        "all_known_accounts_same_principal": True,
        "registry": {
            "version": 2,
            "principals": [
                {
                    "principal_id": PRINCIPAL_ID,
                    "technical_role_ids": ["prozessverantwortung"],
                    "qualifications": ["process_design"],
                    "active": True,
                }
            ],
            "accounts": [
                {
                    "account_id": "github:owner-primary",
                    "provider": "github",
                    "login": "owner-primary",
                    "principal_id": PRINCIPAL_ID,
                    "active": True,
                },
                {
                    "account_id": "github:owner-secondary",
                    "provider": "github",
                    "login": "owner-secondary",
                    "principal_id": PRINCIPAL_ID,
                    "active": True,
                },
                {
                    "account_id": "nvidia-gitlab:owner",
                    "provider": "nvidia-gitlab",
                    "login": "owner",
                    "principal_id": PRINCIPAL_ID,
                    "active": True,
                },
            ],
        },
    }


def _checks() -> list[dict]:
    return [
        {"workflowName": "Privacy and Secrets Guard", "name": "secret-scan", "conclusion": "SUCCESS"},
        {"workflowName": "Privacy and Secrets Guard", "name": "privacy-lint", "conclusion": "SUCCESS"},
        {"workflowName": "NaC Quality Gate", "name": "quality-gate", "conclusion": "SUCCESS"},
        {"workflowName": "NaC Windows Portability", "name": "windows-offline-cli", "conclusion": "SUCCESS"},
    ]


def _approval_body() -> str:
    return (
        "OWNER_SOLO_APPROVAL\n"
        "issue=746\n"
        "pr=747\n"
        f"head_sha={HEAD}\n"
        f"account_id_sha256={identity_binding_sha256('account-id', ACCOUNT_ID)}\n"
        f"principal_id_sha256={identity_binding_sha256('principal-id', PRINCIPAL_ID)}\n"
        f"identity_resolver_sha256={RESOLVER_SHA256}\n"
        "four_eyes_satisfied=false"
    )


class _Reader:
    def __init__(self, *, checks: list[dict] | None = None, body: str | None = None):
        self.checks = _checks() if checks is None else checks
        self.body = _approval_body() if body is None else body

    def read_json(self, argv):
        if argv[0] == "pr":
            return {"number": 747, "headRefOid": HEAD, "statusCheckRollup": self.checks}
        return {
            "html_url": REFERENCE,
            "created_at": "2026-09-18T10:00:00Z",
            "updated_at": "2026-09-18T10:00:00Z",
            "author_association": "OWNER",
            "user": {"login": "owner-primary"},
            "body": self.body,
        }


class Issue746ReconciliationGateTests(unittest.TestCase):
    def _verify(self, reader=None) -> Issue746ReconciliationAuthorization:
        with (
            patch(
                "nac_bff.issue746_reconciliation_gate.load_protected_identity_resolver",
                return_value=_resolver(),
            ),
            patch(
                "nac_bff.issue746_reconciliation_gate.read_clean_git_snapshot",
                return_value=(HEAD, TREE),
            ),
        ):
            return verify_issue746_readonly_reconciliation_gate(
                repo_root=Mock(),
                protected_identity_resolver_file=Mock(),
                protected_identity_resolver_sha256=RESOLVER_SHA256,
                operator_account_id=ACCOUNT_ID,
                owner_solo_approval_reference=REFERENCE,
                github_reader=reader or _Reader(),
            )

    def test_valid_gate_returns_digest_bound_solo_owner_authorization(self) -> None:
        authorization = self._verify()
        self.assertEqual(authorization.approved_head, HEAD)
        self.assertEqual(authorization.approved_tree, TREE)
        self.assertFalse(authorization.four_eyes_satisfied)
        authorization.verify(expected_head=HEAD, expected_tree=TREE)

    def test_same_principal_accounts_never_satisfy_four_eyes(self) -> None:
        operator = resolve_authorized_operator(_resolver(), ACCOUNT_ID)
        self.assertEqual(operator["principal_id"], PRINCIPAL_ID)

    def test_missing_remote_check_blocks(self) -> None:
        with self.assertRaises(Issue746ReconciliationGateError) as raised:
            self._verify(_Reader(checks=_checks()[:-1]))
        self.assertEqual(raised.exception.code, GATE_CLOSED)

    def test_changed_approval_body_blocks(self) -> None:
        with self.assertRaises(Issue746ReconciliationGateError) as raised:
            self._verify(_Reader(body=_approval_body() + "\nchanged=true"))
        self.assertEqual(raised.exception.code, GATE_CLOSED)

    def test_digest_tampering_blocks_runtime_reuse(self) -> None:
        authorization = self._verify()
        tampered = replace(authorization, resolver_sha256="d" * 64)
        with self.assertRaises(Issue746ReconciliationGateError):
            tampered.verify(expected_head=HEAD, expected_tree=TREE)

    def test_synthetic_authorization_object_cannot_bypass_gate(self) -> None:
        authorization = self._verify()
        forged = replace(authorization, _runtime_seal=object())
        with self.assertRaises(Issue746ReconciliationGateError):
            forged.verify(expected_head=HEAD, expected_tree=TREE)

    def test_raw_login_is_not_a_governance_identity(self) -> None:
        with self.assertRaises(Issue746ReconciliationGateError):
            resolve_authorized_operator(_resolver(), "owner-primary")


if __name__ == "__main__":
    unittest.main()
