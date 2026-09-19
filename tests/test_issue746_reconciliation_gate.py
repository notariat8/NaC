from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from nac_bff.issue746_reconciliation_gate import (
    GATE_CLOSED,
    GITHUB_READ_CHANNEL_UNAVAILABLE,
    Issue746ReconciliationAuthorization,
    Issue746ReconciliationGateError,
    identity_binding_sha256,
    _git_read,
    resolve_authorized_operator,
    verify_issue746_readonly_reconciliation_gate,
)


HEAD = "a" * 40
TREE = "b" * 40
RESOLVER_SHA256 = "c" * 64
ACCOUNT_ID = "github:owner-primary"
PRINCIPAL_ID = "person:owner"
REFERENCE = "https://github.com/notariat8/NaC/issues/746#issuecomment-123"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolver() -> dict:
    return {
        "schema_version": "nac.protected-identity-resolver/v1",
        "contract_id": "issue-746-owner-account-principal-resolution",
        "known_owner_account_count": 3,
        "all_known_accounts_same_principal": True,
        "external_two_person_requirement": {
            "required": False,
            "citation": None,
            "scope": "issue746_readonly_reconciliation",
            "source_sha256": None,
        },
        "git_attestation": {
            "executable_path": str(Path(shutil.which("git") or "C:/Git/git.exe").resolve()),
            "executable_sha256": "f" * 64,
        },
        "registry": {
            "version": 2,
            "principals": [
                {
                    "principal_id": PRINCIPAL_ID,
                    "technical_role_ids": [
                        "prozessverantwortung",
                        "freigabeverantwortung",
                    ],
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

        self.calls = []

    def read_pull_request(self, *, owner, repository, number):
        self.calls.append(("pr", owner, repository, number))
        return {
            "number": 747,
            "url": "https://github.com/notariat8/NaC/pull/747",
            "repository": {"nameWithOwner": "notariat8/NaC"},
            "headRefOid": HEAD,
            "statusCheckRollup": self.checks,
        }

    def read_issue_comment(self, *, owner, repository, comment_id):
        self.calls.append(("comment", owner, repository, comment_id))
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
        reader = _Reader()
        authorization = self._verify(reader)
        self.assertEqual(authorization.approved_head, HEAD)
        self.assertEqual(authorization.approved_tree, TREE)
        self.assertFalse(authorization.four_eyes_satisfied)
        self.assertEqual(
            reader.calls,
            [
                ("pr", "notariat8", "NaC", 747),
                ("comment", "notariat8", "NaC", 123),
            ],
        )
        authorization.verify(expected_head=HEAD, expected_tree=TREE)

    def test_same_principal_accounts_never_satisfy_four_eyes(self) -> None:
        operator = resolve_authorized_operator(_resolver(), ACCOUNT_ID)
        self.assertEqual(operator["principal_id"], PRINCIPAL_ID)

    def test_bound_external_two_person_requirement_blocks_single_principal(self) -> None:
        resolver = _resolver()
        resolver["external_two_person_requirement"] = {
            "required": True,
            "citation": "binding-policy:section-4",
            "scope": "issue746_readonly_reconciliation",
            "source_sha256": "e" * 64,
        }
        with self.assertRaises(Issue746ReconciliationGateError) as raised:
            resolve_authorized_operator(resolver, ACCOUNT_ID)
        self.assertIn("single principal", raised.exception.reason)

    def test_malformed_qualification_string_is_rejected(self) -> None:
        resolver = _resolver()
        resolver["registry"]["principals"][0]["qualifications"] = "process_design"
        with self.assertRaises(Issue746ReconciliationGateError):
            resolve_authorized_operator(resolver, ACCOUNT_ID)

    def test_git_snapshot_uses_attested_binary_and_neutral_configuration(self) -> None:
        backend = Mock()
        backend.inspect_private_path.return_value = SimpleNamespace(sha256="f" * 64)
        backend.launch_attested_process.return_value = SimpleNamespace(
            exit_code=0,
            stdout=b"value\n",
        )
        with patch(
            "nac_bff.activation_security_backend.get_platform_security_backend",
            return_value=backend,
        ):
            self.assertEqual(
                _git_read(
                    REPO_ROOT,
                    "rev-parse",
                    "HEAD",
                    executable=Path("C:/Git/git.exe"),
                    executable_sha256="f" * 64,
                ),
                "value",
            )
        spec = backend.launch_attested_process.call_args.args[0]
        self.assertIn("--no-replace-objects", spec.arguments)
        self.assertIn("core.fsmonitor=false", spec.arguments)
        self.assertEqual(spec.environment["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(spec.environment["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertNotIn("PATH", spec.environment)
        self.assertTrue(spec.credential_write_guard)

    def test_git_snapshot_rejects_digest_not_bound_by_resolver(self) -> None:
        backend = Mock()
        backend.inspect_private_path.return_value = SimpleNamespace(sha256="e" * 64)
        with patch(
            "nac_bff.activation_security_backend.get_platform_security_backend",
            return_value=backend,
        ):
            with self.assertRaises(Issue746ReconciliationGateError):
                _git_read(
                    REPO_ROOT,
                    "rev-parse",
                    "HEAD",
                    executable=Path("C:/Git/git.exe"),
                    executable_sha256="f" * 64,
                )
        backend.launch_attested_process.assert_not_called()

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

    def test_same_login_on_non_github_provider_cannot_authorize_comment(self) -> None:
        with self.assertRaises(Issue746ReconciliationGateError) as raised:
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
                verify_issue746_readonly_reconciliation_gate(
                    repo_root=Mock(),
                    protected_identity_resolver_file=Mock(),
                    protected_identity_resolver_sha256=RESOLVER_SHA256,
                    operator_account_id="nvidia-gitlab:owner",
                    owner_solo_approval_reference=REFERENCE,
                    github_reader=_Reader(),
                )
        self.assertEqual(raised.exception.code, GATE_CLOSED)

    def test_missing_or_failed_provider_port_blocks_without_fallback(self) -> None:
        class _FailedReader:
            def read_pull_request(self, **_kwargs):
                raise PermissionError("401")

            def read_issue_comment(self, **_kwargs):
                self.fail("must not be reached")

        with self.assertRaises(Issue746ReconciliationGateError) as raised:
            self._verify(_FailedReader())
        self.assertEqual(raised.exception.code, GATE_CLOSED)
        self.assertEqual(
            raised.exception.reason, GITHUB_READ_CHANNEL_UNAVAILABLE
        )

    def test_wrong_repository_identity_blocks(self) -> None:
        reader = _Reader()
        original = reader.read_pull_request

        def wrong_repo(**kwargs):
            payload = dict(original(**kwargs))
            payload["repository"] = {"nameWithOwner": "other/NaC"}
            return payload

        reader.read_pull_request = wrong_repo
        with self.assertRaises(Issue746ReconciliationGateError):
            self._verify(reader)

    def test_comment_401_reports_exact_channel_gap_without_retry(self) -> None:
        class Reader(_Reader):
            def __init__(self):
                super().__init__()
                self.comment_attempts = 0

            def read_issue_comment(self, **_kwargs):
                self.comment_attempts += 1
                raise PermissionError("401")

        reader = Reader()
        with self.assertRaises(Issue746ReconciliationGateError) as raised:
            self._verify(reader)
        self.assertEqual(raised.exception.reason, GITHUB_READ_CHANNEL_UNAVAILABLE)
        self.assertEqual(reader.comment_attempts, 1)


if __name__ == "__main__":
    unittest.main()
