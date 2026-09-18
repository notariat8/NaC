from __future__ import annotations

import os
import unittest
from unittest import mock

from nac_bff.activation_security_backend import (
    PlatformSecurityBackendUnavailable,
    get_platform_security_backend,
)
from nac_bff import azure_activation_contract as contract
from nac_bff import azure_activation_facade as facade
from nac_bff.azure_activation_contract import ActivationStepError


class PlatformSecurityBackendSelectionTests(unittest.TestCase):
    def test_backend_selection_is_derived_from_runtime_not_environment(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "NAC_PLATFORM_SECURITY_BACKEND": "windows",
                "NAC_ALLOW_INCOMPLETE_SECURITY_BACKEND": "1",
            },
            clear=False,
        ), mock.patch("nac_bff.activation_security_backend.os.name", "unsupported"):
            with self.assertRaises(PlatformSecurityBackendUnavailable):
                get_platform_security_backend()

    def test_backend_must_report_every_required_capability(self) -> None:
        if os.name != "nt":
            with self.assertRaises(PlatformSecurityBackendUnavailable):
                get_platform_security_backend()
            return
        backend = get_platform_security_backend()
        capabilities = backend.capabilities()
        self.assertTrue(capabilities.complete, capabilities.missing)
        self.assertEqual(capabilities.missing, ())

    def test_posix_primitives_do_not_enable_complete_live_backend(self) -> None:
        with (
            mock.patch.object(contract.os, "name", "posix"),
            mock.patch.object(contract.sys, "platform", "linux"),
            mock.patch.object(
                contract,
                "get_platform_security_backend",
                side_effect=PlatformSecurityBackendUnavailable(),
            ),
        ):
            self.assertFalse(contract.platform_security_backend_available())
            with self.assertRaisesRegex(
                ActivationStepError, "^PLATFORM_SECURITY_BACKEND_UNAVAILABLE$"
            ):
                contract.require_platform_security_backend()

    def test_every_live_facade_edge_stops_at_complete_backend_gate(self) -> None:
        edges = (
            facade.run_azure_bff_live_activation,
            facade.reconcile_azure_bff_live_activation_lock,
            facade.build_live_activation_execution_port,
            facade.build_interruption_reconciliation_ports,
            facade.build_function_deployment_reconciliation_ports,
        )
        for edge in edges:
            with self.subTest(edge=edge.__name__), mock.patch.object(
                facade,
                "require_platform_security_backend",
                side_effect=ActivationStepError(
                    "PLATFORM_SECURITY_BACKEND_UNAVAILABLE"
                ),
            ):
                with self.assertRaisesRegex(
                    ActivationStepError, "^PLATFORM_SECURITY_BACKEND_UNAVAILABLE$"
                ):
                    edge()


if __name__ == "__main__":
    unittest.main()
