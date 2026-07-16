from __future__ import annotations

import base64
import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class GraphConfigError(ValueError):
    """Raised when required Microsoft 365 Graph configuration is missing."""


@dataclass(frozen=True, slots=True)
class GraphConfig:
    tenant_id: str
    client_id: str
    client_credential: str
    graph_base_url: str = "https://graph.microsoft.com/v1.0"

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        client_id_name: str = "M365_PROVISIONER_CLIENT_ID",
        client_credential_name: str = "M365_PROVISIONER_CLIENT_SECRET",
    ) -> "GraphConfig":
        values = env or os.environ
        tenant_id = values.get("M365_TENANT_ID", "").strip()
        client_id = values.get(client_id_name, "").strip()
        client_credential = values.get(client_credential_name, "").strip()
        graph_base_url = values.get("M365_GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0").strip()

        missing = [
            name
            for name, value in (
                ("M365_TENANT_ID", tenant_id),
                (client_id_name, client_id),
                (client_credential_name, client_credential),
            )
            if not value
        ]
        if missing:
            raise GraphConfigError("missing Microsoft 365 environment values: " + ", ".join(missing))
        if graph_base_url != "https://graph.microsoft.com/v1.0":
            raise GraphConfigError("M365_GRAPH_BASE_URL must be https://graph.microsoft.com/v1.0")
        return cls(
            tenant_id=tenant_id,
            client_id=client_id,
            client_credential=client_credential,
            graph_base_url=graph_base_url,
        )


@dataclass(frozen=True, slots=True)
class CertificateGraphConfig:
    tenant_id: str
    client_id: str
    certificate_path: Path
    private_key_path: Path
    private_key_password: str | None = None
    graph_base_url: str = "https://graph.microsoft.com/v1.0"

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        client_id_name: str = "M365_PROVISIONER_CLIENT_ID",
        certificate_path_name: str = "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH",
        private_key_path_name: str = "M365_PROVISIONER_CLIENT_KEY_PATH",
        private_key_password_name: str = "M365_PROVISIONER_CLIENT_KEY_PASSWORD",
    ) -> "CertificateGraphConfig":
        values = env or os.environ
        tenant_id = values.get("M365_TENANT_ID", "").strip()
        client_id = values.get(client_id_name, "").strip()
        certificate_path = values.get(certificate_path_name, "").strip()
        private_key_path = values.get(private_key_path_name, "").strip()
        private_key_password = values.get(private_key_password_name, "").strip() or None
        graph_base_url = values.get("M365_GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0").strip()

        missing = [
            name
            for name, value in (
                ("M365_TENANT_ID", tenant_id),
                (client_id_name, client_id),
                (certificate_path_name, certificate_path),
                (private_key_path_name, private_key_path),
            )
            if not value
        ]
        if missing:
            raise GraphConfigError("missing Microsoft 365 certificate environment values: " + ", ".join(missing))
        if graph_base_url != "https://graph.microsoft.com/v1.0":
            raise GraphConfigError("M365_GRAPH_BASE_URL must be https://graph.microsoft.com/v1.0")
        return cls(
            tenant_id,
            client_id,
            Path(certificate_path).expanduser(),
            Path(private_key_path).expanduser(),
            private_key_password,
            graph_base_url,
        )


