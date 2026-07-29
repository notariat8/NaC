from __future__ import annotations

import fcntl
import hashlib
import json
import os
import selectors
import stat
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from notary_kg.business_case_type_mutation import canonical_hash

from .auth import (
    CertificateClientCredentialsTokenProvider,
    CertificateGraphConfig,
    _build_client_assertion_from_bytes,
    _post_token_form,
    _token_endpoint,
)
from .business_case_type_live_write_boundary import principal_binding_sha256
from .business_case_type_live_write_gate import (
    LiveWriteGateBlocked,
    LiveWriteApprovalAttestation,
    build_unverified_live_write_approval_attestation,
    OwnerApprovalVerification,
    WriteIdentityContext,
    validate_write_identity_context,
)
from .business_case_type_write_plan import GRAPH_BASE_URL
from .business_case_type_write_transport import HttpTransportResponse


S4F_STATUS = "S4F_PARTIAL_ADAPTERS_VERIFIED_OFFLINE"
S4D_ISSUE_REF = "https://github.com/notariat8/NaC/issues/700"
_S4D_ISSUE_API_PATH = "repos/notariat8/NaC/issues/700/comments"
_ALLOWED_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
_ALLOWED_METHODS = frozenset({"GET", "POST", "PATCH"})
_MAX_GITHUB_OUTPUT_BYTES = 2 * 1024 * 1024


class ProductionAdapterError(RuntimeError):
    """Stable, redacted production-adapter failure."""


class GitHubIssueCommentPort(Protocol):
    def comments(self) -> tuple[Mapping[str, Any], ...]: ...


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibNoRedirectGraphHttpPort:
    """Bound Graph v1.0 transport with no redirects, retries, or error bodies."""

    def __init__(
        self,
        *,
        opener: Any | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 60:
            raise ValueError("timeout_seconds_invalid")
        self._opener = opener or urllib.request.build_opener(
            _NoRedirectHandler()
        )
        self._timeout_seconds = timeout_seconds

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        follow_redirects: bool,
        automatic_retries: int,
        max_response_bytes: int,
    ) -> HttpTransportResponse:
        if (
            method not in _ALLOWED_METHODS
            or follow_redirects is not False
            or automatic_retries != 0
            or type(max_response_bytes) is not int
            or not 1 <= max_response_bytes <= 1024 * 1024
            or not _bound_graph_url(url)
            or not _safe_headers(headers)
            or (body is not None and type(body) is not bytes)
        ):
            raise ProductionAdapterError("graph_http_request_rejected")
        request = urllib.request.Request(
            url,
            data=body,
            headers=dict(headers),
            method=method,
        )
        try:
            response = self._opener.open(
                request, timeout=self._timeout_seconds
            )
            with response:
                response_body = response.read(max_response_bytes + 1)
                if len(response_body) > max_response_bytes:
                    raise ProductionAdapterError(
                        "graph_http_response_too_large"
                    )
                return HttpTransportResponse(
                    status_code=int(response.status),
                    body=response_body,
                    headers=_response_headers(response.headers),
                )
        except urllib.error.HTTPError as exc:
            try:
                status_code = int(exc.code)
                safe_headers = _response_headers(exc.headers)
            finally:
                exc.close()
            return HttpTransportResponse(
                status_code=status_code,
                body=b"",
                headers=safe_headers,
            )
        except ProductionAdapterError:
            raise
        except Exception:
            raise ProductionAdapterError(
                "graph_http_transport_unavailable"
            ) from None


