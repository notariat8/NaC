from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
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
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
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
        self._runner = runner

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
                capture_output=True,
                text=True,
                shell=False,
                stdin=subprocess.DEVNULL,
                timeout=30,
                env=self._env,
                pass_fds=(descriptor,),
            )
            if result.returncode != 0 or len(
                result.stdout.encode("utf-8")
            ) > _MAX_GITHUB_OUTPUT_BYTES:
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
        workspace_id: str,
        site_binding_sha256: str,
        bff_principal_binding_sha256: str,
        inspection_principal_binding_sha256: str,
        inspection_approval_sha256: str,
        provider_factory: Callable[
            [CertificateGraphConfig],
            CertificateClientCredentialsTokenProvider,
        ] = CertificateClientCredentialsTokenProvider,
        now_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if (
            not isinstance(config, CertificateGraphConfig)
            or config.graph_base_url != GRAPH_BASE_URL
            or principal_binding_sha256(config.client_id)
            != principal_binding_sha256(write_principal_id)
        ):
            raise ValueError("write_identity_config_binding_invalid")
        self._config = config
        self._workspace_id = workspace_id
        self._site_binding_sha256 = site_binding_sha256
        self._write_principal_binding_sha256 = principal_binding_sha256(
            write_principal_id
        )
        self._bff_principal_binding_sha256 = bff_principal_binding_sha256
        self._inspection_principal_binding_sha256 = (
            inspection_principal_binding_sha256
        )
        self._inspection_approval_sha256 = inspection_approval_sha256
        self._provider_factory = provider_factory
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
        return self._provider_factory(self._config)


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
    if type(value) is not str:
        return False
    parsed = urllib.parse.urlsplit(value)
    return bool(
        parsed.scheme == "https"
        and parsed.netloc == "graph.microsoft.com"
        and parsed.path.startswith("/v1.0/")
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
    ):
        raise ValueError("github_cli_binding_invalid")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        metadata = os.fstat(descriptor)
        if metadata.st_size > 128 * 1024 * 1024:
            raise ValueError("github_cli_binding_invalid")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        os.lseek(descriptor, 0, os.SEEK_SET)
    except (OSError, ValueError):
        if descriptor is not None:
            os.close(descriptor)
        raise ValueError("github_cli_binding_invalid") from None
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or not metadata.st_mode & stat.S_IXUSR
        or digest.hexdigest() != expected_sha256
    ):
        os.close(descriptor)
        raise ValueError("github_cli_binding_invalid")
    return descriptor


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
