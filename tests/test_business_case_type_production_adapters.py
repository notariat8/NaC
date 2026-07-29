from __future__ import annotations

import hashlib
from datetime import datetime, timezone
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.auth import CertificateGraphConfig  # noqa: E402
from nac_m365_graph.business_case_type_live_write_boundary import (  # noqa: E402
    principal_binding_sha256,
)
from nac_m365_graph.business_case_type_live_write_gate import (  # noqa: E402
    WriteIdentityContext,
    build_unverified_live_write_approval_attestation,
)
from nac_m365_graph.business_case_type_production_adapters import (  # noqa: E402
    S4D_ISSUE_REF,
    S4F_STATUS,
    CertificateWriteIdentityFactory,
    GhCliIssueCommentPort,
    GitHubS4dOwnerApprovalVerifier,
    ProductionAdapterError,
    UrllibNoRedirectGraphHttpPort,
    _run_bounded_process,
    build_s4f_offline_composition_status,
    format_s4f_offline_composition_status,
)
from notary_kg.business_case_type_mutation import canonical_hash  # noqa: E402


GRAPH_URL = "https://graph.microsoft.com/v1.0/sites/site-id/lists"
IDENTITY_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
INSPECTION_PRINCIPAL_BINDING = "3" * 64
INSPECTION_APPROVAL_SHA256 = "4" * 64
VERIFIER_BINDING = "9" * 64
OWNER_LOGINS = ("z-owner", "a-owner")
OWNER_ALLOWLIST_SHA256 = canonical_hash(
    {
        "schema_version": "nac.s4d-owner-allowlist/v0.1",
        "owners": sorted(OWNER_LOGINS),
    }
)


