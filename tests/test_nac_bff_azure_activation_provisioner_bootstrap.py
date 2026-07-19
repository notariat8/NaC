from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from typing import Callable

from nac_bff.azure_activation import (
    PROVISIONER_CLIENT_ID,
    PROVISIONER_GRAPH_APPLICATION_ROLES,
    TENANT_ID,
)
from nac_bff.azure_activation_provisioner_bootstrap import (
    build_activation_provisioner_bootstrap,
)


class AzureBffActivationProvisionerBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / "privileged-apply-result.json"
        self.certificate = self.root / "provisioner.cert.pem"
        self.private_key = self.root / "provisioner.key.pem"
        self._write_valid_inputs()

    def _write_valid_inputs(self) -> None:
        for path in (self.state, self.certificate, self.private_key):
            if path.is_symlink() or path.exists():
                path.unlink()
        for target in self.root.glob("*.target"):
            if target.is_symlink() or target.exists():
                target.unlink()
        self.state.write_text(json.dumps(self._state_payload()), encoding="utf-8")
        self.certificate.write_text("public-certificate", encoding="utf-8")
        self.private_key.write_text("private-key-must-never-be-read", encoding="utf-8")
        self.private_key.chmod(0o600)

    @staticmethod
    def _state_payload(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": "PASSED",
            "tenantId": TENANT_ID,
            "applications": {
                "m365_provisioning_app": {
                    "displayName": "NaC M365 Provisioning",
                    "clientId": PROVISIONER_CLIENT_ID,
                    "appRoleAssignments": [
                        {
                            "permission": permission,
                            "status": "existing",
                        }
                        for permission in PROVISIONER_GRAPH_APPLICATION_ROLES
                    ],
                }
            },
        }
        payload.update(overrides)
        return payload

    def _build(self, *, env: dict[str, str] | None = None):
        return build_activation_provisioner_bootstrap(
            self.state,
            self.certificate,
            self.private_key,
            env={} if env is None else env,
        )

    def test_valid_inputs_build_redacted_certificate_overlay(self) -> None:
        result = self._build()

        self.assertEqual(result.readiness["status"], "PASSED")
        self.assertRegex(result.binding_sha256 or "", r"^[0-9a-f]{64}$")
        self.assertEqual(
            set(result.env_overlay),
            {
                "M365_TENANT_ID",
                "M365_PROVISIONER_CLIENT_ID",
                "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH",
                "M365_PROVISIONER_CLIENT_KEY_PATH",
            },
        )
        serialized = json.dumps(result.readiness)
        self.assertNotIn(TENANT_ID, serialized)
        self.assertNotIn(PROVISIONER_CLIENT_ID, serialized)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn("private-key-must-never-be-read", serialized)
        self.assertFalse(result.readiness["boundaries"]["private_key_read"])
        self.assertEqual(result.readiness["boundaries"]["provider_requests_made"], 0)
        self.assertFalse(result.readiness["boundaries"]["tenant_writes_started"])

    def test_missing_site_permission_admin_assignment_is_blocked(self) -> None:
        payload = self._state_payload()
        payload["applications"]["m365_provisioning_app"][
            "appRoleAssignments"
        ] = []
        self.state.write_text(json.dumps(payload), encoding="utf-8")

        result = self._build()

        self.assertEqual(result.readiness["status"], "BLOCKED")
        self.assertEqual(
            result.readiness["error_code"],
            "PROVISIONER_SITE_PERMISSION_GRAPH_ROLE_MISSING",
        )
        self.assertEqual(result.readiness["boundaries"]["provider_requests_made"], 0)
        self.assertFalse(result.readiness["boundaries"]["tenant_writes_started"])

    def test_broader_provisioner_role_is_blocked_before_provider_access(self) -> None:
        payload = self._state_payload()
        payload["applications"]["m365_provisioning_app"][
            "appRoleAssignments"
        ].append(
            {
                "permission": "Directory.ReadWrite.All",
                "status": "existing",
            }
        )
        self.state.write_text(json.dumps(payload), encoding="utf-8")

        result = self._build()

        self.assertEqual(result.readiness["status"], "BLOCKED")
        self.assertEqual(
            result.readiness["error_code"],
            "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH",
        )
        self.assertEqual(result.readiness["boundaries"]["provider_requests_made"], 0)
        self.assertFalse(result.readiness["boundaries"]["tenant_writes_started"])

    def test_malformed_provisioner_role_is_blocked_without_crashing(self) -> None:
        payload = self._state_payload()
        payload["applications"]["m365_provisioning_app"][
            "appRoleAssignments"
        ][0]["permission"] = []
        self.state.write_text(json.dumps(payload), encoding="utf-8")

        result = self._build()

        self.assertEqual(result.readiness["status"], "BLOCKED")
        self.assertEqual(
            result.readiness["error_code"],
            "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH",
        )
        self.assertEqual(result.readiness["boundaries"]["provider_requests_made"], 0)
        self.assertFalse(result.readiness["boundaries"]["tenant_writes_started"])

    def test_extra_malformed_assignment_row_is_not_ignored(self) -> None:
        payload = self._state_payload()
        payload["applications"]["m365_provisioning_app"][
            "appRoleAssignments"
        ].append([])
        self.state.write_text(json.dumps(payload), encoding="utf-8")

        result = self._build()

        self.assertEqual(result.readiness["status"], "BLOCKED")
        self.assertEqual(
            result.readiness["error_code"],
            "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH",
        )
        self.assertEqual(result.readiness["boundaries"]["provider_requests_made"], 0)
        self.assertFalse(result.readiness["boundaries"]["tenant_writes_started"])

    def test_binding_is_deterministic_and_changes_with_state_or_any_path(self) -> None:
        baseline = self._build()
        repeated = self._build()
        self.assertEqual(baseline.binding_sha256, repeated.binding_sha256)

        self.state.write_text(
            json.dumps({**self._state_payload(), "issuedAt": "2026-07-19T12:00:00Z"}),
            encoding="utf-8",
        )
        changed_state = self._build()
        self.assertNotEqual(baseline.binding_sha256, changed_state.binding_sha256)

        self._write_valid_inputs()
        alternate_state = self.root / "alternate-state.json"
        alternate_state.write_text(
            json.dumps(self._state_payload()),
            encoding="utf-8",
        )
        alternate_certificate = self.root / "alternate-certificate.pem"
        alternate_certificate.write_text("public-certificate", encoding="utf-8")
        alternate_private_key = self.root / "alternate-private-key.pem"
        alternate_private_key.write_text(
            "private-key-must-never-be-read",
            encoding="utf-8",
        )
        alternate_private_key.chmod(0o600)
        for paths in (
            (alternate_state, self.certificate, self.private_key),
            (self.state, alternate_certificate, self.private_key),
            (self.state, self.certificate, alternate_private_key),
        ):
            with self.subTest(paths=tuple(path.name for path in paths)):
                result = build_activation_provisioner_bootstrap(*paths, env={})
                self.assertEqual(result.readiness["status"], "PASSED")
                self.assertNotEqual(baseline.binding_sha256, result.binding_sha256)

    def test_oversized_state_is_rejected_before_json_decode(self) -> None:
        self.state.write_bytes(b"x" * (128 * 1024 + 1))

        result = self._build()

        self.assertEqual(result.readiness["status"], "BLOCKED")
        self.assertEqual(
            result.readiness["error_code"],
            "PROVISIONER_STATE_FILE_UNTRUSTED",
        )
        self.assertIsNone(result.binding_sha256)

    def test_state_swap_to_symlink_between_lstat_and_open_is_rejected(self) -> None:
        original_open = os.open
        replacement = self.root / "replacement-state.json"
        replacement.write_text(json.dumps(self._state_payload()), encoding="utf-8")
        swapped = False

        def swap_before_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if Path(path) == self.state and not swapped:
                self.state.unlink()
                self.state.symlink_to(replacement)
                swapped = True
            return original_open(path, flags, *args, **kwargs)

        with patch(
            "nac_bff.azure_activation_provisioner_bootstrap.os.open",
            side_effect=swap_before_open,
        ):
            result = self._build()

        self.assertTrue(swapped)
        self.assertEqual(result.readiness["status"], "BLOCKED")
        self.assertEqual(
            result.readiness["error_code"],
            "PROVISIONER_STATE_FILE_UNTRUSTED",
        )

    def test_state_snapshot_change_during_read_is_rejected(self) -> None:
        with patch(
            "nac_bff.azure_activation_provisioner_bootstrap._same_file_snapshot",
            side_effect=(True, False),
        ):
            result = self._build()

        self.assertEqual(result.readiness["status"], "BLOCKED")
        self.assertEqual(
            result.readiness["error_code"],
            "PROVISIONER_STATE_FILE_UNTRUSTED",
        )

    def test_explicit_empty_env_does_not_inherit_secret_process_env(self) -> None:
        with patch.dict(
            os.environ,
            {"M365_PROVISIONER_CLIENT_SECRET": "ambient-secret"},
            clear=False,
        ):
            result = self._build(env={})

        self.assertEqual(result.readiness["status"], "PASSED")
        self.assertNotIn("ambient-secret", json.dumps(result.readiness))

    def test_each_explicit_environment_binding_must_match_exactly(self) -> None:
        cases = (
            ("M365_TENANT_ID", "wrong-tenant"),
            ("M365_PROVISIONER_CLIENT_ID", "wrong-client"),
            (
                "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH",
                str(self.root / "wrong-certificate.pem"),
            ),
            (
                "M365_PROVISIONER_CLIENT_KEY_PATH",
                str(self.root / "wrong-private-key.pem"),
            ),
        )
        for variable, value in cases:
            with self.subTest(variable=variable):
                result = self._build(env={variable: value})
                self.assertEqual(result.readiness["status"], "BLOCKED")
                self.assertEqual(
                    result.readiness["error_code"],
                    "PROVISIONER_ENV_BINDING_MISMATCH",
                )
                self.assertEqual(result.env_overlay, {})
                self.assertNotIn(value, json.dumps(result.readiness))
                self.assertFalse(
                    result.readiness["boundaries"]["private_key_read"]
                )
                self.assertEqual(
                    result.readiness["boundaries"]["provider_requests_made"],
                    0,
                )

    def test_wrong_state_bindings_are_blocked_and_redacted(self) -> None:
        cases = (
            {"status": "FAILED"},
            {"tenantId": "wrong-tenant"},
            {
                "applications": {
                    "m365_provisioning_app": {
                        "displayName": "Wrong App",
                        "clientId": PROVISIONER_CLIENT_ID,
                    }
                }
            },
            {
                "applications": {
                    "m365_provisioning_app": {
                        "displayName": "NaC M365 Provisioning",
                        "clientId": "wrong-client",
                    }
                }
            },
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.state.write_text(
                    json.dumps(self._state_payload(**overrides)), encoding="utf-8"
                )
                result = self._build()
                self.assertEqual(result.readiness["status"], "BLOCKED")
                self.assertEqual(
                    result.readiness["error_code"],
                    "PROVISIONER_STATE_BINDING_MISMATCH",
                )
                self.assertEqual(result.env_overlay, {})
                self.assertNotIn("wrong-", json.dumps(result.readiness))

    def test_secret_or_non_v1_graph_modes_are_blocked(self) -> None:
        cases = (
            (
                {"M365_PROVISIONER_CLIENT_SECRET": "secret-value"},
                "PROVISIONER_CERTIFICATE_MODE_REQUIRED",
            ),
            (
                {"M365_GRAPH_ACCESS_TOKEN": "token-value"},
                "PROVISIONER_CERTIFICATE_MODE_REQUIRED",
            ),
            (
                {"M365_GRAPH_BASE_URL": "https://graph.microsoft.com/beta"},
                "PROVISIONER_GRAPH_BASE_URL_INVALID",
            ),
        )
        for env, code in cases:
            with self.subTest(code=code):
                result = self._build(env=env)
                self.assertEqual(result.readiness["status"], "BLOCKED")
                self.assertEqual(result.readiness["error_code"], code)
                self.assertNotIn(next(iter(env.values())), json.dumps(result.readiness))

    def test_missing_untrusted_or_symlink_inputs_are_blocked(self) -> None:
        cases: list[tuple[str, str, Callable[[], None]]] = [
            (
                "missing-state",
                "PROVISIONER_STATE_FILE_UNTRUSTED",
                lambda: self.state.unlink(),
            ),
            (
                "missing-certificate",
                "PROVISIONER_CERTIFICATE_FILE_UNTRUSTED",
                lambda: self.certificate.unlink(),
            ),
            (
                "missing-key",
                "PROVISIONER_PRIVATE_KEY_FILE_UNTRUSTED",
                lambda: self.private_key.unlink(),
            ),
            (
                "writable-state",
                "PROVISIONER_STATE_FILE_UNTRUSTED",
                lambda: self.state.chmod(0o664),
            ),
            (
                "writable-certificate",
                "PROVISIONER_CERTIFICATE_FILE_UNTRUSTED",
                lambda: self.certificate.chmod(0o666),
            ),
            (
                "insecure-key-mode",
                "PROVISIONER_PRIVATE_KEY_FILE_UNTRUSTED",
                lambda: self.private_key.chmod(0o644),
            ),
        ]
        for name, code, mutate in cases:
            with self.subTest(name=name):
                self._write_valid_inputs()
                mutate()
                result = self._build()
                self.assertEqual(result.readiness["status"], "BLOCKED")
                self.assertEqual(result.readiness["error_code"], code)
                self.assertEqual(result.env_overlay, {})

    def test_each_symlink_input_is_rejected(self) -> None:
        for attribute, code in (
            ("state", "PROVISIONER_STATE_FILE_UNTRUSTED"),
            ("certificate", "PROVISIONER_CERTIFICATE_FILE_UNTRUSTED"),
            ("private_key", "PROVISIONER_PRIVATE_KEY_FILE_UNTRUSTED"),
        ):
            with self.subTest(attribute=attribute):
                self._write_valid_inputs()
                path = getattr(self, attribute)
                target = path.with_suffix(path.suffix + ".target")
                if target.exists():
                    target.unlink()
                path.rename(target)
                path.symlink_to(target)
                result = self._build()
                self.assertEqual(result.readiness["status"], "BLOCKED")
                self.assertEqual(result.readiness["error_code"], code)

    def test_private_key_content_is_never_read(self) -> None:
        original_read_text = Path.read_text
        original_open = os.open

        def guarded_open(path, flags, *args, **kwargs):
            if Path(path) == self.private_key:
                raise AssertionError(
                    "private key content must remain unopened"
                )
            return original_open(path, flags, *args, **kwargs)

        def guarded_read_text(path: Path, *args, **kwargs):
            if path == self.private_key:
                raise AssertionError("private key content must remain unread")
            return original_read_text(path, *args, **kwargs)

        with (
            patch("os.open", side_effect=guarded_open),
            patch.object(Path, "read_text", autospec=True, side_effect=guarded_read_text),
            patch.object(
                Path,
                "read_bytes",
                autospec=True,
                side_effect=AssertionError("private key content must remain unread"),
            ),
        ):
            result = self._build()

        self.assertEqual(result.readiness["status"], "PASSED")
        self.assertFalse(result.readiness["boundaries"]["private_key_read"])


if __name__ == "__main__":
    unittest.main()