class GhCliIssueCommentPort:
    """Read one pinned GitHub issue through an fd-bound gh executable."""

    def __init__(
        self,
        *,
        binary: Path,
        expected_binary_sha256: str,
        environ: Mapping[str, str] | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        descriptor = _open_trusted_executable(binary, expected_binary_sha256)
        os.close(descriptor)
        self._binary = binary
        self._expected_binary_sha256 = expected_binary_sha256
        source = os.environ if environ is None else environ
        self._env = {
            key: value
            for key, value in source.items()
            if key in {"GH_CONFIG_DIR", "HOME", "LANG"} and value
        }
        self._runner = runner or _run_bounded_process

    def comments(self) -> tuple[Mapping[str, Any], ...]:
        descriptor: int | None = None
        try:
            descriptor = _open_trusted_executable(
                self._binary, self._expected_binary_sha256
            )
            result = self._runner(
                [
                    f"/proc/self/fd/{descriptor}",
                    "api",
                    "--paginate",
                    "--slurp",
                    _S4D_ISSUE_API_PATH,
                ],
                check=False,
                shell=False,
                stdin=subprocess.DEVNULL,
                timeout=30,
                env=self._env,
                pass_fds=(descriptor,),
                max_stdout_bytes=_MAX_GITHUB_OUTPUT_BYTES,
            )
            if result.returncode != 0:
                raise ProductionAdapterError(
                    "owner_comment_snapshot_unavailable"
                )
            pages = json.loads(result.stdout)
        except ProductionAdapterError:
            raise
        except Exception:
            raise ProductionAdapterError(
                "owner_comment_snapshot_unavailable"
            ) from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
        if type(pages) is not list or any(type(page) is not list for page in pages):
            raise ProductionAdapterError("owner_comment_snapshot_invalid")
        comments: list[Mapping[str, Any]] = []
        for page in pages:
            for comment in page:
                if type(comment) is not dict:
                    raise ProductionAdapterError(
                        "owner_comment_snapshot_invalid"
                    )
                comments.append(comment)
        return tuple(comments)


class GitHubS4dOwnerApprovalVerifier:
    """Verify the exact canonical S4d owner comment without returning its body."""

    def __init__(
        self,
        *,
        comment_port: GitHubIssueCommentPort,
        owner_logins: tuple[str, ...],
        verifier_principal_binding_sha256: str,
    ) -> None:
        if (
            type(owner_logins) is not tuple
            or not owner_logins
            or any(not _safe_login(login) for login in owner_logins)
            or len(set(owner_logins)) != len(owner_logins)
        ):
            raise ValueError("owner_allowlist_invalid")
        if not _is_sha256(verifier_principal_binding_sha256):
            raise ValueError("verifier_principal_binding_invalid")
        self._comment_port = comment_port
        self._owner_logins = tuple(sorted(owner_logins))
        self._owner_allowlist_sha256 = canonical_hash(
            {
                "schema_version": "nac.s4d-owner-allowlist/v0.1",
                "owners": list(self._owner_logins),
            }
        )
        self._verifier_principal_binding_sha256 = (
            verifier_principal_binding_sha256
        )

    def verify(
        self,
        attestation: LiveWriteApprovalAttestation,
        *,
        expected: Mapping[str, str],
    ) -> OwnerApprovalVerification:
        if not isinstance(attestation, LiveWriteApprovalAttestation):
            raise ProductionAdapterError("owner_comment_binding_rejected")
        expected_fields = frozenset(
            field.name for field in fields(LiveWriteApprovalAttestation)
        ) - {"owner_comment_sha256", "approval_ref"}
        if (
            frozenset(expected) != expected_fields
            or any(type(expected[name]) is not str for name in expected_fields)
        ):
            raise ProductionAdapterError("owner_comment_binding_rejected")
        try:
            canonical_attestation = (
                build_unverified_live_write_approval_attestation(
                    **dict(expected)
                )
            )
        except (LiveWriteGateBlocked, TypeError, ValueError):
            raise ProductionAdapterError(
                "owner_comment_binding_rejected"
            ) from None
        if attestation != canonical_attestation:
            raise ProductionAdapterError("owner_comment_binding_rejected")
        if (
            attestation.owner_allowlist_sha256
            != self._owner_allowlist_sha256
            or attestation.owner_verifier_binding_sha256
            != self._verifier_principal_binding_sha256
        ):
            raise ProductionAdapterError("owner_comment_binding_rejected")
        payload = {
            "schema_version": "nac.s4d-owner-comment/v0.1",
            **dict(expected),
        }
        canonical_body = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        expected_comment_sha256 = canonical_hash(payload)

        matches: list[tuple[str, str]] = []
        for comment in self._comment_port.comments():
            author = comment.get("user")
            login = author.get("login") if type(author) is dict else None
            if (
                login not in self._owner_logins
                or comment.get("author_association")
                not in _ALLOWED_ASSOCIATIONS
                or comment.get("issue_url")
                != "https://api.github.com/repos/notariat8/NaC/issues/700"
                or comment.get("created_at") != comment.get("updated_at")
                or comment.get("body") != canonical_body
            ):
                continue
            observed_at = comment.get("updated_at")
            if type(observed_at) is str:
                matches.append((login, observed_at))
        if len(matches) != 1:
            raise ProductionAdapterError("owner_comment_snapshot_rejected")
        login, observed_at = matches[0]
        return OwnerApprovalVerification(
            source="github_issue_owner_comment",
            issue_ref=S4D_ISSUE_REF,
            owner_comment_sha256=attestation.owner_comment_sha256,
            owner_principal_binding_sha256=canonical_hash(
                {
                    "schema_version": "nac.github-owner-principal/v0.1",
                    "login": login,
                }
            ),
            verifier_principal_binding_sha256=(
                self._verifier_principal_binding_sha256
            ),
            owner_allowlist_sha256=self._owner_allowlist_sha256,
            observed_at=observed_at,
            verified=True,
        )


class CertificateWriteIdentityFactory:
    """Build a writer provider only after complete, fresh identity readback."""

    def __init__(
        self,
        *,
        config: CertificateGraphConfig,
        write_principal_id: str,
        expected_tenant_id: str,
        expected_certificate_sha256: str,
        expected_private_key_sha256: str,
        workspace_id: str,
        site_binding_sha256: str,
        bff_principal_binding_sha256: str,
        inspection_principal_binding_sha256: str,
        inspection_approval_sha256: str,
        provider_factory: Callable[
            [CertificateGraphConfig, bytes, bytes],
            CertificateClientCredentialsTokenProvider,
        ]
        | None = None,
        now_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if (
            not isinstance(config, CertificateGraphConfig)
            or config.graph_base_url != GRAPH_BASE_URL
            or config.tenant_id != expected_tenant_id
            or principal_binding_sha256(config.client_id)
            != principal_binding_sha256(write_principal_id)
            or not _is_sha256(expected_certificate_sha256)
            or not _is_sha256(expected_private_key_sha256)
        ):
            raise ValueError("write_identity_config_binding_invalid")
        self._config = config
        self._workspace_id = workspace_id
        self._site_binding_sha256 = site_binding_sha256
        self._write_principal_binding_sha256 = principal_binding_sha256(
            write_principal_id
        )
        self._expected_certificate_sha256 = expected_certificate_sha256
        self._expected_private_key_sha256 = expected_private_key_sha256
        self._bff_principal_binding_sha256 = bff_principal_binding_sha256
        self._inspection_principal_binding_sha256 = (
            inspection_principal_binding_sha256
        )
        self._inspection_approval_sha256 = inspection_approval_sha256
        self._provider_factory = (
            provider_factory or _build_bound_certificate_provider
        )
        self._now_provider = now_provider

    def build(
        self, context: WriteIdentityContext
    ) -> CertificateClientCredentialsTokenProvider:
        try:
            validated = validate_write_identity_context(
                context,
                workspace_id=self._workspace_id,
                site_binding_sha256=self._site_binding_sha256,
                write_principal_binding_sha256=(
                    self._write_principal_binding_sha256
                ),
                bff_principal_binding_sha256=(
                    self._bff_principal_binding_sha256
                ),
                inspection_principal_binding_sha256=(
                    self._inspection_principal_binding_sha256
                ),
                inspection_approval_sha256=(
                    self._inspection_approval_sha256
                ),
                now=self._now_provider(),
            )
        except (LiveWriteGateBlocked, TypeError, ValueError):
            raise ProductionAdapterError(
                "write_identity_context_rejected"
            ) from None
        if validated is not context:
            raise ProductionAdapterError("write_identity_context_rejected")
        certificate_bytes = _read_bound_credential(
            self._config.certificate_path,
            self._expected_certificate_sha256,
        )
        private_key_bytes = _read_bound_credential(
            self._config.private_key_path,
            self._expected_private_key_sha256,
        )
        return self._provider_factory(
            self._config,
            certificate_bytes,
            private_key_bytes,
        )


class BoundCertificateClientCredentialsTokenProvider(
    CertificateClientCredentialsTokenProvider
):
    """Use credential bytes already verified by the writer factory."""

    def __init__(
        self,
        config: CertificateGraphConfig,
        certificate_bytes: bytes,
        private_key_bytes: bytes,
    ) -> None:
        super().__init__(config)
        self._certificate_bytes = bytes(certificate_bytes)
        self._private_key_bytes = bytes(private_key_bytes)

    def fetch_access_token(self) -> str:
        endpoint = _token_endpoint(self.config.tenant_id)
        return _post_token_form(
            endpoint,
            {
                "client_id": self.config.client_id,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
                "client_assertion_type": (
                    "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
                ),
                "client_assertion": _build_client_assertion_from_bytes(
                    self.config,
                    endpoint,
                    certificate_bytes=self._certificate_bytes,
                    private_key_bytes=self._private_key_bytes,
                ),
            },
        )


def build_s4f_offline_composition_status() -> dict[str, object]:
    offline_verified_adapters = [
        "CertificateWriteIdentityFactory",
        "GitHubS4dOwnerApprovalVerifier",
        "SqliteEvidenceStagingOutbox",
        "UrllibNoRedirectGraphHttpPort",
    ]
    blockers = [
        "azure_blob_worm_policy_lock",
        "azure_blob_worm_rest_transport",
        "broker_product_owner_decision",
        "central_postgresql_outbox_promotion_ack_retention_cleanup",
        "dedicated_entra_write_identity_and_site_grant",
        "durable_reconciliation_store",
        "production_identity_inspection_readback",
        "synced_filesystem_runtime_detection",
        "signature_anchor_owner_decision",
    ]
    return {
        "schema_version": "nac.business-case-type-production-adapters-s4f/v0.1",
        "status": S4F_STATUS,
        "workspace_id": "notary_team_01",
        "offline_verified_adapters": offline_verified_adapters,
        "remaining_blockers": blockers,
        "central_truth_claimed": False,
        "production_readiness_claimed": False,
        "runtime_composition_enabled": False,
        "local_staging_outbox_can_close_mutation": False,
        "live_state_inspected": False,
        "live_write_authorized": False,
        "summary": {
            "implemented_adapter_count": len(offline_verified_adapters),
            "remaining_blocker_count": len(blockers),
            "socket_or_dns_calls": 0,
            "external_credential_store_reads": 0,
            "graph_calls": 0,
            "azure_calls": 0,
            "tenant_writes": 0,
        },
    }


def format_s4f_offline_composition_status(result: Mapping[str, object]) -> str:
    summary = result["summary"]
    assert isinstance(summary, Mapping)
    return (
        f"BusinessCaseType S4f: {result['status']}\n"
        f"Implemented adapters: {summary['implemented_adapter_count']}\n"
        f"Remaining blockers: {summary['remaining_blocker_count']}\n"
        "Live write authorized: false\n"
    )


def _bound_graph_url(value: object) -> bool:
    if (
        type(value) is not str
        or any(not 0x21 <= ord(character) <= 0x7E for character in value)
    ):
        return False
    parsed = urllib.parse.urlsplit(value)
    return bool(
        parsed.scheme == "https"
        and parsed.netloc == "graph.microsoft.com"
        and parsed.path.startswith("/v1.0/")
        and _canonical_graph_path(parsed.path)
        and parsed.username is None
        and parsed.password is None
        and parsed.fragment == ""
        and value.startswith(f"{GRAPH_BASE_URL}/")
    )


def _safe_headers(headers: object) -> bool:
    if not isinstance(headers, Mapping):
        return False
    for name, value in headers.items():
        if (
            type(name) is not str
            or type(value) is not str
            or not name
            or "\r" in name
            or "\n" in name
            or "\r" in value
            or "\n" in value
        ):
            return False
    return True


def _response_headers(headers: object) -> dict[str, str]:
    result: dict[str, str] = {}
    if headers is None:
        return result
    for source, target in (("ETag", "ETag"), ("Retry-After", "Retry-After")):
        try:
            value = headers.get(source)
        except Exception:
            continue
        if type(value) is str and "\r" not in value and "\n" not in value:
            result[target] = value
    try:
        location = headers.get("Location")
    except Exception:
        location = None
    if _bound_graph_url(location):
        result["Location"] = location
    return result


def _open_trusted_executable(path: Path, expected_sha256: str) -> int:
    if (
        not isinstance(path, Path)
        or not path.is_absolute()
        or not _is_sha256(expected_sha256)
        or os.name != "posix"
        or not Path("/proc/self/fd").is_dir()
        or not hasattr(os, "memfd_create")
        or not hasattr(fcntl, "F_ADD_SEALS")
    ):
        raise ValueError("github_cli_binding_invalid")
    source_descriptor: int | None = None
    sealed_descriptor: int | None = None
    try:
        source_descriptor = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        metadata = os.fstat(source_descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or not metadata.st_mode & stat.S_IXUSR
            or metadata.st_size > 128 * 1024 * 1024
        ):
            raise ValueError("github_cli_binding_invalid")
        payload = bytearray()
        digest = hashlib.sha256()
        while True:
            chunk = os.read(source_descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            payload.extend(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ValueError("github_cli_binding_invalid")
        sealed_descriptor = os.memfd_create(
            "nac-gh-sealed",
            getattr(os, "MFD_CLOEXEC", 0)
            | getattr(os, "MFD_ALLOW_SEALING", 0),
        )
        offset = 0
        while offset < len(payload):
            offset += os.write(sealed_descriptor, payload[offset:])
        os.fchmod(sealed_descriptor, 0o500)
        required_seals = (
            fcntl.F_SEAL_WRITE
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_SEAL
        )
        fcntl.fcntl(sealed_descriptor, fcntl.F_ADD_SEALS, required_seals)
        if fcntl.fcntl(sealed_descriptor, fcntl.F_GET_SEALS) != required_seals:
            raise ValueError("github_cli_binding_invalid")
        os.lseek(sealed_descriptor, 0, os.SEEK_SET)
    except (OSError, ValueError):
        if sealed_descriptor is not None:
            os.close(sealed_descriptor)
        raise ValueError("github_cli_binding_invalid") from None
    finally:
        if source_descriptor is not None:
            os.close(source_descriptor)
    return sealed_descriptor


def _canonical_graph_path(path: str) -> bool:
    if "\\" in path or "//" in path:
        return False
    if any(segment in {".", ".."} for segment in path.split("/")):
        return False
    index = 0
    while index < len(path):
        if path[index] != "%":
            index += 1
            continue
        if index + 2 >= len(path):
            return False
        pair = path[index + 1 : index + 3]
        if any(character not in "0123456789abcdefABCDEF" for character in pair):
            return False
        decoded_octet = int(pair, 16)
        if (
            decoded_octet <= 0x20
            or decoded_octet == 0x7F
            or pair.lower() in {"25", "2e", "2f", "5c"}
        ):
            return False
        index += 3
    decoded = urllib.parse.unquote(path)
    return "\\" not in decoded and all(
        segment not in {".", ".."} for segment in decoded.split("/")
    )


def _read_bound_credential(path: Path, expected_sha256: str) -> bytes:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ProductionAdapterError("write_identity_credential_rejected")
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or metadata.st_mode & (stat.S_IRWXG | stat.S_IRWXO)
                or metadata.st_size > 1024 * 1024
            ):
                raise OSError("credential_metadata_invalid")
            payload = bytearray()
            while True:
                chunk = os.read(descriptor, 64 * 1024)
                if not chunk:
                    break
                payload.extend(chunk)
        finally:
            os.close(descriptor)
    except OSError:
        raise ProductionAdapterError(
            "write_identity_credential_rejected"
        ) from None
    result = bytes(payload)
    if not result or hashlib.sha256(result).hexdigest() != expected_sha256:
        raise ProductionAdapterError("write_identity_credential_rejected")
    return result


def _build_bound_certificate_provider(
    config: CertificateGraphConfig,
    certificate_bytes: bytes,
    private_key_bytes: bytes,
) -> BoundCertificateClientCredentialsTokenProvider:
    return BoundCertificateClientCredentialsTokenProvider(
        config,
        certificate_bytes,
        private_key_bytes,
    )


def _run_bounded_process(
    command: list[str],
    *,
    check: bool,
    shell: bool,
    stdin: int,
    timeout: int,
    env: Mapping[str, str],
    pass_fds: tuple[int, ...],
    max_stdout_bytes: int,
) -> subprocess.CompletedProcess[str]:
    del check
    process = subprocess.Popen(
        command,
        shell=shell,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=dict(env),
        pass_fds=pass_fds,
    )
    if process.stdout is None:
        process.kill()
        raise ProductionAdapterError("owner_comment_snapshot_unavailable")
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    payload = bytearray()
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            events = selector.select(min(remaining, 0.25))
            if not events:
                if process.poll() is not None:
                    break
                continue
            chunk = os.read(
                process.stdout.fileno(),
                min(64 * 1024, max_stdout_bytes + 1 - len(payload)),
            )
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > max_stdout_bytes:
                raise ProductionAdapterError(
                    "owner_comment_snapshot_unavailable"
                )
        returncode = process.wait(max(0.0, deadline - time.monotonic()))
        return subprocess.CompletedProcess(
            command,
            returncode,
            payload.decode("utf-8"),
            "",
        )
    except Exception:
        process.kill()
        process.wait()
        raise
    finally:
        selector.close()
        process.stdout.close()


def _safe_login(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 39
        and value[0].isalnum()
        and value[-1].isalnum()
        and all(character.isalnum() or character == "-" for character in value)
    )


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
