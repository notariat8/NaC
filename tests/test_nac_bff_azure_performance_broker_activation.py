from __future__ import annotations

import hashlib
import unittest

from nac_bff import azure_live_commands
from nac_bff.azure_performance_broker_activation import (
    BrokerFunctionActivationError,
    BrokerFunctionSettingsPort,
    SETTING_NAMES,
    build_broker_function_settings,
)


class _Azure:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.values: dict[str, str] = {}

    def run(self, argv: object) -> dict[str, object]:
        command = list(argv)  # type: ignore[arg-type]
        self.commands.append(command)
        if command[:4] == ["functionapp", "config", "appsettings", "set"]:
            start = command.index("--settings") + 1
            end = command.index("--subscription")
            for item in command[start:end]:
                name, value = item.split("=", 1)
                self.values[name] = value
            return {"ok": True, "value": []}
        return {
            "ok": True,
            "value": [
                {"name": "UNRELATED_SETTING", "value": "preserved"},
                *[
                    {"name": name, "value": value}
                    for name, value in sorted(self.values.items())
                ],
            ],
        }


def _settings():
    certificate = b"public-certificate-material" * 3
    return build_broker_function_settings(
        tenant_id="870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
        actor_id="11111111-2222-4333-8444-555555555555",
        owner_binding_sha256="1" * 64,
        commit_sha="2" * 40,
        tree_sha="3" * 64,
        function_package_sha256="4" * 64,
        plan_sha256="5" * 64,
        target_binding_sha256="6" * 64,
        coordination_storage_account_name="naccoord1234567890",
        storage_binding_id="nac-performance-123",
        storage_attestation=b"attestation" * 8,
        ticket_certificate=certificate,
        ticket_certificate_sha256=hashlib.sha256(certificate).hexdigest(),
    )


class BrokerFunctionActivationTests(unittest.TestCase):
    def test_fixed_settings_are_merged_and_read_back_without_values(self) -> None:
        azure = _Azure()

        result = BrokerFunctionSettingsPort(azure).configure_and_verify(_settings())

        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["setting_count"], len(SETTING_NAMES))
        self.assertFalse(result["values_emitted"])
        self.assertEqual(len(azure.commands), 2)
        self.assertEqual(
            azure.commands[0][:4],
            ["functionapp", "config", "appsettings", "set"],
        )
        self.assertEqual(
            azure.commands[1][:4],
            ["functionapp", "config", "appsettings", "list"],
        )
        for command in azure.commands:
            _validated, _family, code = azure_live_commands._validated_command(
                command
            )
            self.assertEqual(code, "AZURE_CLI_OK")

    def test_complete_restart_verifies_current_settings_without_set(self) -> None:
        azure = _Azure()
        settings = _settings()
        azure.values.update(settings.values)

        result = BrokerFunctionSettingsPort(azure).verify_current(settings)

        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(len(azure.commands), 1)
        self.assertEqual(
            azure.commands[0][:4],
            ["functionapp", "config", "appsettings", "list"],
        )

    def test_command_boundary_rejects_incomplete_or_unknown_settings(self) -> None:
        azure = _Azure()
        BrokerFunctionSettingsPort(azure).configure_and_verify(_settings())
        valid = azure.commands[0]
        settings_index = valid.index("--settings") + 1
        subscription_index = valid.index("--subscription")
        blocked = (
            [*valid[:settings_index], *valid[settings_index + 1 :]],
            [
                *valid[:subscription_index],
                "NAC_BFF_PERFORMANCE_LEASE_UNBOUND=true",
                *valid[subscription_index:],
            ],
        )
        for command in blocked:
            with self.subTest(command=command):
                self.assertEqual(
                    azure_live_commands._validated_command(command)[2],
                    "AZURE_CLI_COMMAND_BLOCKED",
                )

    def test_unknown_performance_setting_fails_readback(self) -> None:
        azure = _Azure()
        original = azure.run

        def run(argv: object) -> dict[str, object]:
            result = original(argv)
            if list(argv)[:4] == [  # type: ignore[arg-type]
                "functionapp",
                "config",
                "appsettings",
                "list",
            ]:
                result["value"].append(  # type: ignore[union-attr]
                    {
                        "name": "NAC_BFF_PERFORMANCE_LEASE_UNBOUND",
                        "value": "true",
                    }
                )
            return result

        azure.run = run  # type: ignore[method-assign]
        with self.assertRaisesRegex(
            BrokerFunctionActivationError,
            "BROKER_FUNCTION_SETTINGS_READBACK_MISMATCH",
        ):
            BrokerFunctionSettingsPort(azure).configure_and_verify(_settings())

    def test_tampered_certificate_binding_fails_before_cli(self) -> None:
        settings = _settings()
        values = dict(settings.values)
        values["NAC_BFF_PERFORMANCE_LEASE_TICKET_CERTIFICATE_SHA256"] = "f" * 64
        tampered = type(settings)(values, settings.settings_sha256)
        azure = _Azure()

        with self.assertRaisesRegex(
            BrokerFunctionActivationError, "BROKER_FUNCTION_SETTINGS_INVALID"
        ):
            BrokerFunctionSettingsPort(azure).configure_and_verify(tampered)
        self.assertEqual(azure.commands, [])

    def test_cli_failure_is_redacted(self) -> None:
        class Failure:
            def run(self, _argv: object) -> dict[str, object]:
                return {"ok": False, "value": {"secret": "must-not-leak"}}

        with self.assertRaisesRegex(
            BrokerFunctionActivationError, "^BROKER_FUNCTION_AZURE_FAILED$"
        ):
            BrokerFunctionSettingsPort(Failure()).configure_and_verify(_settings())

    def test_identity_settings_require_canonical_uuids_and_same_owner(self) -> None:
        settings = _settings()
        for name, value in (
            ("NAC_BFF_PERFORMANCE_LEASE_TENANT_ID", "not-a-uuid"),
            (
                "NAC_BFF_PERFORMANCE_LEASE_OWNER_SUBJECT",
                "99999999-2222-4333-8444-555555555555",
            ),
        ):
            with self.subTest(name=name):
                values = dict(settings.values)
                values[name] = value
                tampered = type(settings)(values, settings.settings_sha256)
                with self.assertRaisesRegex(
                    BrokerFunctionActivationError,
                    "^BROKER_FUNCTION_SETTINGS_INVALID$",
                ):
                    BrokerFunctionSettingsPort(_Azure()).configure_and_verify(
                        tampered
                    )


if __name__ == "__main__":
    unittest.main()