class ClientCredentialsTokenProvider:
    def __init__(self, config: GraphConfig):
        self.config = config

    def fetch_access_token(self) -> str:
        endpoint = _token_endpoint(self.config.tenant_id)
        return _post_token_form(
            endpoint,
            {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_credential,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
        )


class CertificateClientCredentialsTokenProvider:
    def __init__(self, config: CertificateGraphConfig):
        self.config = config

    def fetch_access_token(self) -> str:
        endpoint = _token_endpoint(self.config.tenant_id)
        return _post_token_form(
            endpoint,
            {
                "client_id": self.config.client_id,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": _build_client_assertion(self.config, endpoint),
            },
        )


class StaticAccessTokenProvider:
    def __init__(self, token: str):
        token = token.strip()
        if not token:
            raise GraphConfigError("Microsoft Graph access token is empty")
        self._token = token

    def fetch_access_token(self) -> str:
        return self._token


def token_provider_from_env(
    env: Mapping[str, str] | None = None,
    *,
    token_name: str = "M365_GRAPH_ACCESS_TOKEN",
    token_file_name: str = "M365_GRAPH_ACCESS_TOKEN_FILE",
    client_id_name: str = "M365_PROVISIONER_CLIENT_ID",
    client_credential_name: str = "M365_PROVISIONER_CLIENT_SECRET",
    certificate_path_name: str = "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH",
    private_key_path_name: str = "M365_PROVISIONER_CLIENT_KEY_PATH",
    private_key_password_name: str = "M365_PROVISIONER_CLIENT_KEY_PASSWORD",
) -> ClientCredentialsTokenProvider | CertificateClientCredentialsTokenProvider | StaticAccessTokenProvider:
    values = env or os.environ
    inline_token = values.get(token_name, "").strip()
    token_file = values.get(token_file_name, "").strip()
    client_secret = values.get(client_credential_name, "").strip()
    certificate_path = values.get(certificate_path_name, "").strip()
    private_key_path = values.get(private_key_path_name, "").strip()
    if inline_token and token_file:
        raise GraphConfigError(f"set only one of {token_name} or {token_file_name}")
    if (inline_token or token_file) and (client_secret or certificate_path or private_key_path):
        raise GraphConfigError(
            "set only one Microsoft 365 credential mode: access token, client secret or client certificate"
        )
    if token_file:
        try:
            return StaticAccessTokenProvider(Path(token_file).expanduser().read_text(encoding="utf-8"))
        except OSError as exc:
            raise GraphConfigError(f"cannot read {token_file_name}: {exc}") from exc
    if inline_token:
        return StaticAccessTokenProvider(inline_token)
    if certificate_path or private_key_path:
        if client_secret:
            raise GraphConfigError(
                f"set only one of {client_credential_name} or {certificate_path_name}/{private_key_path_name}"
            )
        return CertificateClientCredentialsTokenProvider(
            CertificateGraphConfig.from_env(
                values,
                client_id_name=client_id_name,
                certificate_path_name=certificate_path_name,
                private_key_path_name=private_key_path_name,
                private_key_password_name=private_key_password_name,
            )
        )
    return ClientCredentialsTokenProvider(
        GraphConfig.from_env(
            values,
            client_id_name=client_id_name,
            client_credential_name=client_credential_name,
        )
    )


def runtime_token_provider_from_env(
    env: Mapping[str, str] | None = None,
) -> ClientCredentialsTokenProvider | StaticAccessTokenProvider:
    return token_provider_from_env(
        env,
        token_name="M365_RUNTIME_GRAPH_ACCESS_TOKEN",
        token_file_name="M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE",
        client_id_name="M365_RUNTIME_CLIENT_ID",
        client_credential_name="M365_RUNTIME_CLIENT_SECRET",
        certificate_path_name="M365_RUNTIME_CLIENT_CERTIFICATE_PATH",
        private_key_path_name="M365_RUNTIME_CLIENT_KEY_PATH",
        private_key_password_name="M365_RUNTIME_CLIENT_KEY_PASSWORD",
    )


def _token_endpoint(tenant_id: str) -> str:
    return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"


def _post_token_form(endpoint: str, form: dict[str, str]) -> str:
    request = urllib.request.Request(
        endpoint,
        data=urllib.parse.urlencode(form).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise GraphConfigError("token response did not contain access_token")
    return token


def _build_client_assertion(config: CertificateGraphConfig, token_endpoint: str) -> str:
    try:
        key_bytes = config.private_key_path.read_bytes()
        cert_bytes = config.certificate_path.read_bytes()
    except OSError as exc:
        raise GraphConfigError(f"cannot read Microsoft 365 certificate credential file: {exc}") from exc

    return _build_client_assertion_from_bytes(
        config,
        token_endpoint,
        certificate_bytes=cert_bytes,
        private_key_bytes=key_bytes,
    )


def _build_client_assertion_from_bytes(
    config: CertificateGraphConfig,
    token_endpoint: str,
    *,
    certificate_bytes: bytes,
    private_key_bytes: bytes,
) -> str:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as exc:
        raise GraphConfigError(
            "cryptography is required for Microsoft 365 certificate authentication"
        ) from exc

    password = config.private_key_password.encode("utf-8") if config.private_key_password else None
    try:
        private_key = serialization.load_pem_private_key(
            private_key_bytes, **{"password": password}
        )
    except (TypeError, ValueError) as exc:
        raise GraphConfigError("cannot load Microsoft 365 client private key") from exc

    try:
        certificate = x509.load_pem_x509_certificate(certificate_bytes)
    except ValueError:
        try:
            certificate = x509.load_der_x509_certificate(certificate_bytes)
        except ValueError as exc:
            raise GraphConfigError("cannot load Microsoft 365 client certificate") from exc

    now = int(time.time())
    header = {
        "alg": "RS256",
        "typ": "JWT",
        "x5t": _b64url(certificate.fingerprint(hashes.SHA1())),
    }
    claims = {
        "aud": token_endpoint,
        "iss": config.client_id,
        "sub": config.client_id,
        "jti": str(uuid.uuid4()),
        "nbf": now - 60,
        "exp": now + 600,
    }
    signing_input = (
        _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + _b64url(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    )
    try:
        signature = private_key.sign(signing_input.encode("ascii"), padding.PKCS1v15(), hashes.SHA256())
    except (TypeError, ValueError) as exc:
        raise GraphConfigError("cannot sign Microsoft 365 client assertion") from exc
    return signing_input + "." + _b64url(signature)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
