from __future__ import annotations

import json
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.auth import (  # noqa: E402
    CertificateClientCredentialsTokenProvider,
    CertificateGraphConfig,
    ClientCredentialsTokenProvider,
    GraphConfigError,
    StaticAccessTokenProvider,
    runtime_token_provider_from_env,
)


class M365GraphAuthTests(unittest.TestCase):
    def test_runtime_provider_accepts_certificate_paths(self) -> None:
        provider = runtime_token_provider_from_env(
            {
                "M365_TENANT_ID": "tenant-id",
                "M365_RUNTIME_CLIENT_ID": "client-id",
                "M365_RUNTIME_CLIENT_CERTIFICATE_PATH": "/tmp/runtime.cert.pem",
                "M365_RUNTIME_CLIENT_KEY_PATH": "/tmp/runtime.key.pem",
            }
        )

        self.assertIsInstance(provider, CertificateClientCredentialsTokenProvider)
        self.assertEqual(provider.config.tenant_id, "tenant-id")
        self.assertEqual(provider.config.client_id, "client-id")
        self.assertEqual(provider.config.certificate_path, Path("/tmp/runtime.cert.pem"))
        self.assertEqual(provider.config.private_key_path, Path("/tmp/runtime.key.pem"))
        self.assertIsNone(provider.config.private_key_password)

    def test_certificate_provider_posts_client_assertion_without_client_secret(self) -> None:
        provider = CertificateClientCredentialsTokenProvider(
            CertificateGraphConfig(
                tenant_id="tenant-id",
                client_id="client-id",
                certificate_path=Path("/tmp/runtime.cert.pem"),
                private_key_path=Path("/tmp/runtime.key.pem"),
            )
        )

        with patch("nac_m365_graph.auth._build_client_assertion", return_value="signed.jwt") as build_assertion:
            with patch("nac_m365_graph.auth.urllib.request.urlopen", return_value=_TokenResponse("graph-token")) as urlopen:
                token = provider.fetch_access_token()

        self.assertEqual(token, "graph-token")
        build_assertion.assert_called_once()
        request = urlopen.call_args.args[0]
        form = urllib.parse.parse_qs(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://login.microsoftonline.com/tenant-id/oauth2/v2.0/token")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(form["client_id"], ["client-id"])
        self.assertEqual(form["scope"], ["https://graph.microsoft.com/.default"])
        self.assertEqual(form["grant_type"], ["client_credentials"])
        self.assertEqual(
            form["client_assertion_type"],
            ["urn:ietf:params:oauth:client-assertion-type:jwt-bearer"],
        )
        self.assertEqual(form["client_assertion"], ["signed.jwt"])
        self.assertNotIn("client_secret", form)

    def test_runtime_provider_keeps_static_token_file_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            token_path = Path(tmpdir) / "runtime.token"
            token_path.write_text("static-token\n", encoding="utf-8")
            provider = runtime_token_provider_from_env(
                {
                    "M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE": str(token_path),
                }
            )

        self.assertIsInstance(provider, StaticAccessTokenProvider)
        self.assertEqual(provider.fetch_access_token(), "static-token")

    def test_runtime_provider_keeps_client_secret_mode(self) -> None:
        provider = runtime_token_provider_from_env(
            {
                "M365_TENANT_ID": "tenant-id",
                "M365_RUNTIME_CLIENT_ID": "client-id",
                "M365_RUNTIME_CLIENT_SECRET": "client-secret",
            }
        )

        self.assertIsInstance(provider, ClientCredentialsTokenProvider)
        self.assertEqual(provider.config.client_credential, "client-secret")

    def test_runtime_certificate_mode_requires_certificate_and_key_paths(self) -> None:
        with self.assertRaisesRegex(GraphConfigError, "M365_RUNTIME_CLIENT_KEY_PATH"):
            runtime_token_provider_from_env(
                {
                    "M365_TENANT_ID": "tenant-id",
                    "M365_RUNTIME_CLIENT_ID": "client-id",
                    "M365_RUNTIME_CLIENT_CERTIFICATE_PATH": "/tmp/runtime.cert.pem",
                }
            )

    def test_runtime_provider_rejects_secret_and_certificate_mix(self) -> None:
        with self.assertRaisesRegex(GraphConfigError, "one of M365_RUNTIME_CLIENT_SECRET"):
            runtime_token_provider_from_env(
                {
                    "M365_TENANT_ID": "tenant-id",
                    "M365_RUNTIME_CLIENT_ID": "client-id",
                    "M365_RUNTIME_CLIENT_SECRET": "client-secret",
                    "M365_RUNTIME_CLIENT_CERTIFICATE_PATH": "/tmp/runtime.cert.pem",
                    "M365_RUNTIME_CLIENT_KEY_PATH": "/tmp/runtime.key.pem",
                }
            )


class _TokenResponse:
    def __init__(self, token: str) -> None:
        self._token = token

    def __enter__(self) -> "_TokenResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps({"access_token": self._token}).encode("utf-8")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
