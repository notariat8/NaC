from __future__ import annotations

import hashlib
import json
import sys
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_runtime.azure_blob_worm_rest_transport import (
    AZURE_BLOB_API_VERSION,
    AZURE_MANAGEMENT_API_VERSION,
    AZURE_SUBSCRIPTION_API_VERSION,
    MAX_RESPONSE_BYTES,
    AzureBlobHttpResponse,
    AzureBlobWormRestBinding,
    AzureBlobWormRestTransport,
    AzureBlobWormRestTransportError,
)


TENANT_ID = "11111111-2222-4333-8444-555555555555"
SUBSCRIPTION_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
SUBSCRIPTION_RESOURCE_ID = f"/subscriptions/{SUBSCRIPTION_ID}"
STORAGE_ACCOUNT = "stnacwormoffline001"
STORAGE_RESOURCE_ID = (
    f"{SUBSCRIPTION_RESOURCE_ID}/resourceGroups/rg-nac-worm"
    f"/providers/Microsoft.Storage/storageAccounts/{STORAGE_ACCOUNT}"
)
CONTAINER = "nac-worm-tenant-a"
ENCRYPTION_SCOPE = "nac-worm-tenant-a"
CMK_IDENTIFIER = (
    "https://kv-nac.vault.azure.net/keys/worm/"
    "0123456789abcdef0123456789abcdef"
)
CMK_SHA256 = hashlib.sha256(CMK_IDENTIFIER.encode("utf-8")).hexdigest()
BLOB_NAME = f"tenant/{'a' * 64}/journal/commit-v1-{'b' * 32}.json"
VERSION_ID = "2026-07-29T22:00:00.0000000Z"
NOW = datetime(2026, 7, 29, 22, 0, tzinfo=timezone.utc)


class FakeTokenProvider:
    def __init__(self, token: object = "offline-token") -> None:
        self.token = token
        self.calls = 0

    def fetch_access_token(self) -> str:
        self.calls += 1
        if isinstance(self.token, BaseException):
            raise self.token
        return self.token  # type: ignore[return-value]


class RecordingHttpPort:
    def __init__(self) -> None:
        self.responses: list[object] = []
        self.calls: list[dict[str, Any]] = []

    def queue(self, *responses: object) -> None:
        self.responses.extend(responses)

    def request(self, **request: Any) -> AzureBlobHttpResponse:
        self.calls.append(request)
        if not self.responses:
            raise AssertionError("unexpected HTTP request")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response  # type: ignore[return-value]


def json_response(value: object, status: int = 200) -> AzureBlobHttpResponse:
    return AzureBlobHttpResponse(
        status_code=status,
        body=json.dumps(value, separators=(",", ":")).encode("utf-8"),
    )


def policy_responses() -> tuple[AzureBlobHttpResponse, ...]:
    container_id = (
        f"{STORAGE_RESOURCE_ID}/blobServices/default/containers/{CONTAINER}"
    )
    return (
        json_response(
            {
                "id": container_id,
                "type": (
                    "Microsoft.Storage/storageAccounts/"
                    "blobServices/containers"
                ),
                "properties": {
                    "immutableStorageWithVersioning": {"enabled": True},
                    "legalHold": {"hasLegalHold": False, "tags": []},
                    "defaultEncryptionScope": ENCRYPTION_SCOPE,
                    "denyEncryptionScopeOverride": True,
                },
            }
        ),
        json_response(
            {
                "id": f"{container_id}/immutabilityPolicies/default",
                "etag": '"policy-etag"',
                "properties": {
                    "state": "Locked",
                    "immutabilityPeriodSinceCreationInDays": 3653,
                },
            }
        ),
        json_response(
            {
                "id": (
                    f"{STORAGE_RESOURCE_ID}/encryptionScopes/"
                    f"{ENCRYPTION_SCOPE}"
                ),
                "name": ENCRYPTION_SCOPE,
                "properties": {
                    "state": "Enabled",
                    "source": "Microsoft.KeyVault",
                    "keyVaultProperties": {
                        "currentVersionedKeyIdentifier": CMK_IDENTIFIER
                    },
                },
            }
        ),
    )


class AzureBlobWormRestTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.binding = AzureBlobWormRestBinding(
            management_host="management.azure.com",
            blob_host=f"{STORAGE_ACCOUNT}.blob.core.windows.net",
            tenant_id=TENANT_ID,
            subscription_resource_id=SUBSCRIPTION_RESOURCE_ID,
            storage_account_resource_id=STORAGE_RESOURCE_ID,
            container_name=CONTAINER,
            encryption_scope=ENCRYPTION_SCOPE,
            customer_managed_key_ref_sha256=CMK_SHA256,
        )
        self.management_tokens = FakeTokenProvider("management-token")
        self.blob_tokens = FakeTokenProvider("blob-token")
        self.http = RecordingHttpPort()
        self.transport = AzureBlobWormRestTransport(
            binding=self.binding,
            management_token_provider=self.management_tokens,
            blob_token_provider=self.blob_tokens,
            http_port=self.http,
            utc_now=lambda: NOW,
        )

    def test_constructor_is_inert_and_hosts_are_exactly_bound(self) -> None:
        self.assertEqual(self.management_tokens.calls, 0)
        self.assertEqual(self.blob_tokens.calls, 0)
        self.assertEqual(self.http.calls, [])
        baseline = asdict(self.binding)
        invalid = (
            {**baseline, "management_host": "management.azure.test"},
            {**baseline, "blob_host": "127.0.0.1"},
            {
                **baseline,
                "storage_account_resource_id": (
                    f"{SUBSCRIPTION_RESOURCE_ID}/resourceGroups/rg/extra"
                    "/providers/Microsoft.Storage/storageAccounts/"
                    f"{STORAGE_ACCOUNT}"
                ),
            },
        )
        for values in invalid:
            with self.subTest(values=values):
                with self.assertRaisesRegex(
                    ValueError, r"\Aazure_blob_worm_binding_invalid\Z"
                ):
                    AzureBlobWormRestBinding(**values)

    def test_provider_context_uses_exact_management_gets(self) -> None:
        self.http.queue(
            json_response(
                {
                    "id": SUBSCRIPTION_RESOURCE_ID,
                    "subscriptionId": SUBSCRIPTION_ID,
                    "tenantId": TENANT_ID,
                }
            ),
            json_response(
                {
                    "id": STORAGE_RESOURCE_ID,
                    "name": STORAGE_ACCOUNT,
                    "type": "Microsoft.Storage/storageAccounts",
                }
            ),
        )

        context = self.transport.get_provider_context(CONTAINER)

        self.assertEqual(context.tenant_id, TENANT_ID)
        self.assertEqual(context.resource_id, STORAGE_RESOURCE_ID)
        self.assertEqual(
            [call["url"] for call in self.http.calls],
            [
                (
                    "https://management.azure.com"
                    f"{SUBSCRIPTION_RESOURCE_ID}?api-version="
                    f"{AZURE_SUBSCRIPTION_API_VERSION}"
                ),
                (
                    "https://management.azure.com"
                    f"{STORAGE_RESOURCE_ID}?api-version="
                    f"{AZURE_MANAGEMENT_API_VERSION}"
                ),
            ],
        )
        for call in self.http.calls:
            self.assertEqual(call["method"], "GET")
            self.assertIsNone(call["body"])
            self.assertFalse(call["follow_redirects"])
            self.assertEqual(call["automatic_retries"], 0)
            self.assertEqual(call["max_response_bytes"], MAX_RESPONSE_BYTES)
            self.assertEqual(
                call["headers"],
                {
                    "Authorization": "Bearer management-token",
                    "Accept": "application/json",
                },
            )

    def test_policy_cmk_scope_retention_and_legal_hold_are_read_only_attested(
        self,
    ) -> None:
        self.http.queue(*policy_responses())

        policy = self.transport.get_container_policy(CONTAINER)

        self.assertEqual(policy.default_immutability_policy_mode, "Locked")
        self.assertEqual(policy.default_retention_days, 3653)
        self.assertTrue(policy.legal_hold_capable)
        self.assertEqual(policy.encryption_scope, ENCRYPTION_SCOPE)
        self.assertEqual(policy.encryption_key_source, "Microsoft.Keyvault")
        self.assertEqual(policy.customer_managed_key_ref_sha256, CMK_SHA256)
        self.assertEqual(len(self.http.calls), 3)
        self.assertEqual({call["method"] for call in self.http.calls}, {"GET"})
        self.assertTrue(
            all(
                f"api-version={AZURE_MANAGEMENT_API_VERSION}" in call["url"]
                for call in self.http.calls
            )
        )
        self.assertFalse(
            any(
                "/lock" in call["url"]
                or call["method"] in {"POST", "PATCH", "PUT", "DELETE"}
                for call in self.http.calls
            )
        )

    def test_policy_attestation_fails_closed_without_exposing_cmk(self) -> None:
        responses = list(policy_responses())
        responses[-1] = json_response(
            {
                "id": (
                    f"{STORAGE_RESOURCE_ID}/encryptionScopes/"
                    f"{ENCRYPTION_SCOPE}"
                ),
                "name": ENCRYPTION_SCOPE,
                "properties": {
                    "state": "Enabled",
                    "source": "Microsoft.KeyVault",
                    "keyVaultProperties": {
                        "currentVersionedKeyIdentifier": "provider-secret"
                    },
                },
            }
        )
        self.http.queue(*responses)

        with self.assertRaises(AzureBlobWormRestTransportError) as caught:
            self.transport.get_container_policy(CONTAINER)

        self.assertEqual(
            str(caught.exception), "container_policy_attestation_failed"
        )
        self.assertNotIn("provider-secret", str(caught.exception))

    def test_create_only_201_returns_unique_readback_binding(self) -> None:
        self.http.queue(
            AzureBlobHttpResponse(
                status_code=201,
                body=b"",
                headers={
                    "ETag": '"blob-etag"',
                    "x-ms-version-id": VERSION_ID,
                },
            )
        )

        result = self.transport.put_blob_if_absent(
            CONTAINER,
            BLOB_NAME,
            b'{"evidence":true}',
            {"nac_head_sha256": "a" * 64},
            encryption_scope=ENCRYPTION_SCOPE,
            if_none_match="*",
        )

        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.version_id, VERSION_ID)
        call = self.http.calls[0]
        self.assertEqual(call["method"], "PUT")
        self.assertEqual(
            call["url"],
            (
                f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/"
                f"{CONTAINER}/{BLOB_NAME}"
            ),
        )
        self.assertEqual(call["headers"]["If-None-Match"], "*")
        self.assertEqual(call["headers"]["x-ms-blob-type"], "BlockBlob")
        self.assertEqual(
            call["headers"]["x-ms-encryption-scope"], ENCRYPTION_SCOPE
        )
        self.assertEqual(
            call["headers"]["x-ms-version"], AZURE_BLOB_API_VERSION
        )
        self.assertEqual(
            call["headers"]["Authorization"], "Bearer blob-token"
        )
        self.assertFalse(call["follow_redirects"])
        self.assertEqual(call["automatic_retries"], 0)

    def test_create_only_412_has_unambiguous_recovery_result(self) -> None:
        self.http.queue(
            AzureBlobHttpResponse(
                status_code=412,
                body=b"<Error>redacted by transport</Error>",
                headers={"x-ms-version-id": "must-not-be-trusted"},
            )
        )

        result = self.transport.put_blob_if_absent(
            CONTAINER,
            BLOB_NAME,
            b"body",
            {},
            encryption_scope=ENCRYPTION_SCOPE,
            if_none_match="*",
        )

        self.assertEqual(result.status_code, 412)
        self.assertIsNone(result.etag)
        self.assertIsNone(result.version_id)

    def test_create_rejects_missing_precondition_before_credentials(self) -> None:
        with self.assertRaises(AzureBlobWormRestTransportError) as caught:
            self.transport.put_blob_if_absent(
                CONTAINER,
                BLOB_NAME,
                b"body",
                {},
                encryption_scope=ENCRYPTION_SCOPE,
                if_none_match='"etag"',
            )
        self.assertEqual(str(caught.exception), "blob_create_not_allowed")
        self.assertEqual(self.blob_tokens.calls, 0)
        self.assertEqual(self.http.calls, [])

    def test_201_requires_exactly_one_etag_and_version(self) -> None:
        invalid_headers = (
            {"ETag": '"blob-etag"'},
            {"x-ms-version-id": VERSION_ID},
            {
                "ETag": '"blob-etag"',
                "etag": '"duplicate"',
                "x-ms-version-id": VERSION_ID,
            },
        )
        for headers in invalid_headers:
            with self.subTest(headers=headers):
                self.http.queue(
                    AzureBlobHttpResponse(201, b"", headers)
                )
                with self.assertRaises(AzureBlobWormRestTransportError):
                    self.transport.put_blob_if_absent(
                        CONTAINER,
                        BLOB_NAME,
                        b"body",
                        {},
                        encryption_scope=ENCRYPTION_SCOPE,
                        if_none_match="*",
                    )

    def test_list_versions_is_exact_and_rejects_pagination(self) -> None:
        self.http.queue(
            AzureBlobHttpResponse(
                200,
                (
                    "<EnumerationResults><Blobs>"
                    f"<Blob><Name>{BLOB_NAME}</Name>"
                    f"<VersionId>{VERSION_ID}</VersionId></Blob>"
                    "</Blobs><NextMarker /></EnumerationResults>"
                ).encode("ascii"),
            )
        )

        versions = self.transport.list_blob_versions(CONTAINER, BLOB_NAME)

        self.assertEqual(
            tuple(item.version_id for item in versions), (VERSION_ID,)
        )
        self.assertEqual(
            self.http.calls[0]["url"],
            (
                f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/"
                f"{CONTAINER}?restype=container&comp=list&include=versions"
                "&prefix=tenant%2F"
                f"{'a' * 64}%2Fjournal%2Fcommit-v1-"
                f"{'b' * 32}.json"
            ),
        )

        self.http.queue(
            AzureBlobHttpResponse(
                200,
                (
                    "<EnumerationResults><Blobs />"
                    "<NextMarker>secret-marker</NextMarker>"
                    "</EnumerationResults>"
                ).encode("ascii"),
            )
        )
        with self.assertRaises(AzureBlobWormRestTransportError) as caught:
            self.transport.list_blob_versions(CONTAINER, BLOB_NAME)
        self.assertEqual(
            str(caught.exception), "blob_version_list_incomplete"
        )

    def test_version_bound_get_attests_blob_and_policy(self) -> None:
        self.http.queue(
            AzureBlobHttpResponse(
                200,
                b'{"evidence":true}',
                {
                    "ETag": '"blob-etag"',
                    "x-ms-version-id": VERSION_ID,
                    "x-ms-creation-time": "Wed, 29 Jul 2026 22:00:00 GMT",
                    "x-ms-immutability-policy-until-date": (
                        "Mon, 29 Jul 2036 22:00:00 GMT"
                    ),
                    "x-ms-immutability-policy-mode": "locked",
                    "x-ms-encryption-scope": ENCRYPTION_SCOPE,
                    "x-ms-server-encrypted": "true",
                    "x-ms-meta-nac_head_sha256": "a" * 64,
                },
            ),
            *policy_responses(),
        )

        blob = self.transport.get_blob(
            CONTAINER, BLOB_NAME, version_id=VERSION_ID
        )

        self.assertEqual(blob.version_id, VERSION_ID)
        self.assertEqual(blob.created_at, "2026-07-29T22:00:00Z")
        self.assertEqual(blob.retention_until, "2036-07-29T22:00:00Z")
        self.assertEqual(blob.metadata, {"nac_head_sha256": "a" * 64})
        self.assertEqual(
            self.http.calls[0]["url"],
            (
                f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/"
                f"{CONTAINER}/{BLOB_NAME}?versionid="
                "2026-07-29T22%3A00%3A00.0000000Z"
            ),
        )
        self.assertEqual(
            [call["method"] for call in self.http.calls],
            ["GET", "GET", "GET", "GET"],
        )

    def test_response_limit_and_provider_failures_are_redacted(self) -> None:
        self.http.queue(
            AzureBlobHttpResponse(
                500,
                b"provider-secret:" + b"x" * MAX_RESPONSE_BYTES,
            )
        )
        with self.assertRaises(AzureBlobWormRestTransportError) as caught:
            self.transport.list_blob_versions(CONTAINER, BLOB_NAME)
        self.assertEqual(str(caught.exception), "http_response_invalid")
        self.assertNotIn("provider-secret", str(caught.exception))

        self.http.queue(RuntimeError("token-and-provider-secret"))
        with self.assertRaises(AzureBlobWormRestTransportError) as caught:
            self.transport.list_blob_versions(CONTAINER, BLOB_NAME)
        self.assertEqual(
            str(caught.exception), "http_transport_unavailable"
        )
        self.assertNotIn("secret", str(caught.exception))

    def test_wrong_container_and_blob_path_cannot_reach_ports(self) -> None:
        for container, blob_name in (
            ("other-container", BLOB_NAME),
            (CONTAINER, "../policy/lock"),
            (CONTAINER, f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"),
        ):
            with self.subTest(container=container, blob_name=blob_name):
                with self.assertRaises(AzureBlobWormRestTransportError):
                    self.transport.list_blob_versions(container, blob_name)
        self.assertEqual(self.blob_tokens.calls, 0)
        self.assertEqual(self.http.calls, [])


if __name__ == "__main__":
    unittest.main()
