from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nac_bff.current_state_access_gate import (
    BLOCKED_ACCOUNT_BINDING,
    BLOCKED_SINGLE_PRINCIPAL,
    CurrentStateAccessGateError,
    GateInput,
    authorize_synthetic_current_state_run,
    authorize_current_state_run,
    consume_current_state_run_gate,
)


def _input(**overrides: object) -> GateInput:
    target_payload_sha256 = hashlib.sha256(
        json.dumps({"opaque": "bound"}, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    values: dict[str, object] = {
        "issue": 748,
        "pr": 749,
        "base_pr": 747,
        "base_merge_commit": "80bf813375d7fc2ab292dfdbcc1db447fdb6684a",
        "base_tree": "007e277ca5643f7cb63355961fd0422d92fd4b87",
        "head": "a" * 40,
        "tree": "b" * 40,
        "head_descends_from_base": True,
        "resolver_sha256": "c" * 64,
        "operator_account_id": "microsoft:owner-primary",
        "operator_principal_id": "person:owner",
        "authorized_account_id": "microsoft:owner-primary",
        "authorized_principal_id": "person:owner",
        "provider": "microsoft",
        "tenant_binding_sha256": "d" * 64,
        "account_permission_sha256": "4" * 64,
        "target_binding_sha256": "e" * 64,
        "target_payload_sha256": target_payload_sha256,
        "dpa_avv_binding_sha256": "f" * 64,
        "contract_sha256": "1" * 64,
        "toolchain_sha256": "2" * 64,
        "approval_sha256": "3" * 64,
        "run_nonce_sha256": "6" * 64,
        "approval_mode": "OWNER_SOLO_APPROVAL",
        "four_eyes_satisfied": False,
        "external_two_person_required": False,
        "external_requirement_citation": None,
        "required_checks_successful": True,
        "required_checks_sha256": "5" * 64,
        "worktree_clean": True,
        "credential_write_guard_active": True,
        "evidence_root_binding_sha256": hashlib.sha256(
            str(Path("C:/protected/issue748").resolve()).encode("utf-8")
        ).hexdigest(),
    }
    values.update(overrides)
    return GateInput(**values)


class CurrentStateAccessGateTests(unittest.TestCase):
    def test_unverified_caller_input_cannot_create_runtime_authorization(self) -> None:
        with self.assertRaises(CurrentStateAccessGateError):
            authorize_current_state_run(_input())

    def test_valid_solo_owner_gate_returns_sealed_authorization(self) -> None:
        authorization = authorize_synthetic_current_state_run(_input())
        authorization.verify_for_read(
            account_id="microsoft:owner-primary",
            principal_id="person:owner",
            target_binding_sha256="e" * 64,
            target_payload_sha256=authorization.target_payload_sha256,
            evidence_binding_sha256=authorization.authorization_sha256,
        )
        self.assertFalse(authorization.four_eyes_satisfied)

    def test_other_account_of_same_principal_does_not_inherit_permission(self) -> None:
        with self.assertRaises(CurrentStateAccessGateError) as raised:
            authorize_synthetic_current_state_run(
                _input(operator_account_id="microsoft:owner-secondary")
            )
        self.assertEqual(raised.exception.code, BLOCKED_ACCOUNT_BINDING)

    def test_cited_two_person_duty_blocks_single_principal(self) -> None:
        with self.assertRaises(CurrentStateAccessGateError) as raised:
            authorize_synthetic_current_state_run(
                _input(
                    external_two_person_required=True,
                    external_requirement_citation="binding-policy:section-4",
                )
            )
        self.assertEqual(raised.exception.code, BLOCKED_SINGLE_PRINCIPAL)

    def test_uncited_two_person_claim_is_rejected(self) -> None:
        with self.assertRaises(CurrentStateAccessGateError):
            authorize_synthetic_current_state_run(
                _input(external_two_person_required=True)
            )

    def test_all_binding_and_pre_io_failures_block(self) -> None:
        invalid = (
            {"issue": 739},
            {"pr": 747},
            {"base_pr": 746},
            {"head_descends_from_base": False},
            {"required_checks_successful": False},
            {"worktree_clean": False},
            {"credential_write_guard_active": False},
            {"provider": "github"},
            {"dpa_avv_binding_sha256": ""},
            {"approval_mode": "FOUR_EYES_APPROVAL"},
            {"four_eyes_satisfied": True},
        )
        for changes in invalid:
            with self.subTest(changes=changes):
                with self.assertRaises(CurrentStateAccessGateError):
                    authorize_synthetic_current_state_run(_input(**changes))

    def test_authorization_rejects_per_read_drift(self) -> None:
        authorization = authorize_synthetic_current_state_run(_input())
        for kwargs in (
            {"account_id": "microsoft:owner-secondary", "principal_id": "person:owner", "target_binding_sha256": "e" * 64, "target_payload_sha256": authorization.target_payload_sha256, "evidence_binding_sha256": authorization.authorization_sha256},
            {"account_id": "microsoft:owner-primary", "principal_id": "person:other", "target_binding_sha256": "e" * 64, "target_payload_sha256": authorization.target_payload_sha256, "evidence_binding_sha256": authorization.authorization_sha256},
            {"account_id": "microsoft:owner-primary", "principal_id": "person:owner", "target_binding_sha256": "9" * 64, "target_payload_sha256": authorization.target_payload_sha256, "evidence_binding_sha256": authorization.authorization_sha256},
            {"account_id": "microsoft:owner-primary", "principal_id": "person:owner", "target_binding_sha256": "e" * 64, "target_payload_sha256": "8" * 64, "evidence_binding_sha256": authorization.authorization_sha256},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(CurrentStateAccessGateError):
                    authorization.verify_for_read(**kwargs)

    def test_synthetic_authorization_cannot_consume_production_gate(self) -> None:
        authorization = authorize_synthetic_current_state_run(_input())
        backend = _MemorySecurityBackend()
        with self.assertRaises(CurrentStateAccessGateError) as raised:
            consume_current_state_run_gate(
                authorization,
                evidence_root=Path("C:/protected/issue748"),
                backend=backend,
            )
        self.assertEqual(raised.exception.code, "CURRENT_STATE_ACCESS_GATE_CLOSED")
        self.assertEqual(backend.lock_targets, [])
        self.assertEqual(backend.session.files, {})


class _MemorySession:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.closed = False

    def create_exclusive(self, name: str, payload: bytes):
        if name in self.files:
            raise FileExistsError(name)
        self.files[name] = payload
        return SimpleNamespace(sha256="9" * 64)

    def close(self) -> None:
        self.closed = True


class _MemoryLock:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _MemorySecurityBackend:
    def __init__(self) -> None:
        self.session = _MemorySession()
        self.lock_targets: list[str] = []

    def open_secure_directory(self, path, *, create, **kwargs):
        self.opened = (path, create, kwargs)
        return self.session

    def acquire_run_lock(self, target_binding):
        self.lock_targets.append(target_binding)
        return _MemoryLock()


if __name__ == "__main__":
    unittest.main()