class _Response:
    def __init__(
        self,
        *,
        status: int = 200,
        body: bytes = b"{}",
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.status = status
        self.body = body
        self.headers = dict(headers or {})
        self.read_limits: list[int] = []
        self.closed = False

    def read(self, limit: int) -> bytes:
        self.read_limits.append(limit)
        return self.body[:limit]

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True


class _Opener:
    def __init__(
        self,
        result: _Response | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.result = result or _Response()
        self.error = error
        self.calls: list[tuple[Any, int]] = []

    def open(self, request: Any, *, timeout: int) -> _Response:
        self.calls.append((request, timeout))
        if self.error is not None:
            raise self.error
        return self.result


class _TrackedBody(io.BytesIO):
    def __init__(self, value: bytes) -> None:
        super().__init__(value)
        self.read_called = False

    def read(self, *args: object, **kwargs: object) -> bytes:
        self.read_called = True
        return super().read(*args, **kwargs)


class _CommentPort:
    def __init__(self, comments: tuple[Mapping[str, Any], ...]) -> None:
        self._comments = comments
        self.calls = 0

    def comments(self) -> tuple[Mapping[str, Any], ...]:
        self.calls += 1
        return self._comments


def _graph_request_values() -> dict[str, Any]:
    return {
        "method": "POST",
        "url": GRAPH_URL,
        "headers": {
            "Authorization": "Bearer synthetic-token",
            "Content-Type": "application/json",
        },
        "body": b'{"displayName":"Test"}',
        "follow_redirects": False,
        "automatic_retries": 0,
        "max_response_bytes": 1024,
    }


def _approval_fixture() -> tuple[Any, dict[str, str], str]:
    values = {
        "workspace_id": "notary_team_01",
        "commit_sha": "1" * 40,
        "tree_sha": "2" * 40,
        "domain_contract_sha256": "1" * 64,
        "verification_contract_sha256": "2" * 64,
        "plan_binding_sha256": "3" * 64,
        "toolchain_sha256": "4" * 64,
        "step_sequence_sha256": "5" * 64,
        "evidence_policy_sha256": "6" * 64,
        "target_binding_sha256": "7" * 64,
        "write_principal_binding_sha256": "8" * 64,
        "bff_principal_binding_sha256": "a" * 64,
        "owner_verifier_binding_sha256": VERIFIER_BINDING,
        "owner_allowlist_sha256": OWNER_ALLOWLIST_SHA256,
        "inspection_principal_binding_sha256": "b" * 64,
    }
    attestation = build_unverified_live_write_approval_attestation(**values)
    expected = {
        key: value
        for key, value in asdict(attestation).items()
        if key not in {"owner_comment_sha256", "approval_ref"}
    }
    canonical_body = json.dumps(
        {
            "schema_version": "nac.s4d-owner-comment/v0.1",
            **expected,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return attestation, expected, canonical_body


def _owner_comment(
    body: str,
    *,
    login: str = "a-owner",
    association: str = "OWNER",
    issue_url: str = "https://api.github.com/repos/notariat8/NaC/issues/700",
    created_at: str = "2026-07-29T10:00:00Z",
    updated_at: str = "2026-07-29T10:00:00Z",
) -> dict[str, Any]:
    return {
        "user": {"login": login},
        "author_association": association,
        "issue_url": issue_url,
        "created_at": created_at,
        "updated_at": updated_at,
        "body": body,
    }


def _identity_context(
    write_principal_id: str,
    **overrides: Any,
) -> WriteIdentityContext:
    values: dict[str, Any] = {
        "workspace_id": "notary_team_01",
        "site_binding_sha256": "1" * 64,
        "write_principal_binding_sha256": principal_binding_sha256(
            write_principal_id
        ),
        "write_graph_permissions": ("Sites.Selected",),
        "write_site_roles": ("write",),
        "bff_principal_binding_sha256": "2" * 64,
        "bff_graph_permissions": ("Sites.Selected",),
        "bff_site_roles": ("read",),
        "inspection_source": "synthetic-offline-owner-bound-readback",
        "inspection_observed_at": "2026-07-29T12:00:00Z",
        "inspection_principal_binding_sha256": (
            INSPECTION_PRINCIPAL_BINDING
        ),
        "inspection_approval_sha256": INSPECTION_APPROVAL_SHA256,
    }
    values.update(overrides)
    return WriteIdentityContext(**values)


class GraphHttpAdapterTests(unittest.TestCase):
    def test_success_is_bound_to_graph_v1_and_filters_response_headers(
        self,
    ) -> None:
        response = _Response(
            status=201,
            body=b'{"id":"synthetic"}',
            headers={
                "ETag": '"etag"',
                "Location": GRAPH_URL + "/item-id",
                "Retry-After": "5",
                "Set-Cookie": "must-not-cross-boundary",
                "X-Diagnostic": "raw-provider-detail",
            },
        )
        opener = _Opener(response)
        adapter = UrllibNoRedirectGraphHttpPort(
            opener=opener, timeout_seconds=17
        )

        result = adapter.request(**_graph_request_values())

        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.body, b'{"id":"synthetic"}')
        self.assertEqual(
            result.headers,
            {
                "ETag": '"etag"',
                "Location": GRAPH_URL + "/item-id",
                "Retry-After": "5",
            },
        )
        self.assertEqual(len(opener.calls), 1)
        request, timeout = opener.calls[0]
        self.assertEqual(request.full_url, GRAPH_URL)
        self.assertEqual(request.method, "POST")
        self.assertEqual(timeout, 17)
        self.assertEqual(response.read_limits, [1025])
        self.assertTrue(response.closed)

    def test_request_envelope_drift_fails_before_the_opener(self) -> None:
        invalid_overrides = (
            {"method": "PUT"},
            {"url": "https://graph.microsoft.com/beta/sites/site-id"},
            {"url": "https://graph.microsoft.com.evil/v1.0/sites/site-id"},
            {"url": "https://[invalid/v1.0/sites/site-id"},
            {"url": "http://graph.microsoft.com/v1.0/sites/site-id"},
            {"url": GRAPH_URL + "#fragment"},
            {"url": "https://graph.microsoft.com/v1.0/../beta/sites/x"},
            {"url": "https://graph.microsoft.com/v1.0/%2e%2e/beta/sites/x"},
            {"url": "https://graph.microsoft.com/v1.0/%252e%252e/beta/sites/x"},
            {"url": "https://graph.microsoft.com/v1.0/sites%2fx"},
            {"url": "https://graph.microsoft.com/v1.0//sites/x"},
            {"url": "https://graph.microsoft.com/v1.0\\..\\beta"},
            {"url": "https://graph.microsoft.com/v1.0/sites/x\r\n"},
            {"url": "https://graph.microsoft.com/v1.0/sites/x\t"},
            {"url": "https://graph.microsoft.com/v1.0/sites/x\x00"},
            {"url": "https://graph.microsoft.com/v1.0/sites/%00x"},
            {"url": "https://graph.microsoft.com/v1.0/sites/%0d%0ax"},
            {"follow_redirects": True},
            {"automatic_retries": 1},
            {"max_response_bytes": 0},
            {"max_response_bytes": 1024 * 1024 + 1},
            {"headers": {"Authorization": "Bearer value\r\nX-Evil: true"}},
            {"body": "not-bytes"},
        )
        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides):
                opener = _Opener()
                adapter = UrllibNoRedirectGraphHttpPort(opener=opener)
                values = _graph_request_values()
                values.update(overrides)

                with self.assertRaisesRegex(
                    ProductionAdapterError,
                    r"^graph_http_request_rejected$",
                ):
                    adapter.request(**values)

                self.assertEqual(opener.calls, [])

    def test_redirect_response_is_not_followed_and_error_body_is_never_read(
        self,
    ) -> None:
        raw_body = b'{"error":{"message":"secret provider detail"}}'
        tracked_body = _TrackedBody(raw_body)
        error = urllib.error.HTTPError(
            GRAPH_URL,
            302,
            "redirect with raw detail",
            {
                "Location": "https://login.example.invalid/capture",
                "X-Diagnostic": "secret provider detail",
            },
            tracked_body,
        )
        opener = _Opener(error=error)
        adapter = UrllibNoRedirectGraphHttpPort(opener=opener)

        result = adapter.request(**_graph_request_values())

        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.body, b"")
        self.assertEqual(
            result.headers,
            {},
        )
        self.assertFalse(tracked_body.read_called)
        self.assertTrue(tracked_body.closed)
        self.assertEqual(len(opener.calls), 1)

    def test_transport_failure_and_oversize_response_are_stable_and_redacted(
        self,
    ) -> None:
        sensitive = "Bearer raw-secret-token"
        unavailable = UrllibNoRedirectGraphHttpPort(
            opener=_Opener(error=RuntimeError(sensitive))
        )
        with self.assertRaises(ProductionAdapterError) as unavailable_error:
            unavailable.request(**_graph_request_values())
        self.assertEqual(
            str(unavailable_error.exception),
            "graph_http_transport_unavailable",
        )
        self.assertNotIn(sensitive, str(unavailable_error.exception))

        oversize = UrllibNoRedirectGraphHttpPort(
            opener=_Opener(_Response(body=b"x" * 1025))
        )
        with self.assertRaisesRegex(
            ProductionAdapterError,
            r"^graph_http_response_too_large$",
        ):
            oversize.request(**_graph_request_values())


class GitHubOwnerVerifierTests(unittest.TestCase):
    def test_exact_single_canonical_owner_comment_is_verified_without_body(
        self,
    ) -> None:
        attestation, expected, canonical_body = _approval_fixture()
        port = _CommentPort(
            (
                _owner_comment("unrelated comment", login="not-an-owner"),
                _owner_comment(canonical_body),
            )
        )
        verifier = GitHubS4dOwnerApprovalVerifier(
            comment_port=port,
            owner_logins=OWNER_LOGINS,
            verifier_principal_binding_sha256=VERIFIER_BINDING,
        )

        result = verifier.verify(attestation, expected=expected)

        self.assertTrue(result.verified)
        self.assertEqual(result.source, "github_issue_owner_comment")
        self.assertEqual(result.issue_ref, S4D_ISSUE_REF)
        self.assertEqual(
            result.owner_comment_sha256,
            attestation.owner_comment_sha256,
        )
        self.assertEqual(
            result.owner_principal_binding_sha256,
            canonical_hash(
                {
                    "schema_version": "nac.github-owner-principal/v0.1",
                    "login": "a-owner",
                }
            ),
        )
        self.assertEqual(result.owner_allowlist_sha256, OWNER_ALLOWLIST_SHA256)
        self.assertEqual(
            result.verifier_principal_binding_sha256,
            VERIFIER_BINDING,
        )
        self.assertEqual(result.observed_at, "2026-07-29T10:00:00Z")
        self.assertNotIn("body", asdict(result))
        self.assertNotIn(canonical_body, repr(result))
        self.assertEqual(port.calls, 1)

    def test_duplicate_exact_comments_are_rejected(self) -> None:
        attestation, expected, canonical_body = _approval_fixture()
        verifier = GitHubS4dOwnerApprovalVerifier(
            comment_port=_CommentPort(
                (
                    _owner_comment(canonical_body),
                    _owner_comment(canonical_body, login="z-owner"),
                )
            ),
            owner_logins=OWNER_LOGINS,
            verifier_principal_binding_sha256=VERIFIER_BINDING,
        )

        with self.assertRaisesRegex(
            ProductionAdapterError,
            r"^owner_comment_snapshot_rejected$",
        ):
            verifier.verify(attestation, expected=expected)

    def test_comment_metadata_or_canonical_body_drift_is_rejected(self) -> None:
        attestation, expected, canonical_body = _approval_fixture()
        drifted_comments = (
            _owner_comment(canonical_body + " "),
            _owner_comment(canonical_body, association="CONTRIBUTOR"),
            _owner_comment(
                canonical_body,
                issue_url=(
                    "https://api.github.com/repos/notariat8/NaC/issues/701"
                ),
            ),
            _owner_comment(
                canonical_body,
                updated_at="2026-07-29T10:00:01Z",
            ),
            _owner_comment(canonical_body, login="unlisted-owner"),
        )
        for comment in drifted_comments:
            with self.subTest(comment=comment):
                verifier = GitHubS4dOwnerApprovalVerifier(
                    comment_port=_CommentPort((comment,)),
                    owner_logins=OWNER_LOGINS,
                    verifier_principal_binding_sha256=VERIFIER_BINDING,
                )
                with self.assertRaisesRegex(
                    ProductionAdapterError,
                    r"^owner_comment_snapshot_rejected$",
                ):
                    verifier.verify(attestation, expected=expected)

    def test_attestation_binding_drift_is_rejected_before_comment_access(
        self,
    ) -> None:
        attestation, expected, canonical_body = _approval_fixture()
        port = _CommentPort((_owner_comment(canonical_body),))
        verifier = GitHubS4dOwnerApprovalVerifier(
            comment_port=port,
            owner_logins=OWNER_LOGINS,
            verifier_principal_binding_sha256=VERIFIER_BINDING,
        )
        drifted = (
            replace(attestation, owner_allowlist_sha256="f" * 64),
            replace(attestation, owner_verifier_binding_sha256="e" * 64),
            replace(attestation, owner_comment_sha256="d" * 64),
            replace(attestation, commit_sha="f" * 40),
            replace(attestation, approval_ref="owner-approval-v1-" + "e" * 64),
        )

        for candidate in drifted:
            with self.subTest(candidate=candidate):
                with self.assertRaisesRegex(
                    ProductionAdapterError,
                    r"^owner_comment_binding_rejected$",
                ):
                    verifier.verify(candidate, expected=expected)

        self.assertEqual(port.calls, 0)

    def test_direct_verifier_rejects_non_allowlisted_workspace_binding(
        self,
    ) -> None:
        attestation, expected, _ = _approval_fixture()
        expected["workspace_id"] = "other_workspace"
        payload = {
            "schema_version": "nac.s4d-owner-comment/v0.1",
            **expected,
        }
        comment_sha256 = canonical_hash(payload)
        candidate = replace(
            attestation,
            workspace_id="other_workspace",
            owner_comment_sha256=comment_sha256,
            approval_ref=f"owner-approval-v1-{comment_sha256}",
        )
        canonical_body = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        port = _CommentPort((_owner_comment(canonical_body),))
        verifier = GitHubS4dOwnerApprovalVerifier(
            comment_port=port,
            owner_logins=OWNER_LOGINS,
            verifier_principal_binding_sha256=VERIFIER_BINDING,
        )

        with self.assertRaisesRegex(
            ProductionAdapterError,
            r"^owner_comment_binding_rejected$",
        ):
            verifier.verify(candidate, expected=expected)

        self.assertEqual(port.calls, 0)

    def test_rejection_does_not_leak_raw_comment_content(self) -> None:
        attestation, expected, _ = _approval_fixture()
        raw_comment = "token=raw-owner-secret"
        verifier = GitHubS4dOwnerApprovalVerifier(
            comment_port=_CommentPort((_owner_comment(raw_comment),)),
            owner_logins=OWNER_LOGINS,
            verifier_principal_binding_sha256=VERIFIER_BINDING,
        )

        with self.assertRaises(ProductionAdapterError) as captured:
            verifier.verify(attestation, expected=expected)

        self.assertEqual(
            str(captured.exception), "owner_comment_snapshot_rejected"
        )
        self.assertNotIn(raw_comment, str(captured.exception))

    def test_gh_cli_failure_does_not_leak_stdout_stderr_or_environment(
        self,
    ) -> None:
        raw_stdout = "raw owner comment"
        raw_stderr = "gh-token=raw-secret"
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "gh"
            binary.write_bytes(b"synthetic-gh")
            os.chmod(binary, 0o700)
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()

            def runner(*args: object, **kwargs: object) -> Any:
                command = args[0]
                descriptor = kwargs["pass_fds"][0]
                self.assertEqual(
                    command[0], f"/proc/self/fd/{descriptor}"
                )
                self.assertEqual(kwargs["pass_fds"], (descriptor,))
                return subprocess.CompletedProcess(
                    args=[],
                    returncode=1,
                    stdout=raw_stdout,
                    stderr=raw_stderr,
                )

            port = GhCliIssueCommentPort(
                binary=binary,
                expected_binary_sha256=digest,
                environ={
                    "HOME": directory,
                    "GH_TOKEN": "raw-environment-token",
                    "UNRELATED": "raw-environment-value",
                },
                runner=runner,
            )
            with self.assertRaises(ProductionAdapterError) as captured:
                port.comments()

        self.assertEqual(
            str(captured.exception), "owner_comment_snapshot_unavailable"
        )
        rendered = str(captured.exception)
        self.assertNotIn(raw_stdout, rendered)
        self.assertNotIn(raw_stderr, rendered)
        self.assertNotIn("raw-environment-token", rendered)

    def test_gh_cli_binary_is_revalidated_before_every_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "gh"
            binary.write_bytes(b"synthetic-gh")
            os.chmod(binary, 0o700)
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            runner_calls: list[object] = []

            def runner(*args: object, **kwargs: object) -> Any:
                runner_calls.append((args, kwargs))
                raise AssertionError("runner must not be called")

            port = GhCliIssueCommentPort(
                binary=binary,
                expected_binary_sha256=digest,
                environ={"HOME": directory},
                runner=runner,
            )
            binary.write_bytes(b"replaced-gh")
            os.chmod(binary, 0o700)

            with self.assertRaisesRegex(
                ProductionAdapterError,
                r"^owner_comment_snapshot_unavailable$",
            ):
                port.comments()

        self.assertEqual(runner_calls, [])

    def test_gh_cli_executes_sealed_copy_when_source_changes_in_place(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "gh"
            original = b"synthetic-gh-original"
            binary.write_bytes(original)
            os.chmod(binary, 0o700)
            digest = hashlib.sha256(original).hexdigest()
            executed_payloads: list[bytes] = []

            def runner(*args: object, **kwargs: object) -> Any:
                descriptor = kwargs["pass_fds"][0]
                binary.write_bytes(b"mutated-in-place-after-sealing")
                os.chmod(binary, 0o700)
                os.lseek(descriptor, 0, os.SEEK_SET)
                executed_payloads.append(os.read(descriptor, len(original) + 64))
                with self.assertRaises(OSError):
                    os.write(descriptor, b"x")
                return subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout="[[]]",
                    stderr="",
                )

            port = GhCliIssueCommentPort(
                binary=binary,
                expected_binary_sha256=digest,
                environ={"HOME": directory},
                runner=runner,
            )

            self.assertEqual(port.comments(), ())

        self.assertEqual(executed_payloads, [original])

    def test_bounded_runner_reads_only_limit_plus_one_and_reaps_process(
        self,
    ) -> None:
        original_read = os.read
        read_sizes: list[int] = []
        captured_processes: list[Any] = []
        real_popen = subprocess.Popen

        def tracked_read(descriptor: int, size: int) -> bytes:
            chunk = original_read(descriptor, size)
            read_sizes.append(len(chunk))
            return chunk

        def tracked_popen(*args: object, **kwargs: object) -> Any:
            process = real_popen(*args, **kwargs)
            captured_processes.append(process)
            return process

        with mock.patch(
            "nac_m365_graph.business_case_type_production_adapters.os.read",
            side_effect=tracked_read,
        ), mock.patch(
            "nac_m365_graph.business_case_type_production_adapters.subprocess.Popen",
            side_effect=tracked_popen,
        ):
            with self.assertRaisesRegex(
                ProductionAdapterError,
                r"^owner_comment_snapshot_unavailable$",
            ):
                _run_bounded_process(
                    ["/usr/bin/head", "-c", "4096", "/dev/zero"],
                    check=False,
                    shell=False,
                    stdin=subprocess.DEVNULL,
                    timeout=5,
                    env={"LANG": "C"},
                    pass_fds=(),
                    max_stdout_bytes=1024,
                )

        self.assertEqual(sum(read_sizes), 1025)
        self.assertEqual(len(captured_processes), 1)
        self.assertIsNotNone(captured_processes[0].poll())


class CertificateWriteIdentityFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.certificate_bytes = b"synthetic-certificate"
        self.private_key_bytes = b"synthetic-private-key"
        self.certificate_path = root / "writer.crt"
        self.private_key_path = root / "writer.key"
        self.certificate_path.write_bytes(self.certificate_bytes)
        self.private_key_path.write_bytes(self.private_key_bytes)
        os.chmod(self.certificate_path, 0o600)
        os.chmod(self.private_key_path, 0o600)
        self.certificate_sha256 = hashlib.sha256(
            self.certificate_bytes
        ).hexdigest()
        self.private_key_sha256 = hashlib.sha256(
            self.private_key_bytes
        ).hexdigest()
        self.write_principal_id = "writer-principal-id"
        self.config = CertificateGraphConfig(
            tenant_id="tenant-id",
            client_id=self.write_principal_id,
            certificate_path=self.certificate_path,
            private_key_path=self.private_key_path,
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_provider_is_constructed_only_after_exact_write_identity_binding(
        self,
    ) -> None:
        calls: list[tuple[CertificateGraphConfig, bytes, bytes]] = []
        provider = object()

        def provider_factory(
            config: CertificateGraphConfig,
            certificate_bytes: bytes,
            private_key_bytes: bytes,
        ) -> Any:
            calls.append((config, certificate_bytes, private_key_bytes))
            return provider

        factory = CertificateWriteIdentityFactory(
            config=self.config,
            write_principal_id=self.write_principal_id,
            expected_tenant_id="tenant-id",
            expected_certificate_sha256=self.certificate_sha256,
            expected_private_key_sha256=self.private_key_sha256,
            workspace_id="notary_team_01",
            site_binding_sha256="1" * 64,
            bff_principal_binding_sha256="2" * 64,
            inspection_principal_binding_sha256=(
                INSPECTION_PRINCIPAL_BINDING
            ),
            inspection_approval_sha256=INSPECTION_APPROVAL_SHA256,
            now_provider=lambda: IDENTITY_NOW,
            provider_factory=provider_factory,
        )

        result = factory.build(_identity_context(self.write_principal_id))

        self.assertIs(result, provider)
        self.assertEqual(
            calls,
            [(self.config, self.certificate_bytes, self.private_key_bytes)],
        )

    def test_any_write_identity_scope_or_role_drift_fails_before_factory(
        self,
    ) -> None:
        calls: list[tuple[CertificateGraphConfig, bytes, bytes]] = []
        factory = CertificateWriteIdentityFactory(
            config=self.config,
            write_principal_id=self.write_principal_id,
            expected_tenant_id="tenant-id",
            expected_certificate_sha256=self.certificate_sha256,
            expected_private_key_sha256=self.private_key_sha256,
            workspace_id="notary_team_01",
            site_binding_sha256="1" * 64,
            bff_principal_binding_sha256="2" * 64,
            inspection_principal_binding_sha256=(
                INSPECTION_PRINCIPAL_BINDING
            ),
            inspection_approval_sha256=INSPECTION_APPROVAL_SHA256,
            now_provider=lambda: IDENTITY_NOW,
            provider_factory=lambda config, certificate, private_key: calls.append(
                (config, certificate, private_key)
            ),
        )
        drifted_contexts = (
            _identity_context(
                self.write_principal_id,
                write_principal_binding_sha256=principal_binding_sha256(
                    "different-writer-principal"
                ),
            ),
            _identity_context(
                self.write_principal_id,
                write_graph_permissions=("Sites.ReadWrite.All",),
            ),
            _identity_context(
                self.write_principal_id,
                write_graph_permissions=(
                    "Sites.Selected",
                    "Sites.ReadWrite.All",
                ),
            ),
            _identity_context(
                self.write_principal_id,
                write_site_roles=("owner",),
            ),
            _identity_context(
                self.write_principal_id,
                broader_write_graph_roles=("Sites.ReadWrite.All",),
            ),
            _identity_context(
                self.write_principal_id, workspace_id="other_workspace"
            ),
            _identity_context(
                self.write_principal_id, site_binding_sha256="a" * 64
            ),
            _identity_context(
                self.write_principal_id,
                bff_graph_permissions=("Sites.ReadWrite.All",),
            ),
            _identity_context(
                self.write_principal_id,
                inspection_approval_sha256="b" * 64,
            ),
            _identity_context(
                self.write_principal_id,
                inspection_observed_at="2026-07-29T11:00:00Z",
            ),
        )

        for context in drifted_contexts:
            with self.subTest(context=context):
                with self.assertRaisesRegex(
                    ProductionAdapterError,
                    r"^write_identity_context_rejected$",
                ):
                    factory.build(context)

        self.assertEqual(calls, [])


    def test_certificate_client_id_must_match_inspected_writer(self) -> None:
        mismatched = CertificateGraphConfig(
            tenant_id="tenant-id",
            client_id="different-writer-client",
            certificate_path=self.certificate_path,
            private_key_path=self.private_key_path,
        )

        with self.assertRaisesRegex(
            ValueError, r"^write_identity_config_binding_invalid$"
        ):
            CertificateWriteIdentityFactory(
                config=mismatched,
                write_principal_id=self.write_principal_id,
                expected_tenant_id="tenant-id",
                expected_certificate_sha256=self.certificate_sha256,
                expected_private_key_sha256=self.private_key_sha256,
                workspace_id="notary_team_01",
                site_binding_sha256="1" * 64,
                bff_principal_binding_sha256="2" * 64,
                inspection_principal_binding_sha256=(
                    INSPECTION_PRINCIPAL_BINDING
                ),
                inspection_approval_sha256=INSPECTION_APPROVAL_SHA256,
                now_provider=lambda: IDENTITY_NOW,
            )

    def test_tenant_and_credential_drift_fail_closed(self) -> None:
        drifted_configs = (
            replace(self.config, tenant_id="other-tenant"),
            self.config,
            self.config,
        )
        bindings = (
            ("tenant-id", self.certificate_sha256, self.private_key_sha256),
            ("tenant-id", "a" * 64, self.private_key_sha256),
            ("tenant-id", self.certificate_sha256, "b" * 64),
        )
        for config, binding in zip(drifted_configs, bindings, strict=True):
            with self.subTest(config=config, binding=binding):
                expected_tenant, certificate_hash, private_key_hash = binding
                if config.tenant_id != expected_tenant:
                    with self.assertRaisesRegex(
                        ValueError,
                        r"^write_identity_config_binding_invalid$",
                    ):
                        CertificateWriteIdentityFactory(
                            config=config,
                            write_principal_id=self.write_principal_id,
                            expected_tenant_id=expected_tenant,
                            expected_certificate_sha256=certificate_hash,
                            expected_private_key_sha256=private_key_hash,
                            workspace_id="notary_team_01",
                            site_binding_sha256="1" * 64,
                            bff_principal_binding_sha256="2" * 64,
                            inspection_principal_binding_sha256=(
                                INSPECTION_PRINCIPAL_BINDING
                            ),
                            inspection_approval_sha256=(
                                INSPECTION_APPROVAL_SHA256
                            ),
                            now_provider=lambda: IDENTITY_NOW,
                        )
                    continue
                factory = CertificateWriteIdentityFactory(
                    config=config,
                    write_principal_id=self.write_principal_id,
                    expected_tenant_id=expected_tenant,
                    expected_certificate_sha256=certificate_hash,
                    expected_private_key_sha256=private_key_hash,
                    workspace_id="notary_team_01",
                    site_binding_sha256="1" * 64,
                    bff_principal_binding_sha256="2" * 64,
                    inspection_principal_binding_sha256=(
                        INSPECTION_PRINCIPAL_BINDING
                    ),
                    inspection_approval_sha256=INSPECTION_APPROVAL_SHA256,
                    now_provider=lambda: IDENTITY_NOW,
                )
                with self.assertRaisesRegex(
                    ProductionAdapterError,
                    r"^write_identity_credential_rejected$",
                ):
                    factory.build(_identity_context(self.write_principal_id))

    def test_bound_provider_receives_credential_bytes_not_reopenable_paths(
        self,
    ) -> None:
        captured: list[tuple[bytes, bytes]] = []
        provider = object()

        def provider_factory(
            config: CertificateGraphConfig,
            certificate_bytes: bytes,
            private_key_bytes: bytes,
        ) -> Any:
            self.certificate_path.write_bytes(b"mutated-after-read")
            captured.append((certificate_bytes, private_key_bytes))
            return provider

        factory = CertificateWriteIdentityFactory(
            config=self.config,
            write_principal_id=self.write_principal_id,
            expected_tenant_id="tenant-id",
            expected_certificate_sha256=self.certificate_sha256,
            expected_private_key_sha256=self.private_key_sha256,
            workspace_id="notary_team_01",
            site_binding_sha256="1" * 64,
            bff_principal_binding_sha256="2" * 64,
            inspection_principal_binding_sha256=INSPECTION_PRINCIPAL_BINDING,
            inspection_approval_sha256=INSPECTION_APPROVAL_SHA256,
            now_provider=lambda: IDENTITY_NOW,
            provider_factory=provider_factory,
        )

        self.assertIs(
            factory.build(_identity_context(self.write_principal_id)),
            provider,
        )
        self.assertEqual(
            captured,
            [(self.certificate_bytes, self.private_key_bytes)],
        )


class S4fCompositionStatusTests(unittest.TestCase):

    def test_status_is_partial_and_all_readiness_and_live_effect_flags_are_false(
        self,
    ) -> None:
        result = build_s4f_offline_composition_status()

        self.assertEqual(result["status"], S4F_STATUS)
        self.assertEqual(
            S4F_STATUS, "S4F_PARTIAL_ADAPTERS_VERIFIED_OFFLINE"
        )
        self.assertEqual(result["workspace_id"], "notary_team_01")
        self.assertIs(result["central_truth_claimed"], False)
        self.assertIs(result["production_readiness_claimed"], False)
        self.assertIs(result["runtime_composition_enabled"], False)
        self.assertIs(
            result["local_staging_outbox_can_close_mutation"], False
        )
        self.assertIs(result["live_state_inspected"], False)
        self.assertIs(result["live_write_authorized"], False)
        self.assertEqual(
            set(result["remaining_blockers"]),
            {
                "central_postgresql_outbox_promotion_ack_retention_cleanup",
                "durable_reconciliation_store",
                "broker_product_owner_decision",
                "synced_filesystem_runtime_detection",
                "signature_anchor_owner_decision",
                "production_identity_inspection_readback",
                "azure_blob_worm_rest_transport",
                "azure_blob_worm_policy_lock",
                "dedicated_entra_write_identity_and_site_grant",
            },
        )
        summary = result["summary"]
        self.assertIsInstance(summary, Mapping)
        self.assertEqual(
            {
                key: summary[key]
                for key in (
                    "socket_or_dns_calls",
                    "external_credential_store_reads",
                    "graph_calls",
                    "azure_calls",
                    "tenant_writes",
                )
            },
            {
                "socket_or_dns_calls": 0,
                "external_credential_store_reads": 0,
                "graph_calls": 0,
                "azure_calls": 0,
                "tenant_writes": 0,
            },
        )
        rendered = format_s4f_offline_composition_status(result)
        self.assertIn("Live write authorized: false", rendered)
        self.assertNotIn("RUNTIME_READY", rendered)
        self.assertNotIn("LIVE_READY", rendered)


if __name__ == "__main__":
    unittest.main()
