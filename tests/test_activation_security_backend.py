from __future__ import annotations

import unittest
from unittest import mock

from nac_bff.activation_security_backend import (
    PlatformSecurityBackendUnavailable,
    get_platform_security_backend,
)


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
        backend = get_platform_security_backend()
        capabilities = backend.capabilities()
        self.assertTrue(capabilities.complete, capabilities.missing)
        self.assertEqual(capabilities.missing, ())


if __name__ == "__main__":
    unittest.main()
