"""Archived tests for the superseded direct local Azure Storage lease path.

The active performance lane uses the BFF broker/system-identity boundary and its focused
test modules.  This file remains as migration history and is intentionally not
part of unittest discovery.
"""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from unittest import mock
from uuid import UUID

from nac_bff.azure_activation_attestations import TOOLCHAIN_ATTESTATION_FIELDS
import nac_bff.azure_performance_acceptance as performance_acceptance
import nac_bff.azure_performance_authorization as performance_authorization
import nac_bff.azure_performance_infrastructure_safety as infrastructure_safety
import nac_bff.azure_performance_lease as performance_lease
from nac_bff.azure_performance_authorization import (
    BLOB_BOOTSTRAP,
    BLOB_LEASE_ACQUIRE,
    BLOB_LEASE_ASSERT_HELD,
    BLOB_LEASE_RELEASE,
)
from nac_bff.azure_performance_lease import (
    AzureBlobLeaseAdapter,
    AzureBlobLeaseBinding,
    AzureBlobLeaseBootstrapAdapter,
    AzureBlobLeaseBootstrapBinding,
    AzureBlobLeaseError,
    _issue_attested_azure_storage_access_token,
    build_lease_acquisition_safety_evidence,
    calculate_azure_blob_lease_bootstrap_binding_sha256,
    lease_bootstrap_policy,
    lease_bootstrap_policy_sha256,
    lease_policy,
    lease_policy_sha256,
)
from nac_bff.azure_performance_infrastructure_safety import (
    BOOTSTRAP_ALLOWED_DATA_ACTIONS,
    RUNTIME_ALLOWED_DATA_ACTIONS,
    AzurePerformanceInfrastructureReadbackAdapter,
    AzurePerformanceInfrastructureSafetyVerification,
    begin_azure_performance_infrastructure_readback_session,
    effective_coordination_tags,
    exact_bootstrap_lease_blob_condition,
    exact_runtime_lease_blob_condition,
    verify_azure_performance_infrastructure_safety,
)
from nac_bff.azure_performance_monitor import monitor_policy_sha256


TARGET_SHA256 = "1" * 64
READ_IDENTITY_SHA256 = "2" * 64
WRITE_IDENTITY_SHA256 = "3" * 64
BOOTSTRAP_READ_IDENTITY_SHA256 = "4" * 64
BOOTSTRAP_WRITE_IDENTITY_SHA256 = "5" * 64
OWNER_APPROVAL_BODY_SHA256 = "9" * 64
EXPECTED_ETAG = '"0x8DBABCDEF012345"'
TOKEN_SUBJECT = "11111111-2222-4333-8444-555555555555"
BOOTSTRAP_TOKEN_SUBJECT = "66666666-2222-4333-8444-555555555555"
TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
COORDINATION_RESOURCE_ID = (
    "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
    "resourceGroups/rg-nac-bff-test/providers/Microsoft.Storage/"
    "storageAccounts/nacperflease001"
)
BFF_RESOURCE_ID = (
    "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
    "resourceGroups/rg-nac-bff-test/providers/Microsoft.Storage/"
    "storageAccounts/nacbffdeploy001"
)
WORM_RESOURCE_ID = (
    "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
    "resourceGroups/rg-nac-worm/providers/Microsoft.Storage/"
    "storageAccounts/nacwormevidence001"
)
LEASE_ID = UUID("12345678-1234-4abc-8def-1234567890ab")
OTHER_LEASE_ID = UUID("87654321-4321-4abc-8def-ba0987654321")
API_VERSION = "2023-11-03"
BASE_URL = (
    "https://nacperflease001.blob.core.windows.net/"
    f"nac-bff-performance-leases/locks/{TARGET_SHA256}.lock"
)
LEASE_URL = f"{BASE_URL}?comp=lease"
FIXED_DATE = "Mon, 03 Aug 2026 12:00:00 GMT"
FIXED_NOW = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
FIXED_NOW_TIMESTAMP = int(FIXED_NOW.timestamp())


def _issue_test_live_action_capability(
    *,
    target_binding_sha256: str,
    action_bindings: dict[str, tuple[str, int]],
):
    bindings = dict(action_bindings)
    bindings.setdefault(
        performance_authorization.TARGET_GET,
        (target_binding_sha256, 1),
    )
    owner = object.__new__(performance_acceptance.PerformanceExecutionAuthorization)
    execution_bindings = {
        "contract_sha256": "4" * 64,
        "expected_activation_hash": "5" * 64,
        "phase_plan_sha256": "6" * 64,
        "monitor_policy_sha256": monitor_policy_sha256(),
        "monitor_window_anchor_sha256": "7" * 64,
        "owner_approval_body_sha256": OWNER_APPROVAL_BODY_SHA256,
        "target_binding_sha256": target_binding_sha256,
        "infrastructure_safety_policy_sha256": "8" * 64,
        "infrastructure_safety_evidence_sha256": "a" * 64,
    }
    owner_fields = {
        "status": "VERIFIED",
        "owner_login": performance_acceptance.REQUIRED_OWNER_LOGIN,
        "owner_approval_reference_sha256": "b" * 64,
        "owner_approval_body_sha256": OWNER_APPROVAL_BODY_SHA256,
        "action": performance_acceptance.OWNER_ACTION,
        "correlation_id": "lease-adapter-unit-test",
        "contract_sha256": execution_bindings["contract_sha256"],
        "activation_hash": execution_bindings["expected_activation_hash"],
        "activation_receipt_sha256": "c" * 64,
        "activation_evidence_sha256": "d" * 64,
        "target_binding_sha256": target_binding_sha256,
        "measurement_preflight_sha256": "e" * 64,
        "phase_plan_sha256": execution_bindings["phase_plan_sha256"],
        "monitor_window_anchor_sha256": execution_bindings[
            "monitor_window_anchor_sha256"
        ],
        "interruption_terminalization_status": (
            "VERIFIED_BY_COMMITTED_ACTIVATION_RECEIPT"
        ),
    }
    for name, value in owner_fields.items():
        object.__setattr__(owner, name, value)
    object.__setattr__(
        owner, "_seal", performance_acceptance._EXECUTION_AUTHORIZATION_SEAL
    )
    performance_acceptance._ISSUED_EXECUTION_AUTHORIZATIONS[id(owner)] = owner

    safety = dict.__new__(AzurePerformanceInfrastructureSafetyVerification)
    dict.__init__(
        safety,
        {
            "owner_binding_sha256": OWNER_APPROVAL_BODY_SHA256,
            "target_binding_sha256": target_binding_sha256,
            "infrastructure_safety_policy_sha256": execution_bindings[
                "infrastructure_safety_policy_sha256"
            ],
            "infrastructure_safety_evidence_sha256": execution_bindings[
                "infrastructure_safety_evidence_sha256"
            ],
        },
    )
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        checkpoint = root / "checkpoint"
        with mock.patch.object(
            performance_authorization,
            "validate_infrastructure_safety_evidence",
            return_value=safety,
        ):
            authority = performance_authorization._issue_verified_performance_authority(
                owner_authorization=owner,
                infrastructure_safety_verification=safety,
                execution_bindings=execution_bindings,
                action_bindings=bindings,
                repo_root=root,
                run_binding_sha256="f" * 64,
                checkpoint_commit_path=checkpoint / "state.commit.redacted.json",
                checkpoint_slot_paths={
                    "a": checkpoint / "state.slot-a.redacted.json",
                    "b": checkpoint / "state.slot-b.redacted.json",
                },
                final_evidence_path=checkpoint / "evidence.redacted.json",
            )
    return authority.capability


def _lease_capability(adapter: AzureBlobLeaseAdapter, uses: int = 4096):
    return _issue_test_live_action_capability(
        target_binding_sha256=adapter.target_binding_sha256,
        action_bindings={
            BLOB_LEASE_ACQUIRE: (adapter.lease_binding_sha256, uses),
            BLOB_LEASE_ASSERT_HELD: (adapter.lease_binding_sha256, uses),
            BLOB_LEASE_RELEASE: (adapter.lease_binding_sha256, uses),
        },
    )


def _bootstrap_capability(adapter: AzureBlobLeaseBootstrapAdapter, uses: int = 4):
    return _issue_test_live_action_capability(
        target_binding_sha256=adapter._binding.target_binding_sha256,
        action_bindings={
            BLOB_BOOTSTRAP: (adapter.bootstrap_binding_sha256, uses),
        },
    )


class _FdBackedTestRuntime:
    def __init__(self, executable: Path) -> None:
        self._descriptor = os.open(executable, os.O_RDONLY)
        self.pass_fds = (self._descriptor,)

    def command(self, azure_argv: list[str]) -> list[str]:
        return [f"/proc/self/fd/{self._descriptor}", *azure_argv]

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        os.close(self._descriptor)


def _prepare_test_runtime(path: Path, **_kwargs: object):
    return _FdBackedTestRuntime(path)
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _jwt(
    *,
    omit: tuple[str, ...] = (),
    algorithm: str = "RS256",
    **updates: object,
) -> str:
    claims = {
        "aud": "https://storage.azure.com",
        "exp": FIXED_NOW_TIMESTAMP + 24 * 60 * 60,
        "nbf": FIXED_NOW_TIMESTAMP - 60,
        "oid": TOKEN_SUBJECT,
        "tid": TENANT_ID,
    }
    claims.update(updates)
    for name in omit:
        claims.pop(name, None)

    def encode(value: object) -> str:
        return base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":"), sort_keys=True).encode("ascii")
        ).decode("ascii").rstrip("=")

    return f"{encode({'alg': algorithm})}.{encode(claims)}.signature"


STORAGE_TOKEN = _jwt()


def _attested_storage_token(
    token: str = STORAGE_TOKEN,
    *,
    identity_binding_sha256: str = WRITE_IDENTITY_SHA256,
    source_attestation_sha256: str | None = None,
):
    encoded = token.split(".")[1]
    claims = json.loads(
        base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    )
    return _issue_attested_azure_storage_access_token(
        token,
        scope=(
            "https://storage.azure.com/.default"
            if claims.get("aud") == "https://storage.azure.com"
            else claims.get("aud")
        ),
        identity_binding_sha256=identity_binding_sha256,
        subject=claims.get("oid"),
        tenant_id=claims.get("tid"),
        not_before=claims.get("nbf"),
        expires_at=claims.get("exp"),
        source_attestation_sha256=(
            source_attestation_sha256 or identity_binding_sha256
        ),
    )


class _Response:
    def __init__(
        self,
        status: int,
        url: str,
        headers: dict[str, str],
        body: bytes = b"",
    ) -> None:
        self.status = status
        self._url = url
        self.headers = headers
        self._body = body
        self.closed = False

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self._url

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            result, self._body = self._body, b""
            return result
        result, self._body = self._body[:size], self._body[size:]
        return result

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class _Opener:
    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[object, int]] = []

    def open(self, request: object, *, timeout: int) -> _Response:
        self.calls.append((request, timeout))
        if not self.outcomes:
            raise AssertionError("unexpected network call")
        outcome = self.outcomes.pop(0)
        if callable(outcome):
            outcome = outcome(request)
        if isinstance(outcome, BaseException):
            raise outcome
        assert isinstance(outcome, _Response)
        return outcome


class _TokenProvider:
    def __init__(self, token: str | None = None) -> None:
        self.token = token
        self.calls: list[dict[str, str]] = []

    def __call__(self, **kwargs: str):
        self.calls.append(kwargs)
        token = self.token
        if token is None:
            token = (
                _jwt(oid=BOOTSTRAP_TOKEN_SUBJECT)
                if kwargs["identity_binding_sha256"]
                in {
                    BOOTSTRAP_READ_IDENTITY_SHA256,
                    BOOTSTRAP_WRITE_IDENTITY_SHA256,
                }
                else STORAGE_TOKEN
            )
        return _attested_storage_token(
            token,
            identity_binding_sha256=kwargs["identity_binding_sha256"],
        )


def _binding(**updates: str) -> AzureBlobLeaseBinding:
    values = {
        "account_name": "nacperflease001",
        "bff_account_name": "nacbffdeploy001",
        "worm_account_name": "nacwormevidence001",
        "coordination_storage_account_resource_id": COORDINATION_RESOURCE_ID,
        "owner_approval_body_sha256": OWNER_APPROVAL_BODY_SHA256,
        "token_subject": TOKEN_SUBJECT,
        "token_tenant_id": TENANT_ID,
        "target_binding_sha256": TARGET_SHA256,
        "expected_etag": EXPECTED_ETAG,
        "read_identity_binding_sha256": READ_IDENTITY_SHA256,
        "write_identity_binding_sha256": WRITE_IDENTITY_SHA256,
    }
    values.update(updates)
    return AzureBlobLeaseBinding(**values)


def _bootstrap_binding(**updates: str) -> AzureBlobLeaseBootstrapBinding:
    values = {
        "account_name": "nacperflease001",
        "bff_account_name": "nacbffdeploy001",
        "worm_account_name": "nacwormevidence001",
        "coordination_storage_account_resource_id": COORDINATION_RESOURCE_ID,
        "owner_approval_body_sha256": OWNER_APPROVAL_BODY_SHA256,
        "token_subject": BOOTSTRAP_TOKEN_SUBJECT,
        "token_tenant_id": TENANT_ID,
        "target_binding_sha256": TARGET_SHA256,
        "read_identity_binding_sha256": BOOTSTRAP_READ_IDENTITY_SHA256,
        "write_identity_binding_sha256": BOOTSTRAP_WRITE_IDENTITY_SHA256,
        "runtime_token_subject": TOKEN_SUBJECT,
        "runtime_read_identity_binding_sha256": READ_IDENTITY_SHA256,
        "runtime_write_identity_binding_sha256": WRITE_IDENTITY_SHA256,
    }
    values.update(updates)
    return AzureBlobLeaseBootstrapBinding(**values)


_SAFETY_LOCATION = "germanywestcentral"
_SAFETY_TAGS = {"environment": "test", "system": "nac"}
_SAFETY_ALLOWED_IP = "8.8.8.8"
_SAFETY_TOOLCHAIN_SHA256 = "7" * 64
_SAFETY_GROUP_ID = "abcdef02-2222-4333-8444-555555555555"
_SAFETY_RUNTIME_GROUP_ID = "abcdef04-2222-4333-8444-555555555555"
_SAFETY_CACHE: dict[tuple[str, ...], object] = {}
_ADAPTER_TOOLCHAIN = {
    name: ("a" if name == "azure_cli_toolchain_sha256" else "b") * 64
    for name in TOOLCHAIN_ATTESTATION_FIELDS
}


def _canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


def _storage_parts(resource_id: str) -> tuple[str, str, str]:
    parts = resource_id.split("/")
    return parts[2], parts[4], parts[-1]


def _fixture_storage(
    name: str,
    resource_id: str,
    *,
    coordination_id: str,
    target_binding_sha256: str,
) -> dict[str, object]:
    if resource_id != coordination_id:
        return {"id": resource_id, "name": name}
    return {
        "id": resource_id,
        "name": name,
        "type": "Microsoft.Storage/storageAccounts",
        "location": _SAFETY_LOCATION,
        "kind": "StorageV2",
        "sku": {"name": "Standard_LRS", "tier": "Standard"},
        "tags": effective_coordination_tags(
            _SAFETY_TAGS, target_binding_sha256
        ),
        "properties": {
            "accessTier": "Hot",
            "allowBlobPublicAccess": False,
            "allowCrossTenantReplication": False,
            "allowSharedKeyAccess": False,
            "defaultToOAuthAuthentication": True,
            "isHnsEnabled": False,
            "minimumTlsVersion": "TLS1_2",
            "networkAcls": {
                "bypass": "None",
                "defaultAction": "Deny",
                "ipRules": [
                    {"action": "Allow", "value": _SAFETY_ALLOWED_IP}
                ],
                "resourceAccessRules": [],
                "virtualNetworkRules": [],
            },
            "publicNetworkAccess": "Enabled",
            "supportsHttpsTrafficOnly": True,
        },
    }


def _fixture_blob_service(coordination_id: str) -> dict[str, object]:
    return {
        "id": f"{coordination_id}/blobServices/default",
        "name": "default",
        "type": "Microsoft.Storage/storageAccounts/blobServices",
        "properties": {
            "isVersioningEnabled": False,
            "deleteRetentionPolicy": {"enabled": False},
            "containerDeleteRetentionPolicy": {"enabled": False},
        },
    }


def _fixture_lease_container(
    coordination_id: str, target_binding_sha256: str
) -> dict[str, object]:
    return {
        "id": (
            f"{coordination_id}/blobServices/default/containers/"
            "nac-bff-performance-leases"
        ),
        "name": "nac-bff-performance-leases",
        "type": "Microsoft.Storage/storageAccounts/blobServices/containers",
        "properties": {
            "publicAccess": "None",
            "metadata": {
                "nac_schema_version": (
                    "nac.azure-bff-performance-coordination/v1"
                ),
                "data_classification": "synthetic-only",
                "lease_blob_path": f"locks/{target_binding_sha256}.lock",
                "lease_blob_type": "BlockBlob",
                "lease_blob_content_length": "0",
                "lease_blob_bootstrap": (
                    "owner-gated-put-if-absent-before-runtime"
                ),
                "bootstrap_authorization": (
                    "blob-read-plus-add-only-no-write-no-delete"
                ),
                "runtime_authorization": (
                    "blob-read-plus-write-only-no-add-no-delete"
                ),
                "azure_blob_write_authorization": (
                    "runtime-write-includes-create-overwrite-lease-and-break"
                ),
                "operation_restriction_boundary": (
                    "sealed-app-api-defense-in-depth-not-azure-enforced"
                ),
                "principal_separation": (
                    "distinct-owner-bound-bootstrap-and-runtime-principals"
                ),
            },
        },
    }


def _fixture_role_definition(
    resource_group_scope: str, role_definition_id: str, *, runtime: bool = False
) -> dict[str, object]:
    return {
        "id": role_definition_id,
        "properties": {
            "type": "CustomRole",
            "assignableScopes": [resource_group_scope],
            "permissions": [
                {
                    "actions": [],
                    "notActions": [],
                    "dataActions": sorted(
                        RUNTIME_ALLOWED_DATA_ACTIONS
                        if runtime
                        else BOOTSTRAP_ALLOWED_DATA_ACTIONS
                    ),
                    "notDataActions": [],
                }
            ],
        },
    }


def _fixture_role_assignment(
    *,
    container_scope: str,
    principal_id: str,
    role_definition_id: str,
    role_assignment_id: str,
    target_binding_sha256: str,
    runtime: bool = False,
) -> dict[str, object]:
    return {
        "id": role_assignment_id,
        "scope": container_scope,
        "properties": {
            "principalId": principal_id,
            "principalType": "ServicePrincipal",
            "roleDefinitionId": role_definition_id,
            "conditionVersion": "2.0",
            "condition": (
                exact_runtime_lease_blob_condition(target_binding_sha256)
                if runtime
                else exact_bootstrap_lease_blob_condition(
                    target_binding_sha256
                )
            ),
        },
    }


def _fixture_responses(
    *,
    tenant_id: str,
    bootstrap_principal_id: str,
    runtime_principal_id: str,
    target_binding_sha256: str,
    coordination_id: str,
    bff_id: str,
    worm_id: str,
    deployment_started_at: datetime,
    deployment_completed_at: datetime,
) -> tuple[dict[str, object], dict[str, object]]:
    subscription_id, resource_group_name, coordination_name = _storage_parts(
        coordination_id
    )
    _, _, bff_name = _storage_parts(bff_id)
    _, _, worm_name = _storage_parts(worm_id)
    resource_group_scope = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}"
    )
    container_scope = (
        f"{coordination_id}/blobServices/default/containers/"
        "nac-bff-performance-leases"
    )
    role_definition_id = (
        f"{resource_group_scope}/providers/Microsoft.Authorization/"
        "roleDefinitions/22222222-2222-4333-8444-555555555555"
    )
    role_assignment_id = (
        f"{container_scope}/providers/Microsoft.Authorization/"
        "roleAssignments/33333333-2222-4333-8444-555555555555"
    )
    runtime_role_definition_id = (
        f"{resource_group_scope}/providers/Microsoft.Authorization/"
        "roleDefinitions/22222223-2222-4333-8444-555555555555"
    )
    runtime_role_assignment_id = (
        f"{container_scope}/providers/Microsoft.Authorization/"
        "roleAssignments/33333334-2222-4333-8444-555555555555"
    )
    deployment_id = (
        f"{resource_group_scope}/providers/Microsoft.Resources/deployments/"
        "nac-bff-performance-coordination"
    )
    root_management_group = (
        f"/providers/Microsoft.Management/managementGroups/{tenant_id}"
    )
    child_management_group = (
        "/providers/Microsoft.Management/managementGroups/nac-test-platform"
    )
    role_definition = _fixture_role_definition(
        resource_group_scope, role_definition_id
    )
    role_assignment = _fixture_role_assignment(
        container_scope=container_scope,
        principal_id=bootstrap_principal_id,
        role_definition_id=role_definition_id,
        role_assignment_id=role_assignment_id,
        target_binding_sha256=target_binding_sha256,
    )
    runtime_role_definition = _fixture_role_definition(
        resource_group_scope, runtime_role_definition_id, runtime=True
    )
    runtime_role_assignment = _fixture_role_assignment(
        container_scope=container_scope,
        principal_id=runtime_principal_id,
        role_definition_id=runtime_role_definition_id,
        role_assignment_id=runtime_role_assignment_id,
        target_binding_sha256=target_binding_sha256,
        runtime=True,
    )
    deployment_parameters = {
        "tenantId": tenant_id,
        "subscriptionId": subscription_id,
        "resourceGroupName": resource_group_name,
        "storageAccountName": coordination_name,
        "bootstrapPrincipalId": bootstrap_principal_id,
        "runtimePrincipalId": runtime_principal_id,
        "allowedClientIpAddress": _SAFETY_ALLOWED_IP,
        "targetBindingSha256": target_binding_sha256,
        "location": _SAFETY_LOCATION,
        "tags": _SAFETY_TAGS,
    }
    deployment = {
        "id": deployment_id,
        "properties": {
            "provisioningState": "Succeeded",
            "startTime": deployment_started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timestamp": deployment_completed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "parameters": {
                name: {"value": value}
                for name, value in deployment_parameters.items()
            },
        },
    }
    ancestors = [
        "/",
        root_management_group,
        child_management_group,
        f"/subscriptions/{subscription_id}",
        resource_group_scope,
        coordination_id,
        f"{coordination_id}/blobServices/default",
        container_scope,
    ]
    responses: dict[str, object] = {
        f"https://management.azure.com{bff_id}?api-version=2023-05-01": (
            _fixture_storage(
                bff_name,
                bff_id,
                coordination_id=coordination_id,
                target_binding_sha256=target_binding_sha256,
            )
        ),
        f"https://management.azure.com{worm_id}?api-version=2023-05-01": (
            _fixture_storage(
                worm_name,
                worm_id,
                coordination_id=coordination_id,
                target_binding_sha256=target_binding_sha256,
            )
        ),
        f"https://management.azure.com{coordination_id}?api-version=2023-05-01": (
            _fixture_storage(
                coordination_name,
                coordination_id,
                coordination_id=coordination_id,
                target_binding_sha256=target_binding_sha256,
            )
        ),
        (
            f"https://management.azure.com{coordination_id}/blobServices/default"
            "?api-version=2023-05-01"
        ): _fixture_blob_service(coordination_id),
        (
            f"https://management.azure.com{container_scope}"
            "?api-version=2023-05-01"
        ): _fixture_lease_container(coordination_id, target_binding_sha256),
        f"https://management.azure.com{deployment_id}?api-version=2022-09-01": (
            deployment
        ),
        f"https://management.azure.com{role_definition_id}?api-version=2022-04-01": (
            role_definition
        ),
        f"https://management.azure.com{role_assignment_id}?api-version=2022-04-01": (
            role_assignment
        ),
        f"https://management.azure.com{runtime_role_definition_id}?api-version=2022-04-01": (
            runtime_role_definition
        ),
        f"https://management.azure.com{runtime_role_assignment_id}?api-version=2022-04-01": (
            runtime_role_assignment
        ),
        (
            f"https://management.azure.com{root_management_group}"
            "?api-version=2021-04-01&$expand=children&$recurse=true"
        ): {
            "id": root_management_group,
            "properties": {
                "children": [
                    {
                        "id": child_management_group,
                        "properties": {
                            "children": [
                                {"id": f"/subscriptions/{subscription_id}"}
                            ]
                        },
                    }
                ]
            },
        },
        (
            f"https://graph.microsoft.com/v1.0/servicePrincipals/"
            f"{bootstrap_principal_id}/"
            "transitiveMemberOf/microsoft.graph.group?$select=id"
        ): {"value": [{"id": _SAFETY_GROUP_ID}]},
        (
            f"https://graph.microsoft.com/v1.0/servicePrincipals/"
            f"{runtime_principal_id}/"
            "transitiveMemberOf/microsoft.graph.group?$select=id"
        ): {"value": [{"id": _SAFETY_RUNTIME_GROUP_ID}]},
    }
    name_resource = (
        f"/subscriptions/{subscription_id}/providers/Microsoft.Storage/"
        "checkNameAvailability"
    )
    responses[
        f"https://management.azure.com{name_resource}?api-version=2023-05-01"
    ] = {"nameAvailable": True}
    for scope in ancestors:
        prefix = "" if scope == "/" else scope
        url = (
            f"https://management.azure.com{prefix}/providers/"
            "Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
            "&$filter=atScope()"
        )
        responses[url] = {
            "value": (
                [role_assignment, runtime_role_assignment]
                if scope == container_scope
                else []
            )
        }
    arguments = {
        "coordination_storage_account_name": coordination_name,
        "coordination_storage_account_resource_id": coordination_id,
        "bff_storage_account_resource_id": bff_id,
        "worm_storage_account_resource_id": worm_id,
        "bootstrap_principal_id": bootstrap_principal_id,
        "runtime_principal_id": runtime_principal_id,
        "target_binding_sha256": target_binding_sha256,
        "tenant_id": tenant_id,
        "subscription_id": subscription_id,
        "resource_group_name": resource_group_name,
        "location": _SAFETY_LOCATION,
        "tags": _SAFETY_TAGS,
        "allowed_client_ip_address": _SAFETY_ALLOWED_IP,
        "deployment_id": deployment_id,
        "role_definition_id": role_definition_id,
        "role_assignment_id": role_assignment_id,
        "runtime_role_definition_id": runtime_role_definition_id,
        "runtime_role_assignment_id": runtime_role_assignment_id,
        "root_management_group": root_management_group,
        "container_scope": container_scope,
        "ancestors": ancestors,
    }
    return responses, arguments


def _write_fixture_azure_cli(
    directory: Path, responses: dict[str, object]
) -> Path:
    executable = directory / "az"
    source = f"""#!{sys.executable}
import json
import sys
args = sys.argv[1:]
url = args[args.index('--url') + 1]
responses = json.loads({json.dumps(json.dumps(responses, separators=(',', ':'), sort_keys=True))})
if url not in responses:
    print('unexpected URL: ' + url, file=sys.stderr)
    raise SystemExit(64)
print(json.dumps(responses[url], separators=(',', ':'), sort_keys=True))
"""
    executable.write_text(source, encoding="utf-8")
    executable.chmod(0o755)
    return executable


def _at(
    when: datetime, function: Callable[..., object], *args: object, **kwargs: object
) -> object:
    with mock.patch.object(
        infrastructure_safety, "_trusted_now", return_value=when
    ):
        return function(*args, **kwargs)


def _issue_complete_infrastructure_safety_evidence(
    *,
    owner_binding_sha256: str,
    tenant_id: str,
    bootstrap_principal_id: str,
    runtime_principal_id: str,
    target_binding_sha256: str,
    coordination_id: str,
    bff_id: str,
    worm_id: str,
    verified_at_utc: str,
) -> dict[str, object]:
    cache_key = (
        owner_binding_sha256,
        tenant_id,
        bootstrap_principal_id,
        runtime_principal_id,
        target_binding_sha256,
        coordination_id,
        bff_id,
        worm_id,
        verified_at_utc,
    )
    cached = _SAFETY_CACHE.get(cache_key)
    if cached is not None:
        return cached
    verified_at = datetime.strptime(
        verified_at_utc, "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    session_at = verified_at - timedelta(minutes=5)
    name_at = session_at + timedelta(seconds=1)
    deployment_started_at = session_at + timedelta(seconds=2)
    deployment_completed_at = session_at + timedelta(seconds=3)
    deployment_at = session_at + timedelta(seconds=4)
    postdeployment_at = session_at + timedelta(minutes=1, seconds=1)
    responses, values = _fixture_responses(
        tenant_id=tenant_id,
        bootstrap_principal_id=bootstrap_principal_id,
        runtime_principal_id=runtime_principal_id,
        target_binding_sha256=target_binding_sha256,
        coordination_id=coordination_id,
        bff_id=bff_id,
        worm_id=worm_id,
        deployment_started_at=deployment_started_at,
        deployment_completed_at=deployment_completed_at,
    )
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        fake_az = _write_fixture_azure_cli(directory, responses)
        with mock.patch.object(
            infrastructure_safety, "AZURE_CLI_EXECUTION_PATH", fake_az
        ), mock.patch.object(
            infrastructure_safety,
            "calculate_azure_cli_toolchain_sha256",
            return_value="a" * 64,
        ), mock.patch.object(
            infrastructure_safety,
            "calculate_toolchain_attestations_sha256",
            return_value=_SAFETY_TOOLCHAIN_SHA256,
        ), mock.patch.object(
            infrastructure_safety,
            "_READBACK_REPLAY_LEDGER_DIRECTORY",
            directory / "replay-ledger",
        ):
            session = _at(
                session_at,
                begin_azure_performance_infrastructure_readback_session,
                owner_approval_body_sha256=owner_binding_sha256,
                toolchain_attestations_sha256=_SAFETY_TOOLCHAIN_SHA256,
            )
            adapter = AzurePerformanceInfrastructureReadbackAdapter(
                session, toolchain_attestations=_ADAPTER_TOOLCHAIN
            )
            name = _at(
                name_at,
                adapter.check_storage_account_name_availability,
                subscription_id=values["subscription_id"],
                storage_account_name=values[
                    "coordination_storage_account_name"
                ],
            )
            deployment = _at(
                deployment_at,
                adapter.execute_read,
                observation_kind="coordination-deployment-receipt",
                resource_id=values["deployment_id"],
            )

            def post(function: Callable[..., object], **kwargs: object) -> object:
                return _at(postdeployment_at, function, **kwargs)

            arguments = {
                "readback_session": adapter.verification_capability,
                "coordination_storage_account_name": values[
                    "coordination_storage_account_name"
                ],
                "coordination_name_readback_envelope": name,
                "deployment_receipt_envelope": deployment,
                "coordination_storage_readback_envelope": post(
                    adapter.execute_read,
                    observation_kind=(
                        "coordination-storage-account-configuration"
                    ),
                    resource_id=coordination_id,
                ),
                "coordination_blob_service_readback_envelope": post(
                    adapter.execute_read,
                    observation_kind=(
                        "coordination-blob-service-configuration"
                    ),
                    resource_id=f"{coordination_id}/blobServices/default",
                ),
                "lease_container_readback_envelope": post(
                    adapter.execute_read,
                    observation_kind=(
                        "coordination-lease-container-configuration"
                    ),
                    resource_id=values["container_scope"],
                ),
                "coordination_storage_account_resource_id": coordination_id,
                "bff_storage_account_resource_id": bff_id,
                "worm_storage_account_resource_id": worm_id,
                "bff_storage_readback_envelope": post(
                    adapter.execute_read,
                    observation_kind="bff-storage-account-resource-id",
                    resource_id=bff_id,
                ),
                "worm_storage_readback_envelope": post(
                    adapter.execute_read,
                    observation_kind="worm-storage-account-resource-id",
                    resource_id=worm_id,
                ),
                "bootstrap_principal_id": bootstrap_principal_id,
                "runtime_principal_id": runtime_principal_id,
                "target_binding_sha256": target_binding_sha256,
                "bootstrap_role_definition": post(
                    adapter.execute_read,
                    observation_kind="coordination-role-definition",
                    resource_id=values["role_definition_id"],
                ),
                "runtime_role_definition": post(
                    adapter.execute_read,
                    observation_kind="coordination-role-definition",
                    resource_id=values["runtime_role_definition_id"],
                ),
                "bootstrap_role_assignment": post(
                    adapter.execute_read,
                    observation_kind="coordination-role-assignment",
                    resource_id=values["role_assignment_id"],
                ),
                "runtime_role_assignment": post(
                    adapter.execute_read,
                    observation_kind="coordination-role-assignment",
                    resource_id=values["runtime_role_assignment_id"],
                ),
                "subscription_ancestry_readback_envelope": post(
                    adapter.read_management_group_ancestry,
                    tenant_id=tenant_id,
                    subscription_id=values["subscription_id"],
                ),
                "bootstrap_effective_rbac_readback_envelope": post(
                    adapter.read_effective_rbac,
                    principal_id=bootstrap_principal_id,
                    target_resource_id=values["container_scope"],
                    ancestor_scopes=values["ancestors"],
                ),
                "runtime_effective_rbac_readback_envelope": post(
                    adapter.read_effective_rbac,
                    principal_id=runtime_principal_id,
                    target_resource_id=values["container_scope"],
                    ancestor_scopes=values["ancestors"],
                ),
                "tenant_id": tenant_id,
                "subscription_id": values["subscription_id"],
                "resource_group_name": values["resource_group_name"],
                "location": _SAFETY_LOCATION,
                "tags": _SAFETY_TAGS,
                "allowed_client_ip_address": _SAFETY_ALLOWED_IP,
            }
            evidence = _at(
                verified_at,
                verify_azure_performance_infrastructure_safety,
                **arguments,
            )
    _SAFETY_CACHE[cache_key] = evidence
    return evidence


def _infrastructure_safety_evidence(**updates: object):
    coordination_id = str(
        updates.pop(
            "coordination_storage_account_resource_id",
            COORDINATION_RESOURCE_ID,
        )
    )
    evidence = _issue_complete_infrastructure_safety_evidence(
        owner_binding_sha256=str(
            updates.pop("owner_binding_sha256", OWNER_APPROVAL_BODY_SHA256)
        ),
        tenant_id=str(updates.pop("tenant_id", TENANT_ID)),
        bootstrap_principal_id=str(
            updates.pop("bootstrap_principal_id", BOOTSTRAP_TOKEN_SUBJECT)
        ),
        runtime_principal_id=str(
            updates.pop("runtime_principal_id", TOKEN_SUBJECT)
        ),
        target_binding_sha256=str(
            updates.pop("target_binding_sha256", TARGET_SHA256)
        ),
        coordination_id=coordination_id,
        bff_id=str(
            updates.pop("bff_storage_account_resource_id", BFF_RESOURCE_ID)
        ),
        worm_id=str(
            updates.pop("worm_storage_account_resource_id", WORM_RESOURCE_ID)
        ),
        verified_at_utc=str(
            updates.pop("verified_at_utc", "2026-08-03T12:00:00Z")
        ),
    )
    changes: dict[str, object] = {}
    for key in (
        "coordination_storage_account_name",
        "lease_container_resource_id",
        "lease_blob_path",
    ):
        supplied = updates.pop(key, evidence[key])
        if supplied != evidence[key]:
            changes[key] = supplied
    changes.update(updates)
    if not changes:
        return evidence
    tampered = dict(evidence)
    tampered.update(changes)
    tampered.pop("infrastructure_safety_evidence_sha256", None)
    tampered["infrastructure_safety_evidence_sha256"] = (
        _canonical_json_sha256(tampered)
    )
    return tampered


def _acquisition_safety(
    binding: AzureBlobLeaseBinding | None = None,
) -> dict[str, object]:
    selected = binding or _binding()
    coordination_resource_id = selected.coordination_storage_account_resource_id
    resource_prefix = coordination_resource_id.rsplit("/", 1)[0]
    return build_lease_acquisition_safety_evidence(
        binding=selected,
        infrastructure_safety_evidence=_infrastructure_safety_evidence(
            target_binding_sha256=selected.target_binding_sha256,
            coordination_storage_account_name=selected.account_name,
            coordination_storage_account_resource_id=coordination_resource_id,
            bff_storage_account_resource_id=(
                f"{resource_prefix}/{selected.bff_account_name}"
            ),
            worm_storage_account_resource_id=(
                f"{resource_prefix}/{selected.worm_account_name}"
            ),
            lease_container_resource_id=(
                f"{coordination_resource_id}/blobServices/default/containers/"
                "nac-bff-performance-leases"
            ),
            lease_blob_path=f"locks/{selected.target_binding_sha256}.lock",
            runtime_principal_id=selected.token_subject,
        ),
    )


def _success_headers(**updates: str) -> dict[str, str]:
    values = {"ETag": EXPECTED_ETAG, "x-ms-version": API_VERSION}
    values.update(updates)
    return values


def _head_held() -> _Response:
    return _Response(
        200,
        BASE_URL,
        _success_headers(
            **{
                "x-ms-lease-duration": "infinite",
                "x-ms-lease-state": "leased",
                "x-ms-lease-status": "locked",
            }
        ),
    )


def _head_not_present() -> _Response:
    return _Response(
        412,
        BASE_URL,
        {"x-ms-error-code": "LeaseNotPresentWithBlobOperation"},
    )


def _head_released() -> _Response:
    return _Response(
        200,
        BASE_URL,
        _success_headers(
            **{
                "x-ms-lease-state": "available",
                "x-ms-lease-status": "unlocked",
            }
        ),
    )


def _acquired() -> _Response:
    return _Response(
        201,
        LEASE_URL,
        _success_headers(**{"x-ms-lease-id": str(LEASE_ID)}),
    )


def _released() -> _Response:
    return _Response(200, LEASE_URL, _success_headers())


def _request_headers(request: object) -> dict[str, str]:
    return {
        name.lower(): value
        for name, value in getattr(request, "header_items")()
    }


class AzurePerformanceLeaseTests(unittest.TestCase):
    def test_policy_digest_excludes_break_delete_and_reacquire(self) -> None:
        policy = lease_policy()
        self.assertEqual(
            policy["allowed_operations"], ["acquire", "assert_held", "release"]
        )
        self.assertIn("break", policy["forbidden_operations"])
        self.assertIn("delete", policy["forbidden_operations"])
        self.assertEqual(policy["passed_state_requires"], "RELEASED")
        self.assertEqual(len(lease_policy_sha256()), 64)

    def test_bootstrap_policy_is_put_if_absent_and_readback_only(self) -> None:
        policy = lease_bootstrap_policy()
        self.assertEqual(
            policy["allowed_operations"], ["put_blob_if_absent", "head_blob"]
        )
        self.assertEqual(policy["put_precondition"], "If-None-Match:*")
        self.assertIn("overwrite", policy["forbidden_operations"])
        self.assertIn("delete", policy["forbidden_operations"])
        self.assertEqual(
            policy["existing_blob_responses"],
            [
                {"error_code": "BlobAlreadyExists", "status": 409},
                {"error_code": "ConditionNotMet", "status": 412},
            ],
        )
        self.assertEqual(policy["binding_source"], "independent_head_readback")
        self.assertTrue(policy["infrastructure_safety_evidence_required"])
        self.assertEqual(policy["infrastructure_safety_max_age_seconds"], 300)
        self.assertTrue(
            policy[
                "owner_principal_tenant_resource_target_binding_required"
            ]
        )
        self.assertTrue(policy["token_subject_and_tenant_validation_required"])
        self.assertTrue(
            policy["distinct_bootstrap_runtime_identity_bindings_required"]
        )
        self.assertTrue(policy["runtime_binding_handoff_required"])
        self.assertFalse(policy["azure_rbac_write_operation_filtering"])
        self.assertEqual(len(lease_bootstrap_policy_sha256()), 64)

    def test_bootstrap_binding_requires_distinct_bootstrap_and_runtime_identities(
        self,
    ) -> None:
        for field, value in (
            ("runtime_token_subject", BOOTSTRAP_TOKEN_SUBJECT),
            ("runtime_token_subject", "not-a-uuid"),
            ("runtime_read_identity_binding_sha256", "not-a-hash"),
            ("runtime_write_identity_binding_sha256", "not-a-hash"),
            (
                "runtime_read_identity_binding_sha256",
                BOOTSTRAP_READ_IDENTITY_SHA256,
            ),
            (
                "runtime_write_identity_binding_sha256",
                BOOTSTRAP_WRITE_IDENTITY_SHA256,
            ),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(
                    ValueError,
                    r"^AZURE_BLOB_LEASE_BOOTSTRAP_BINDING_INVALID$",
                ):
                    _bootstrap_binding(**{field: value})

    def test_bootstrap_canonical_hash_binds_runtime_identity_handoff(self) -> None:
        binding = _bootstrap_binding()
        digest = calculate_azure_blob_lease_bootstrap_binding_sha256(binding)
        for field, value in (
            ("runtime_token_subject", str(OTHER_LEASE_ID)),
            ("runtime_read_identity_binding_sha256", "6" * 64),
            ("runtime_write_identity_binding_sha256", "7" * 64),
        ):
            with self.subTest(field=field):
                changed = AzureBlobLeaseBootstrapBinding(
                    **{**asdict(binding), field: value}
                )
                self.assertNotEqual(
                    calculate_azure_blob_lease_bootstrap_binding_sha256(changed),
                    digest,
                )

    def test_bootstrap_requires_capability_before_token_or_network(self) -> None:
        provider = _TokenProvider()
        opener = _Opener(_Response(201, BASE_URL, _success_headers()))
        adapter = AzureBlobLeaseBootstrapAdapter(
            binding=_bootstrap_binding(),
            infrastructure_safety_evidence=_infrastructure_safety_evidence(),
            token_provider=provider,
            opener=opener,
            clock=self.clock,
        )

        with self.assertRaisesRegex(
            AzureBlobLeaseError, "AZURE_BLOB_LEASE_LIVE_CAPABILITY_REQUIRED"
        ):
            adapter.bootstrap()

        self.assertEqual(provider.calls, [])
        self.assertEqual(opener.calls, [])

    def test_bootstrap_consumption_failure_precedes_token_and_network(self) -> None:
        provider = _TokenProvider()
        opener = _Opener()
        adapter = AzureBlobLeaseBootstrapAdapter(
            binding=_bootstrap_binding(),
            infrastructure_safety_evidence=_infrastructure_safety_evidence(),
            token_provider=provider,
            opener=opener,
            clock=self.clock,
        )

        def authorize(_capability, *, consume, **_kwargs):
            if consume:
                raise performance_authorization.PerformanceLiveAuthorizationError(
                    "PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED"
                )

        with mock.patch.object(
            performance_lease,
            "_authorize_live_action",
            side_effect=authorize,
        ):
            with self.assertRaisesRegex(
                AzureBlobLeaseError,
                "AZURE_BLOB_LEASE_LIVE_CAPABILITY_EXHAUSTED",
            ):
                adapter.bootstrap(object())  # type: ignore[arg-type]

        self.assertEqual(provider.calls, [])
        self.assertEqual(opener.calls, [])

    def test_bootstrap_rejects_unattested_and_alg_none_token_results(self) -> None:
        for name, provider in (
            ("unattested", lambda **_kwargs: STORAGE_TOKEN),
            ("alg_none", _TokenProvider(_jwt(algorithm="none"))),
            (
                "wrong_source",
                lambda **kwargs: _attested_storage_token(
                    identity_binding_sha256=kwargs["identity_binding_sha256"],
                    source_attestation_sha256="0" * 64,
                ),
            ),
        ):
            with self.subTest(name=name):
                adapter = AzureBlobLeaseBootstrapAdapter(
                    binding=_bootstrap_binding(),
                    infrastructure_safety_evidence=(
                        _infrastructure_safety_evidence()
                    ),
                    token_provider=provider,
                    opener=_Opener(),
                    clock=self.clock,
                )
                with self.assertRaisesRegex(
                    AzureBlobLeaseError,
                    "AZURE_BLOB_LEASE_BOOTSTRAP_TOKEN_INVALID",
                ):
                    adapter.bootstrap(_bootstrap_capability(adapter))

    def test_bootstrap_creates_exact_zero_byte_blob_and_returns_etag_binding(self) -> None:
        opener = _Opener(
            _Response(201, BASE_URL, _success_headers()),
            _Response(
                200,
                BASE_URL,
                _success_headers(
                    **{
                        "Content-Length": "0",
                        "x-ms-blob-type": "BlockBlob",
                    }
                ),
            ),
        )
        provider = _TokenProvider()
        adapter = AzureBlobLeaseBootstrapAdapter(
            binding=_bootstrap_binding(),
            infrastructure_safety_evidence=_infrastructure_safety_evidence(),
            token_provider=provider,
            opener=opener,
            clock=lambda: datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
        )

        result = adapter.bootstrap(_bootstrap_capability(adapter))

        self.assertEqual([call[0].method for call in opener.calls], ["PUT", "HEAD"])
        request, timeout = opener.calls[0]
        headers = _request_headers(request)
        self.assertEqual(getattr(request, "method"), "PUT")
        self.assertEqual(getattr(request, "full_url"), BASE_URL)
        self.assertEqual(getattr(request, "data"), b"")
        self.assertEqual(timeout, 30)
        self.assertEqual(headers["if-none-match"], "*")
        self.assertEqual(headers["x-ms-blob-type"], "BlockBlob")
        self.assertEqual(headers["content-length"], "0")
        self.assertEqual(result.expected_etag, EXPECTED_ETAG)
        self.assertEqual(result.target_binding_sha256, TARGET_SHA256)
        self.assertEqual(result.token_subject, TOKEN_SUBJECT)
        self.assertEqual(
            result.read_identity_binding_sha256, READ_IDENTITY_SHA256
        )
        self.assertEqual(
            result.write_identity_binding_sha256, WRITE_IDENTITY_SHA256
        )
        self.assertEqual(
            provider.calls,
            [
                {
                    "audience": "https://storage.azure.com/.default",
                    "identity_binding_sha256": (
                        BOOTSTRAP_WRITE_IDENTITY_SHA256
                    ),
                },
                {
                    "audience": "https://storage.azure.com/.default",
                    "identity_binding_sha256": (
                        BOOTSTRAP_READ_IDENTITY_SHA256
                    ),
                },
            ],
        )

    def test_bootstrap_exact_existing_responses_are_headed_without_overwrite(self) -> None:
        for status, error_code in (
            (409, "BlobAlreadyExists"),
            (412, "ConditionNotMet"),
        ):
            with self.subTest(status=status, error_code=error_code):
                opener = _Opener(
                    _Response(
                        status,
                        BASE_URL,
                        {"x-ms-error-code": error_code},
                    ),
                    _Response(
                        200,
                        BASE_URL,
                        _success_headers(
                            **{
                                "Content-Length": "0",
                                "x-ms-blob-type": "BlockBlob",
                            }
                        ),
                    ),
                )
                adapter = AzureBlobLeaseBootstrapAdapter(
                    binding=_bootstrap_binding(),
                    infrastructure_safety_evidence=(
                        _infrastructure_safety_evidence()
                    ),
                    token_provider=_TokenProvider(),
                    opener=opener,
                    clock=lambda: datetime(
                        2026, 8, 3, 12, 0, tzinfo=timezone.utc
                    ),
                )

                result = adapter.bootstrap(_bootstrap_capability(adapter))

                self.assertEqual(
                    [call[0].method for call in opener.calls], ["PUT", "HEAD"]
                )
                self.assertEqual(result.expected_etag, EXPECTED_ETAG)

    def test_bootstrap_rejects_mismatched_or_unsafe_conflict_responses(self) -> None:
        for status, error_code in (
            (409, "ConditionNotMet"),
            (412, "BlobAlreadyExists"),
            (409, "LeaseAlreadyPresent"),
            (412, "LeaseIdMissing"),
        ):
            with self.subTest(status=status, error_code=error_code):
                opener = _Opener(
                    _Response(
                        status,
                        BASE_URL,
                        {"x-ms-error-code": error_code},
                    )
                )
                adapter = AzureBlobLeaseBootstrapAdapter(
                    binding=_bootstrap_binding(),
                    infrastructure_safety_evidence=(
                        _infrastructure_safety_evidence()
                    ),
                    token_provider=_TokenProvider(),
                    opener=opener,
                    clock=lambda: datetime(
                        2026, 8, 3, 12, 0, tzinfo=timezone.utc
                    ),
                )

                with self.assertRaisesRegex(
                    AzureBlobLeaseError,
                    r"^AZURE_BLOB_LEASE_BOOTSTRAP_RESPONSE_INVALID$",
                ):
                    adapter.bootstrap(_bootstrap_capability(adapter))
                self.assertEqual(len(opener.calls), 1)

    def test_bootstrap_head_binds_only_strong_etag_block_blob_and_zero_length(self) -> None:
        invalid_readbacks = (
            _Response(
                200,
                BASE_URL,
                _success_headers(
                    **{
                        "Content-Length": "1",
                        "x-ms-blob-type": "BlockBlob",
                    }
                ),
            ),
            _Response(
                200,
                BASE_URL,
                _success_headers(
                    **{
                        "Content-Length": "0",
                        "x-ms-blob-type": "AppendBlob",
                    }
                ),
            ),
            _Response(
                200,
                BASE_URL,
                _success_headers(
                    ETag='W/"weak"',
                    **{
                        "Content-Length": "0",
                        "x-ms-blob-type": "BlockBlob",
                    },
                ),
            ),
        )
        for index, readback in enumerate(invalid_readbacks):
            with self.subTest(index=index):
                adapter = AzureBlobLeaseBootstrapAdapter(
                    binding=_bootstrap_binding(),
                    infrastructure_safety_evidence=(
                        _infrastructure_safety_evidence()
                    ),
                    token_provider=_TokenProvider(),
                    opener=_Opener(
                        _Response(201, BASE_URL, _success_headers()),
                        readback,
                    ),
                    clock=lambda: datetime(
                        2026, 8, 3, 12, 0, tzinfo=timezone.utc
                    ),
                )
                with self.assertRaises(AzureBlobLeaseError):
                    adapter.bootstrap(_bootstrap_capability(adapter))

    def test_bootstrap_rejects_etag_change_between_create_and_head(self) -> None:
        adapter = AzureBlobLeaseBootstrapAdapter(
            binding=_bootstrap_binding(),
            infrastructure_safety_evidence=_infrastructure_safety_evidence(),
            token_provider=_TokenProvider(),
            opener=_Opener(
                _Response(201, BASE_URL, _success_headers()),
                _Response(
                    200,
                    BASE_URL,
                    _success_headers(
                        ETag='"changed"',
                        **{
                            "Content-Length": "0",
                            "x-ms-blob-type": "BlockBlob",
                        },
                    ),
                ),
            ),
            clock=lambda: datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
        )

        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_BOOTSTRAP_DRIFT$"
        ):
            adapter.bootstrap(_bootstrap_capability(adapter))

    def test_bootstrap_cross_binds_owner_infrastructure_before_http(self) -> None:
        for field, value in (
            ("owner_binding_sha256", "0" * 64),
            ("bootstrap_principal_id", str(OTHER_LEASE_ID)),
            ("runtime_principal_id", str(OTHER_LEASE_ID)),
            ("tenant_id", str(OTHER_LEASE_ID)),
            (
                "coordination_storage_account_resource_id",
                COORDINATION_RESOURCE_ID.replace(
                    "nacperflease001", "otherleaseaccount01"
                ),
            ),
            ("target_binding_sha256", "0" * 64),
        ):
            with self.subTest(field=field):
                opener = _Opener()
                with self.assertRaisesRegex(
                    AzureBlobLeaseError,
                    r"^AZURE_BLOB_LEASE_BOOTSTRAP_SAFETY_INVALID$",
                ):
                    AzureBlobLeaseBootstrapAdapter(
                        binding=_bootstrap_binding(),
                        infrastructure_safety_evidence=(
                            _infrastructure_safety_evidence(**{field: value})
                        ),
                        token_provider=_TokenProvider(),
                        opener=opener,
                        clock=lambda: datetime(
                            2026, 8, 3, 12, 0, tzinfo=timezone.utc
                        ),
                    )
                self.assertEqual(opener.calls, [])

    def test_acquisition_safety_binds_runtime_not_bootstrap_principal(self) -> None:
        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_ACQUISITION_SAFETY_INVALID$",
        ):
            build_lease_acquisition_safety_evidence(
                binding=_binding(token_subject=BOOTSTRAP_TOKEN_SUBJECT),
                infrastructure_safety_evidence=(
                    _infrastructure_safety_evidence()
                ),
            )

    def test_bootstrap_rejects_wrong_token_subject_before_http(self) -> None:
        opener = _Opener()
        adapter = AzureBlobLeaseBootstrapAdapter(
            binding=_bootstrap_binding(),
            infrastructure_safety_evidence=_infrastructure_safety_evidence(),
            token_provider=_TokenProvider(_jwt(oid=str(OTHER_LEASE_ID))),
            opener=opener,
            clock=lambda: datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
        )

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_BOOTSTRAP_TOKEN_SUBJECT_MISMATCH$",
        ):
            adapter.bootstrap(_bootstrap_capability(adapter))

        self.assertEqual(opener.calls, [])

    def test_bootstrap_rejects_wrong_token_tenant_before_http(self) -> None:
        opener = _Opener()
        adapter = AzureBlobLeaseBootstrapAdapter(
            binding=_bootstrap_binding(),
            infrastructure_safety_evidence=_infrastructure_safety_evidence(),
            token_provider=_TokenProvider(
                _jwt(
                    oid=BOOTSTRAP_TOKEN_SUBJECT,
                    tid=str(OTHER_LEASE_ID),
                )
            ),
            opener=opener,
            clock=lambda: datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
        )

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_BOOTSTRAP_TOKEN_TENANT_MISMATCH$",
        ):
            adapter.bootstrap(_bootstrap_capability(adapter))

        self.assertEqual(opener.calls, [])

    def test_bootstrap_rejects_invalid_audience_and_lifetime_before_http(
        self,
    ) -> None:
        invalid_tokens = {
            "wrong_audience": _jwt(aud="https://storage.azure.com/"),
            "audience_list": _jwt(aud=["https://storage.azure.com"]),
            "expired": _jwt(exp=FIXED_NOW_TIMESTAMP),
            "not_yet_valid": _jwt(nbf=FIXED_NOW_TIMESTAMP + 1),
            "missing_exp": _jwt(omit=("exp",)),
            "missing_nbf": _jwt(omit=("nbf",)),
            "malformed_exp": _jwt(exp="never"),
            "malformed_nbf": _jwt(nbf=True),
        }
        for name, token in invalid_tokens.items():
            with self.subTest(name=name):
                opener = _Opener()
                adapter = AzureBlobLeaseBootstrapAdapter(
                    binding=_bootstrap_binding(),
                    infrastructure_safety_evidence=(
                        _infrastructure_safety_evidence()
                    ),
                    token_provider=_TokenProvider(token),
                    opener=opener,
                    clock=lambda: FIXED_NOW,
                )

                with self.assertRaisesRegex(
                    AzureBlobLeaseError,
                    r"^AZURE_BLOB_LEASE_BOOTSTRAP_TOKEN_INVALID$",
                ):
                    adapter.bootstrap(_bootstrap_capability(adapter))

                self.assertEqual(opener.calls, [])

    def test_bootstrap_rejects_stale_safety_before_http(self) -> None:
        opener = _Opener()
        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_BOOTSTRAP_SAFETY_INVALID$",
        ):
            AzureBlobLeaseBootstrapAdapter(
                binding=_bootstrap_binding(),
                infrastructure_safety_evidence=_infrastructure_safety_evidence(
                    verified_at_utc="2026-08-03T11:54:59Z"
                ),
                token_provider=_TokenProvider(),
                opener=opener,
                clock=lambda: datetime(
                    2026, 8, 3, 12, 0, tzinfo=timezone.utc
                ),
            )

        self.assertEqual(opener.calls, [])

    def test_bootstrap_rechecks_safety_after_delayed_token_provider(self) -> None:
        opener = _Opener()
        current = [datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)]

        def delayed_token(**kwargs: str):
            current[0] = datetime(
                2026, 8, 3, 12, 5, 1, tzinfo=timezone.utc
            )
            return _attested_storage_token(
                identity_binding_sha256=kwargs["identity_binding_sha256"]
            )

        adapter = AzureBlobLeaseBootstrapAdapter(
            binding=_bootstrap_binding(),
            infrastructure_safety_evidence=_infrastructure_safety_evidence(),
            token_provider=delayed_token,
            opener=opener,
            clock=lambda: current[0],
        )

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_INFRASTRUCTURE_SAFETY_STALE$",
        ):
            adapter.bootstrap(_bootstrap_capability(adapter))

        self.assertEqual(opener.calls, [])

    def test_bootstrap_rechecks_safety_immediately_before_mutating_put(self) -> None:
        opener = _Opener()
        fresh = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
        stale = datetime(2026, 8, 3, 12, 5, 1, tzinfo=timezone.utc)
        times = iter((fresh, fresh, stale))
        adapter = AzureBlobLeaseBootstrapAdapter(
            binding=_bootstrap_binding(),
            infrastructure_safety_evidence=_infrastructure_safety_evidence(),
            token_provider=_TokenProvider(),
            opener=opener,
            clock=lambda: next(times),
        )

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_INFRASTRUCTURE_SAFETY_STALE$",
        ):
            adapter.bootstrap(_bootstrap_capability(adapter))

        self.assertEqual(opener.calls, [])

    def test_bootstrap_rejects_missing_safety_before_http(self) -> None:
        opener = _Opener()

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_BOOTSTRAP_SAFETY_INVALID$",
        ):
            AzureBlobLeaseBootstrapAdapter(
                binding=_bootstrap_binding(),
                infrastructure_safety_evidence=None,  # type: ignore[arg-type]
                token_provider=_TokenProvider(),
                opener=opener,
                clock=lambda: datetime(
                    2026, 8, 3, 12, 0, tzinfo=timezone.utc
                ),
            )

        self.assertEqual(opener.calls, [])

    def setUp(self) -> None:
        trusted_now = mock.patch.object(
            infrastructure_safety,
            "_trusted_now",
            return_value=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
        )
        trusted_now.start()
        self.addCleanup(trusted_now.stop)
        bound_runtime = mock.patch.object(
            infrastructure_safety,
            "_prepare_bound_runtime",
            side_effect=_prepare_test_runtime,
        )
        bound_runtime.start()
        self.addCleanup(bound_runtime.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state_path = Path(self.temporary.name) / "lease-state.json"
        self.clock = lambda: datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)

    def adapter(
        self,
        opener: _Opener,
        *,
        token_provider: object | None = None,
        binding: AzureBlobLeaseBinding | None = None,
        state_path: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> tuple[AzureBlobLeaseAdapter, object]:
        provider = token_provider or _TokenProvider()
        selected_binding = binding or _binding()
        adapter = AzureBlobLeaseAdapter(
                binding=selected_binding,
                acquisition_safety_evidence=_acquisition_safety(selected_binding),
                state_path=state_path or self.state_path,
                token_provider=provider,
                opener=opener,
                clock=clock or self.clock,
            )
        adapter._test_live_action_capability = _lease_capability(adapter)
        return adapter, provider

    def acquire_held(self) -> None:
        adapter, _ = self.adapter(_Opener(_acquired()))
        adapter.acquire(LEASE_ID)

    def state_payload(self) -> dict[str, object]:
        document = json.loads(self.state_path.read_text(encoding="ascii"))
        return document["payload"]

    def test_binding_is_fixed_to_dedicated_account_and_safe_values(self) -> None:
        binding = _binding()
        self.assertEqual(binding.api_version, API_VERSION)
        self.assertEqual(binding.container_name, "nac-bff-performance-leases")
        self.assertEqual(binding.token_audience, "https://storage.azure.com/.default")
        token = _attested_storage_token()
        with self.assertRaises(AttributeError):
            token.scope = "https://example.invalid/.default"

    def test_lease_requires_capability_before_state_token_or_network(self) -> None:
        provider = _TokenProvider()
        opener = _Opener(_acquired())
        adapter = AzureBlobLeaseAdapter(
            binding=_binding(),
            acquisition_safety_evidence=_acquisition_safety(_binding()),
            state_path=self.state_path,
            token_provider=provider,
            opener=opener,
            clock=self.clock,
        )

        with self.assertRaisesRegex(
            AzureBlobLeaseError, "AZURE_BLOB_LEASE_LIVE_CAPABILITY_REQUIRED"
        ):
            adapter.acquire(LEASE_ID)

        self.assertFalse(self.state_path.exists())
        self.assertEqual(provider.calls, [])
        self.assertEqual(opener.calls, [])

    def test_acquire_consumption_failure_precedes_token_state_and_network(self) -> None:
        provider = _TokenProvider()
        opener = _Opener()
        adapter = AzureBlobLeaseAdapter(
            binding=_binding(),
            acquisition_safety_evidence=_acquisition_safety(_binding()),
            state_path=self.state_path,
            token_provider=provider,
            opener=opener,
            clock=self.clock,
        )

        def authorize(_capability, *, consume, **_kwargs):
            if consume:
                raise performance_authorization.PerformanceLiveAuthorizationError(
                    "PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED"
                )

        with mock.patch.object(
            performance_lease,
            "_authorize_live_action",
            side_effect=authorize,
        ):
            with self.assertRaisesRegex(
                AzureBlobLeaseError,
                "AZURE_BLOB_LEASE_LIVE_CAPABILITY_EXHAUSTED",
            ):
                adapter.acquire(LEASE_ID, object())  # type: ignore[arg-type]

        self.assertEqual(provider.calls, [])
        self.assertFalse(self.state_path.exists())
        self.assertEqual(opener.calls, [])

    def test_acquire_rejects_unattested_and_alg_none_token_results(self) -> None:
        for name, provider in (
            ("unattested", lambda **_kwargs: STORAGE_TOKEN),
            ("alg_none", _TokenProvider(_jwt(algorithm="none"))),
            (
                "wrong_source",
                lambda **kwargs: _attested_storage_token(
                    identity_binding_sha256=kwargs["identity_binding_sha256"],
                    source_attestation_sha256="0" * 64,
                ),
            ),
        ):
            with self.subTest(name=name):
                state_path = Path(self.temporary.name) / f"{name}.json"
                adapter, _ = self.adapter(
                    _Opener(),
                    token_provider=provider,
                    state_path=state_path,
                )
                with self.assertRaisesRegex(
                    AzureBlobLeaseError,
                    "AZURE_BLOB_LEASE_TOKEN_INVALID",
                ):
                    adapter.acquire(LEASE_ID)
                self.assertFalse(state_path.exists())

    def test_lease_rejects_wrong_action_target_binding_and_replay(self) -> None:
        opener = _Opener(_acquired())
        adapter, provider = self.adapter(opener)
        adapter._test_live_action_capability = None
        wrong_capabilities = (
            _issue_test_live_action_capability(
                target_binding_sha256=adapter.target_binding_sha256,
                action_bindings={
                    BLOB_BOOTSTRAP: (adapter.lease_binding_sha256, 1)
                },
            ),
            _issue_test_live_action_capability(
                target_binding_sha256="0" * 64,
                action_bindings={
                    BLOB_LEASE_ACQUIRE: (adapter.lease_binding_sha256, 1)
                },
            ),
            _issue_test_live_action_capability(
                target_binding_sha256=adapter.target_binding_sha256,
                action_bindings={BLOB_LEASE_ACQUIRE: ("0" * 64, 1)},
            ),
        )

        for capability in wrong_capabilities:
            with self.assertRaisesRegex(
                AzureBlobLeaseError,
                "AZURE_BLOB_LEASE_LIVE_CAPABILITY_BINDING_MISMATCH",
            ):
                adapter.acquire(LEASE_ID, capability)
        self.assertFalse(self.state_path.exists())
        self.assertEqual(provider.calls, [])
        self.assertEqual(opener.calls, [])

        one_use = _lease_capability(adapter, uses=1)
        self.assertEqual(adapter.acquire(LEASE_ID, one_use).lifecycle_state, "HELD")
        with self.assertRaisesRegex(
            AzureBlobLeaseError, "AZURE_BLOB_LEASE_LIVE_CAPABILITY_EXHAUSTED"
        ):
            adapter.acquire(LEASE_ID, one_use)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(len(opener.calls), 1)

    def test_state_path_rejects_symlink_in_any_ancestor(self) -> None:
        root = Path(self.temporary.name)
        external = root / "external"
        external.mkdir(mode=0o700)
        linked = root / "linked"
        linked.symlink_to(external, target_is_directory=True)
        opener = _Opener(_acquired())
        provider = _TokenProvider()

        with self.assertRaisesRegex(
            AzureBlobLeaseError, "AZURE_BLOB_LEASE_STATE_INVALID"
        ):
            AzureBlobLeaseAdapter(
                binding=_binding(),
                acquisition_safety_evidence=_acquisition_safety(_binding()),
                state_path=linked / "nested" / "lease-state.json",
                token_provider=provider,
                opener=opener,
                clock=self.clock,
            )

        self.assertEqual(provider.calls, [])
        self.assertEqual(opener.calls, [])
        self.assertEqual(list(external.iterdir()), [])

        for field, value in (
            ("account_name", "nacbffdeploy001"),
            ("account_name", "nacwormevidence001"),
            ("account_name", "Bad-Account"),
            ("target_binding_sha256", "not-a-hash"),
            ("read_identity_binding_sha256", "not-a-hash"),
            ("write_identity_binding_sha256", "not-a-hash"),
            (
                "coordination_storage_account_resource_id",
                COORDINATION_RESOURCE_ID.replace(
                    "nacperflease001", "otherleaseaccount01"
                ),
            ),
            ("token_subject", "not-a-uuid"),
            ("expected_etag", "*"),
            ("expected_etag", 'W/"weak"'),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(
                    ValueError, r"^AZURE_BLOB_LEASE_BINDING_INVALID$"
                ):
                    _binding(**{field: value})

    def test_acquisition_safety_cross_binds_runtime_lease_before_network(self) -> None:
        for field, value in (
            ("owner_approval_body_sha256", "0" * 64),
            ("lease_binding_sha256", "0" * 64),
            (
                "coordination_storage_account_resource_id",
                COORDINATION_RESOURCE_ID.replace(
                    "nacperflease001", "otherleaseaccount01"
                ),
            ),
            ("expected_etag", '"changed"'),
            ("token_subject", str(OTHER_LEASE_ID)),
            ("token_tenant_id", str(OTHER_LEASE_ID)),
        ):
            with self.subTest(field=field):
                evidence = _acquisition_safety()
                evidence[field] = value
                evidence.pop("lease_acquisition_safety_evidence_sha256")
                evidence["lease_acquisition_safety_evidence_sha256"] = (
                    hashlib.sha256(
                        json.dumps(
                            evidence,
                            allow_nan=False,
                            ensure_ascii=True,
                            separators=(",", ":"),
                            sort_keys=True,
                        ).encode("ascii")
                    ).hexdigest()
                )
                opener = _Opener()
                with self.assertRaisesRegex(
                    AzureBlobLeaseError,
                    r"^AZURE_BLOB_LEASE_ACQUISITION_SAFETY_INVALID$",
                ):
                    AzureBlobLeaseAdapter(
                        binding=_binding(),
                        acquisition_safety_evidence=evidence,
                        state_path=self.state_path,
                        token_provider=_TokenProvider(),
                        opener=opener,
                        clock=self.clock,
                    )
                self.assertEqual(opener.calls, [])

    def test_acquire_rejects_token_subject_before_state_or_http(self) -> None:
        opener = _Opener()
        provider = _TokenProvider(_jwt(oid=str(OTHER_LEASE_ID)))
        adapter, _ = self.adapter(opener, token_provider=provider)

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_TOKEN_SUBJECT_MISMATCH$",
        ):
            adapter.acquire(LEASE_ID)

        self.assertEqual(opener.calls, [])
        self.assertFalse(self.state_path.exists())

    def test_acquire_rejects_token_tenant_before_state_or_http(self) -> None:
        opener = _Opener()
        provider = _TokenProvider(_jwt(tid=str(OTHER_LEASE_ID)))
        adapter, _ = self.adapter(opener, token_provider=provider)

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_TOKEN_TENANT_MISMATCH$",
        ):
            adapter.acquire(LEASE_ID)

        self.assertEqual(opener.calls, [])
        self.assertFalse(self.state_path.exists())

    def test_acquire_rejects_invalid_audience_and_lifetime_before_state_or_http(
        self,
    ) -> None:
        invalid_tokens = {
            "wrong_audience": _jwt(aud="https://storage.azure.com/"),
            "audience_list": _jwt(aud=["https://storage.azure.com"]),
            "expired": _jwt(exp=FIXED_NOW_TIMESTAMP),
            "not_yet_valid": _jwt(nbf=FIXED_NOW_TIMESTAMP + 1),
            "missing_exp": _jwt(omit=("exp",)),
            "missing_nbf": _jwt(omit=("nbf",)),
            "malformed_exp": _jwt(exp="never"),
            "malformed_nbf": _jwt(nbf=True),
        }
        for name, token in invalid_tokens.items():
            with self.subTest(name=name):
                state_path = Path(self.temporary.name) / f"{name}.json"
                opener = _Opener()
                adapter, _ = self.adapter(
                    opener,
                    token_provider=_TokenProvider(token),
                    state_path=state_path,
                )

                with self.assertRaisesRegex(
                    AzureBlobLeaseError,
                    r"^AZURE_BLOB_LEASE_TOKEN_INVALID$",
                ):
                    adapter.acquire(LEASE_ID)

                self.assertEqual(opener.calls, [])
                self.assertFalse(state_path.exists())

    def test_acquire_rejects_stale_safety_before_state_or_http(self) -> None:
        opener = _Opener()
        binding = _binding()
        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_ACQUISITION_SAFETY_INVALID$",
        ):
            build_lease_acquisition_safety_evidence(
                binding=binding,
                infrastructure_safety_evidence=_infrastructure_safety_evidence(
                    verified_at_utc="2026-08-03T11:54:59Z"
                ),
            )

        self.assertEqual(opener.calls, [])
        self.assertFalse(self.state_path.exists())

    def test_acquire_rechecks_safety_after_delayed_token_provider(self) -> None:
        opener = _Opener()
        current = [datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)]

        def delayed_token(**kwargs: str):
            current[0] = datetime(
                2026, 8, 3, 12, 5, 1, tzinfo=timezone.utc
            )
            return _attested_storage_token(
                identity_binding_sha256=kwargs["identity_binding_sha256"]
            )

        adapter, _ = self.adapter(
            opener,
            token_provider=delayed_token,
            clock=lambda: current[0],
        )

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_INFRASTRUCTURE_SAFETY_STALE$",
        ):
            adapter.acquire(LEASE_ID)

        self.assertEqual(opener.calls, [])
        self.assertFalse(self.state_path.exists())

    def test_acquire_rechecks_safety_immediately_before_mutating_put(self) -> None:
        opener = _Opener()
        fresh = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
        stale = datetime(2026, 8, 3, 12, 5, 1, tzinfo=timezone.utc)
        times = iter((fresh, fresh, fresh, fresh, stale))
        adapter, _ = self.adapter(opener, clock=lambda: next(times))

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_INFRASTRUCTURE_SAFETY_STALE$",
        ):
            adapter.acquire(LEASE_ID)

        self.assertEqual(opener.calls, [])
        self.assertEqual(
            self.state_payload()["lifecycle_state"], "ACQUIRE_IN_FLIGHT"
        )

    def test_release_allows_acquisition_safety_to_age_after_lease_is_held(self) -> None:
        self.acquire_held()
        opener = _Opener(_released(), _head_released())
        current = [datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)]

        def delayed_token(**kwargs: str):
            current[0] = datetime(
                2026, 8, 3, 12, 5, 1, tzinfo=timezone.utc
            )
            return _attested_storage_token(
                identity_binding_sha256=kwargs["identity_binding_sha256"]
            )

        adapter, _ = self.adapter(
            opener,
            token_provider=delayed_token,
            clock=lambda: current[0],
        )

        receipt = adapter.release(LEASE_ID)

        self.assertEqual(receipt.lifecycle_state, "RELEASED")
        self.assertEqual(len(opener.calls), 2)
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")

    def test_assert_and_release_work_after_multi_hour_measurement(self) -> None:
        self.acquire_held()
        opener = _Opener(_head_held(), _released(), _head_released())
        adapter, _ = self.adapter(
            opener,
            clock=lambda: datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(adapter.assert_held(LEASE_ID).lifecycle_state, "HELD")
        self.assertEqual(adapter.release(LEASE_ID).lifecycle_state, "RELEASED")

        self.assertEqual(len(opener.calls), 3)
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")

    def test_acquire_rejects_missing_safety_before_http(self) -> None:
        opener = _Opener()

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_ACQUISITION_SAFETY_INVALID$",
        ):
            AzureBlobLeaseAdapter(
                binding=_binding(),
                acquisition_safety_evidence=None,  # type: ignore[arg-type]
                state_path=self.state_path,
                token_provider=_TokenProvider(),
                opener=opener,
                clock=self.clock,
            )

        self.assertEqual(opener.calls, [])

    def test_execution_fence_rejects_a_second_process_lifecycle(self) -> None:
        first, _ = self.adapter(_Opener())
        second, _ = self.adapter(_Opener())

        with first.execution_fence():
            with self.assertRaisesRegex(
                AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_CONCURRENT_RUN$"
            ):
                with second.execution_fence():
                    self.fail("concurrent lifecycle entered the process fence")

        with second.execution_fence():
            pass

        run_lock_path = self.state_path.with_name(
            f".{self.state_path.name}.run.lock"
        )
        self.assertEqual(run_lock_path.stat().st_mode & 0o777, 0o600)

    def test_execution_fence_rejects_lock_held_by_real_subprocess(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(
                None,
                (
                    str(repo_root / "src"),
                    str(repo_root),
                    environment.get("PYTHONPATH", ""),
                ),
            )
        )
        script = textwrap.dedent(
            """
            import sys
            from pathlib import Path
            from nac_bff.azure_performance_lease import _PrivateLifecycleStore

            store = _PrivateLifecycleStore(Path(sys.argv[1]))
            with store.run_locked():
                print("LOCKED", flush=True)
                sys.stdin.read(1)
            """
        )
        process = subprocess.Popen(
            [sys.executable, "-c", script, str(self.state_path)],
            cwd=repo_root,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdout is not None
        ready = process.stdout.readline().strip()
        try:
            if ready != "LOCKED":
                _, stderr = process.communicate(timeout=5)
                self.fail(f"subprocess did not acquire lock: {stderr}")
            adapter, _ = self.adapter(_Opener())
            with self.assertRaisesRegex(
                AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_CONCURRENT_RUN$"
            ):
                with adapter.execution_fence():
                    self.fail("subprocess execution fence was not enforced")
        finally:
            if process.poll() is None:
                process.communicate("x", timeout=5)
        self.assertEqual(process.returncode, 0)

    def test_acquire_is_exact_conditional_put_and_persists_held(self) -> None:
        opener = _Opener(_acquired())
        adapter, provider = self.adapter(opener)

        receipt = adapter.acquire(LEASE_ID)

        self.assertEqual(len(opener.calls), 1)
        request, timeout = opener.calls[0]
        self.assertEqual(getattr(request, "method"), "PUT")
        self.assertEqual(getattr(request, "full_url"), LEASE_URL)
        self.assertEqual(getattr(request, "data"), b"")
        self.assertEqual(timeout, 30)
        self.assertEqual(
            _request_headers(request),
            {
                "authorization": f"Bearer {STORAGE_TOKEN}",
                "content-length": "0",
                "if-match": EXPECTED_ETAG,
                "x-ms-client-request-id": str(LEASE_ID),
                "x-ms-date": FIXED_DATE,
                "x-ms-lease-action": "acquire",
                "x-ms-lease-duration": "-1",
                "x-ms-proposed-lease-id": str(LEASE_ID),
                "x-ms-version": API_VERSION,
            },
        )
        self.assertEqual(
            getattr(provider, "calls"),
            [
                {
                    "audience": "https://storage.azure.com/.default",
                    "identity_binding_sha256": WRITE_IDENTITY_SHA256,
                }
            ],
        )
        self.assertEqual(self.state_payload()["lifecycle_state"], "HELD")
        self.assertEqual(self.state_path.stat().st_mode & 0o777, 0o600)
        lock_path = self.state_path.with_name(f".{self.state_path.name}.lock")
        self.assertEqual(lock_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(set(asdict(receipt)), {
            "lease_binding_sha256",
            "target_binding_sha256",
            "lease_id_sha256",
            "read_identity_binding_sha256",
            "write_identity_binding_sha256",
            "lifecycle_state",
            "lifecycle_state_sha256",
        })
        self.assertEqual(receipt.lifecycle_state, "HELD")
        self.assertTrue(
            all(
                SHA256_RE.fullmatch(value)
                for key, value in asdict(receipt).items()
                if key.endswith("sha256")
            )
        )
        serialized = json.dumps(asdict(receipt), sort_keys=True)
        for secret in (
            str(LEASE_ID),
            "nacperflease001",
            EXPECTED_ETAG,
            STORAGE_TOKEN,
        ):
            self.assertNotIn(secret, serialized)

    def test_assert_held_is_exact_conditional_head_with_read_identity(self) -> None:
        self.acquire_held()
        opener = _Opener(_head_held())
        adapter, provider = self.adapter(opener)

        receipt = adapter.assert_held(LEASE_ID)

        self.assertEqual(len(opener.calls), 1)
        request, timeout = opener.calls[0]
        self.assertEqual(getattr(request, "method"), "HEAD")
        self.assertEqual(getattr(request, "full_url"), BASE_URL)
        self.assertIsNone(getattr(request, "data"))
        self.assertEqual(timeout, 30)
        self.assertEqual(
            _request_headers(request),
            {
                "authorization": f"Bearer {STORAGE_TOKEN}",
                "if-match": EXPECTED_ETAG,
                "x-ms-client-request-id": str(LEASE_ID),
                "x-ms-date": FIXED_DATE,
                "x-ms-lease-id": str(LEASE_ID),
                "x-ms-version": API_VERSION,
            },
        )
        self.assertEqual(
            getattr(provider, "calls"),
            [
                {
                    "audience": "https://storage.azure.com/.default",
                    "identity_binding_sha256": READ_IDENTITY_SHA256,
                }
            ],
        )
        self.assertEqual(receipt.target_binding_sha256, TARGET_SHA256)
        self.assertEqual(receipt.lifecycle_state, "HELD")

    def test_release_is_exact_put_then_conditional_head_and_durable(self) -> None:
        self.acquire_held()
        opener = _Opener(_released(), _head_released(), _head_released())
        adapter, provider = self.adapter(opener)

        receipt = adapter.release(LEASE_ID)

        self.assertEqual(len(opener.calls), 2)
        release_request = opener.calls[0][0]
        self.assertEqual(getattr(release_request, "method"), "PUT")
        self.assertEqual(getattr(release_request, "full_url"), LEASE_URL)
        self.assertEqual(
            _request_headers(release_request),
            {
                "authorization": f"Bearer {STORAGE_TOKEN}",
                "content-length": "0",
                "if-match": EXPECTED_ETAG,
                "x-ms-client-request-id": str(LEASE_ID),
                "x-ms-date": FIXED_DATE,
                "x-ms-lease-action": "release",
                "x-ms-lease-id": str(LEASE_ID),
                "x-ms-version": API_VERSION,
            },
        )
        head_request = opener.calls[1][0]
        self.assertEqual(getattr(head_request, "method"), "HEAD")
        self.assertEqual(getattr(head_request, "full_url"), BASE_URL)
        self.assertEqual(
            _request_headers(head_request),
            {
                "authorization": f"Bearer {STORAGE_TOKEN}",
                "if-match": EXPECTED_ETAG,
                "x-ms-client-request-id": str(LEASE_ID),
                "x-ms-date": FIXED_DATE,
                "x-ms-version": API_VERSION,
            },
        )
        self.assertEqual(
            [call["identity_binding_sha256"] for call in getattr(provider, "calls")],
            [WRITE_IDENTITY_SHA256, READ_IDENTITY_SHA256],
        )
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")
        self.assertEqual(receipt.lifecycle_state, "RELEASED")
        self.assertTrue(
            all(
                SHA256_RE.fullmatch(value)
                for key, value in asdict(receipt).items()
                if key.endswith("sha256")
            )
        )

        adapter.release(LEASE_ID)
        self.assertEqual(len(opener.calls), 3)
        self.assertEqual(getattr(opener.calls[2][0], "method"), "HEAD")

    def test_crash_after_remote_acquire_resumes_by_head_without_reacquire(self) -> None:
        def acquired_then_crash(_: object) -> object:
            raise OSError("remote acquired; process lost response")

        first, _ = self.adapter(_Opener(acquired_then_crash))
        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_TRANSPORT_UNAVAILABLE$",
        ):
            first.acquire(LEASE_ID)
        self.assertEqual(
            self.state_payload()["lifecycle_state"], "ACQUIRE_IN_FLIGHT"
        )

        opener = _Opener(_head_held())
        resumed, _ = self.adapter(opener)
        resumed.acquire(LEASE_ID)
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(getattr(opener.calls[0][0], "method"), "HEAD")
        self.assertEqual(self.state_payload()["lifecycle_state"], "HELD")

    def test_real_process_restart_uses_fresh_safety_to_reconcile_same_lease(self) -> None:
        first, _ = self.adapter(_Opener(OSError("acquire response lost")))
        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_TRANSPORT_UNAVAILABLE$",
        ):
            first.acquire(LEASE_ID)
        self.assertEqual(
            self.state_payload()["lifecycle_state"], "ACQUIRE_IN_FLIGHT"
        )

        repo_root = Path(__file__).resolve().parents[1]
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(
                None,
                (
                    str(repo_root / "src"),
                    str(repo_root),
                    environment.get("PYTHONPATH", ""),
                ),
            )
        )
        script = textwrap.dedent(
            """
            import json
            import sys
            from datetime import datetime, timezone
            from pathlib import Path
            from unittest import mock

            from nac_bff.azure_performance_lease import (
                AzureBlobLeaseAdapter,
                AzureBlobLeaseError,
                build_lease_acquisition_safety_evidence,
            )
            from tests import test_nac_bff_azure_performance_lease as fixture

            now = datetime(2026, 8, 3, 12, 6, tzinfo=timezone.utc)
            binding = fixture._binding()
            with (
                mock.patch.object(
                    fixture.infrastructure_safety, "_trusted_now", return_value=now
                ),
                mock.patch.object(
                    fixture.infrastructure_safety,
                    "_prepare_bound_runtime",
                    side_effect=fixture._prepare_test_runtime,
                ),
            ):
                try:
                    build_lease_acquisition_safety_evidence(
                        binding=binding,
                        infrastructure_safety_evidence=(
                            fixture._infrastructure_safety_evidence(
                                verified_at_utc="2026-08-03T12:00:00Z"
                            )
                        ),
                    )
                except AzureBlobLeaseError as error:
                    stale_error = str(error)
                else:
                    stale_error = None
                fresh_safety = build_lease_acquisition_safety_evidence(
                    binding=binding,
                    infrastructure_safety_evidence=(
                        fixture._infrastructure_safety_evidence(
                            verified_at_utc="2026-08-03T12:06:00Z"
                        )
                    ),
                )
                opener = fixture._Opener(fixture._head_held())
                adapter = AzureBlobLeaseAdapter(
                    binding=binding,
                    acquisition_safety_evidence=fresh_safety,
                    state_path=Path(sys.argv[1]),
                    token_provider=fixture._TokenProvider(),
                    opener=opener,
                    clock=lambda: now,
                )
                adapter._test_live_action_capability = fixture._lease_capability(
                    adapter
                )
                receipt = adapter.acquire(fixture.LEASE_ID)
            print(json.dumps({
                "lifecycle": receipt.lifecycle_state,
                "method": opener.calls[0][0].method,
                "network_calls": len(opener.calls),
                "stable_bindings": (
                    fresh_safety["owner_approval_body_sha256"]
                    == binding.owner_approval_body_sha256
                    and fresh_safety["token_subject"] == binding.token_subject
                    and fresh_safety["token_tenant_id"] == binding.token_tenant_id
                    and fresh_safety["target_binding_sha256"]
                    == binding.target_binding_sha256
                ),
                "stale_error": stale_error,
            }, sort_keys=True))
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", script, str(self.state_path)],
            cwd=repo_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "lifecycle": "HELD",
                "method": "HEAD",
                "network_calls": 1,
                "stable_bindings": True,
                "stale_error": "AZURE_BLOB_LEASE_ACQUISITION_SAFETY_INVALID",
            },
        )
        self.assertEqual(self.state_payload()["lifecycle_state"], "HELD")

    def test_acquire_in_flight_never_reacquires_when_same_id_is_not_held(self) -> None:
        first, _ = self.adapter(_Opener(OSError("uncertain")))
        with self.assertRaises(AzureBlobLeaseError):
            first.acquire(LEASE_ID)

        opener = _Opener(_head_not_present())
        resumed, _ = self.adapter(opener)
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_NOT_HELD$"
        ):
            resumed.acquire(LEASE_ID)
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(getattr(opener.calls[0][0], "method"), "HEAD")

    def test_resume_requires_same_lease_id_before_network(self) -> None:
        self.acquire_held()
        opener = _Opener()
        adapter, _ = self.adapter(opener)
        for operation in (adapter.acquire, adapter.assert_held, adapter.release):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(
                    AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_ID_MISMATCH$"
                ):
                    operation(OTHER_LEASE_ID)
        self.assertEqual(opener.calls, [])

    def test_uncertain_release_that_is_already_absent_persists_released(self) -> None:
        self.acquire_held()
        first, _ = self.adapter(_Opener(OSError("release response lost")))
        with self.assertRaises(AzureBlobLeaseError):
            first.release(LEASE_ID)
        self.assertEqual(
            self.state_payload()["lifecycle_state"], "RELEASE_INTENT"
        )

        opener = _Opener(_head_not_present(), _head_released())
        resumed, _ = self.adapter(opener)
        resumed.release(LEASE_ID)
        self.assertEqual(len(opener.calls), 2)
        self.assertEqual(getattr(opener.calls[0][0], "method"), "HEAD")
        self.assertEqual(getattr(opener.calls[1][0], "method"), "HEAD")
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")

    def test_uncertain_release_allows_one_reconciled_same_id_release(self) -> None:
        self.acquire_held()
        first, _ = self.adapter(_Opener(OSError("first release uncertain")))
        with self.assertRaises(AzureBlobLeaseError):
            first.release(LEASE_ID)

        opener = _Opener(_head_held(), _released(), _head_released())
        resumed, _ = self.adapter(opener)
        resumed.release(LEASE_ID)
        self.assertEqual(
            [getattr(call[0], "method") for call in opener.calls],
            ["HEAD", "PUT", "HEAD"],
        )
        self.assertEqual(self.state_payload()["release_attempts"], 2)
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")

    def test_second_uncertain_release_cannot_issue_a_third_release(self) -> None:
        self.acquire_held()
        first, _ = self.adapter(_Opener(OSError("first release uncertain")))
        with self.assertRaises(AzureBlobLeaseError):
            first.release(LEASE_ID)

        second_opener = _Opener(_head_held(), OSError("second release uncertain"))
        second, _ = self.adapter(second_opener)
        with self.assertRaises(AzureBlobLeaseError):
            second.release(LEASE_ID)
        self.assertEqual(self.state_payload()["release_attempts"], 2)

        third_opener = _Opener(_head_held())
        third, _ = self.adapter(third_opener)
        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_RELEASE_RECONCILIATION_EXHAUSTED$",
        ):
            third.release(LEASE_ID)
        self.assertEqual(len(third_opener.calls), 1)
        self.assertEqual(getattr(third_opener.calls[0][0], "method"), "HEAD")

    def test_release_has_no_success_receipt_until_released_is_persisted(self) -> None:
        self.acquire_held()
        adapter, _ = self.adapter(_Opener(_released(), _head_released()))
        real_save = adapter._store.save

        def fail_released(payload: dict[str, object], directory: int) -> None:
            if payload["lifecycle_state"] == "RELEASED":
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_UNAVAILABLE")
            real_save(payload, directory)

        adapter._store.save = fail_released
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_UNAVAILABLE$"
        ):
            adapter.release(LEASE_ID)
        self.assertEqual(
            self.state_payload()["lifecycle_state"], "RELEASE_INTENT"
        )

        resumed, _ = self.adapter(_Opener(_head_not_present(), _head_released()))
        receipt = resumed.release(LEASE_ID)
        self.assertEqual(receipt.lifecycle_state, "RELEASED")
        self.assertTrue(SHA256_RE.fullmatch(receipt.lifecycle_state_sha256))
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")

    def test_recomputed_released_state_requires_remote_evidence(self) -> None:
        self.acquire_held()
        document = json.loads(self.state_path.read_text(encoding="ascii"))
        payload = document["payload"]
        payload["generation"] += 1
        payload["lifecycle_state"] = "RELEASED"
        payload["release_attempts"] = 1
        document["payload_sha256"] = _canonical_json_sha256(payload)
        self.state_path.write_text(json.dumps(document), encoding="ascii")
        os.chmod(self.state_path, 0o600)
        opener = _Opener(OSError("released readback unavailable"))
        adapter, provider = self.adapter(opener)

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_TRANSPORT_UNAVAILABLE$",
        ):
            adapter.release(LEASE_ID)

        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(getattr(opener.calls[0][0], "method"), "HEAD")
        self.assertEqual(
            getattr(provider, "calls"),
            [
                {
                    "audience": "https://storage.azure.com/.default",
                    "identity_binding_sha256": READ_IDENTITY_SHA256,
                }
            ],
        )

    def test_released_state_blocks_when_remote_is_still_held(self) -> None:
        self.acquire_held()
        released, _ = self.adapter(_Opener(_released(), _head_released()))
        released.release(LEASE_ID)
        opener = _Opener(_head_held())
        adapter, _ = self.adapter(opener)

        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_RELEASE_UNCERTAIN$",
        ):
            adapter.release(LEASE_ID)

        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(self.state_payload()["lifecycle_state"], "RELEASED")

    def test_released_readback_consumes_capability_and_fails_closed(self) -> None:
        self.acquire_held()
        released, _ = self.adapter(_Opener(_released(), _head_released()))
        released.release(LEASE_ID)
        success_opener = _Opener(_head_released())
        success, success_provider = self.adapter(success_opener)
        success_capability = _lease_capability(success, uses=1)

        self.assertEqual(
            success.release(LEASE_ID, success_capability).lifecycle_state,
            "RELEASED",
        )
        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_LIVE_CAPABILITY_EXHAUSTED$",
        ):
            success.release(LEASE_ID, success_capability)
        self.assertEqual(len(success_opener.calls), 1)
        self.assertEqual(
            getattr(success_provider, "calls")[0]["identity_binding_sha256"],
            READ_IDENTITY_SHA256,
        )

        cases = (
            (
                _Response(
                    412,
                    BASE_URL,
                    {"x-ms-error-code": "LeaseIdMismatchWithBlobOperation"},
                ),
                "AZURE_BLOB_LEASE_FOREIGN",
            ),
            (_Response(404, BASE_URL, {}), "AZURE_BLOB_LEASE_BINDING_DRIFT"),
            (
                _Response(
                    200,
                    BASE_URL,
                    {
                        "ETag": '"changed"',
                        "x-ms-version": API_VERSION,
                        "x-ms-lease-state": "available",
                        "x-ms-lease-status": "unlocked",
                    },
                ),
                "AZURE_BLOB_LEASE_RESPONSE_INVALID",
            ),
            (
                _Response(
                    200,
                    BASE_URL,
                    {
                        "ETag": EXPECTED_ETAG,
                        "x-ms-version": "2021-01-01",
                        "x-ms-lease-state": "available",
                        "x-ms-lease-status": "unlocked",
                    },
                ),
                "AZURE_BLOB_LEASE_RESPONSE_INVALID",
            ),
            (
                _Response(
                    200,
                    "https://evil.invalid/redirected",
                    _success_headers(
                        **{
                            "x-ms-lease-state": "available",
                            "x-ms-lease-status": "unlocked",
                        }
                    ),
                ),
                "AZURE_BLOB_LEASE_RESPONSE_INVALID",
            ),
            (
                _Response(200, BASE_URL, _success_headers()),
                "AZURE_BLOB_LEASE_RESPONSE_INVALID",
            ),
        )
        for index, (response, code) in enumerate(cases):
            with self.subTest(index=index, code=code):
                opener = _Opener(response)
                adapter, _ = self.adapter(opener)
                capability = _lease_capability(adapter, uses=1)
                with self.assertRaisesRegex(AzureBlobLeaseError, f"^{code}$"):
                    adapter.release(LEASE_ID, capability)
                with self.assertRaisesRegex(
                    AzureBlobLeaseError,
                    r"^AZURE_BLOB_LEASE_LIVE_CAPABILITY_EXHAUSTED$",
                ):
                    adapter.release(LEASE_ID, capability)
                self.assertEqual(len(opener.calls), 1)

    def test_foreign_lost_and_binding_drift_heads_fail_closed(self) -> None:
        self.acquire_held()
        cases = (
            (
                _Response(
                    412,
                    BASE_URL,
                    {"x-ms-error-code": "LeaseIdMismatchWithBlobOperation"},
                ),
                "AZURE_BLOB_LEASE_FOREIGN",
            ),
            (_head_not_present(), "AZURE_BLOB_LEASE_NOT_HELD"),
            (
                _Response(
                    412,
                    BASE_URL,
                    {"x-ms-error-code": "ConditionNotMet"},
                ),
                "AZURE_BLOB_LEASE_BINDING_DRIFT",
            ),
            (_Response(404, BASE_URL, {}), "AZURE_BLOB_LEASE_BINDING_DRIFT"),
        )
        for response, code in cases:
            with self.subTest(code=code):
                adapter, _ = self.adapter(_Opener(response))
                with self.assertRaisesRegex(AzureBlobLeaseError, f"^{code}$"):
                    adapter.assert_held(LEASE_ID)

    def test_responses_require_exact_status_etag_version_lease_and_no_redirect(self) -> None:
        invalid = (
            _Response(200, LEASE_URL, _success_headers()),
            _Response(
                201,
                LEASE_URL,
                _success_headers(**{"x-ms-lease-id": str(OTHER_LEASE_ID)}),
            ),
            _Response(
                201,
                LEASE_URL,
                {"ETag": '"changed"', "x-ms-version": API_VERSION,
                 "x-ms-lease-id": str(LEASE_ID)},
            ),
            _Response(
                201,
                LEASE_URL,
                {"ETag": EXPECTED_ETAG, "x-ms-version": "2021-01-01",
                 "x-ms-lease-id": str(LEASE_ID)},
            ),
            _Response(
                201,
                "https://evil.invalid/redirected",
                _success_headers(**{"x-ms-lease-id": str(LEASE_ID)}),
            ),
            _Response(
                201,
                LEASE_URL,
                _success_headers(
                    **{
                        "Location": "https://evil.invalid",
                        "x-ms-lease-id": str(LEASE_ID),
                    }
                ),
            ),
            _Response(
                201,
                LEASE_URL,
                _success_headers(**{"x-ms-lease-id": str(LEASE_ID)}),
                b"unexpected",
            ),
        )
        for index, response in enumerate(invalid):
            with self.subTest(index=index):
                path = Path(self.temporary.name) / f"state-{index}" / "lease.json"
                opener = _Opener(response)
                adapter = AzureBlobLeaseAdapter(
                    binding=_binding(),
                    acquisition_safety_evidence=_acquisition_safety(),
                    state_path=path,
                    token_provider=_TokenProvider(),
                    opener=opener,
                    clock=self.clock,
                )
                adapter._test_live_action_capability = _lease_capability(adapter)
                with self.assertRaisesRegex(
                    AzureBlobLeaseError,
                    r"^AZURE_BLOB_LEASE_RESPONSE_INVALID$",
                ):
                    adapter.acquire(LEASE_ID)
                self.assertEqual(len(opener.calls), 1)

    def test_errors_are_stable_redacted_and_requests_are_not_retried(self) -> None:
        secret = (
            f"token=secret account=nacperflease001 lease={LEASE_ID} "
            f"etag={EXPECTED_ETAG}"
        )
        opener = _Opener(RuntimeError(secret))
        adapter, _ = self.adapter(opener)
        with self.assertRaises(AzureBlobLeaseError) as raised:
            adapter.acquire(LEASE_ID)
        self.assertEqual(
            str(raised.exception), "AZURE_BLOB_LEASE_TRANSPORT_UNAVAILABLE"
        )
        self.assertEqual(len(opener.calls), 1)
        self.assertNotIn(secret, str(raised.exception))
        self.assertNotIn(str(LEASE_ID), str(raised.exception))

        token_path = Path(self.temporary.name) / "token-failure" / "lease.json"

        def token_failure(**_: str) -> str:
            raise RuntimeError(secret)

        token_adapter = AzureBlobLeaseAdapter(
            binding=_binding(),
            acquisition_safety_evidence=_acquisition_safety(),
            state_path=token_path,
            token_provider=token_failure,
            opener=_Opener(),
            clock=self.clock,
        )
        token_adapter._test_live_action_capability = _lease_capability(
            token_adapter
        )
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_TOKEN_UNAVAILABLE$"
        ):
            token_adapter.acquire(LEASE_ID)

    def test_assert_capability_is_consumed_before_token_failure(self) -> None:
        self.acquire_held()
        calls = 0

        def token_failure(**_: str) -> str:
            nonlocal calls
            calls += 1
            raise RuntimeError("must stay redacted")

        adapter, _ = self.adapter(
            _Opener(),
            token_provider=token_failure,
        )
        adapter._test_live_action_capability = None
        one_use = _lease_capability(adapter, uses=1)

        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_TOKEN_UNAVAILABLE$"
        ):
            adapter.assert_held(LEASE_ID, one_use)
        with self.assertRaisesRegex(
            AzureBlobLeaseError,
            r"^AZURE_BLOB_LEASE_LIVE_CAPABILITY_EXHAUSTED$",
        ):
            adapter.assert_held(LEASE_ID, one_use)
        self.assertEqual(calls, 1)

    def test_private_state_rejects_tampering_permissions_and_binding_change(self) -> None:
        self.acquire_held()
        document = json.loads(self.state_path.read_text(encoding="ascii"))
        document["payload"]["lifecycle_state"] = "RELEASED"
        self.state_path.write_text(json.dumps(document), encoding="ascii")
        os.chmod(self.state_path, 0o600)
        adapter, _ = self.adapter(_Opener())
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_INVALID$"
        ):
            adapter.assert_held(LEASE_ID)

        self.state_path.unlink()
        self.acquire_held()
        os.chmod(self.state_path, 0o644)
        adapter, _ = self.adapter(_Opener())
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_INVALID$"
        ):
            adapter.assert_held(LEASE_ID)
        os.chmod(self.state_path, 0o600)

        adapter, _ = self.adapter(
            _Opener(), binding=_binding(expected_etag='"different"')
        )
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_CONFLICT$"
        ):
            adapter.assert_held(LEASE_ID)

        adapter, _ = self.adapter(
            _Opener(), binding=_binding(bff_account_name="otherbffaccount01")
        )
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_CONFLICT$"
        ):
            adapter.assert_held(LEASE_ID)

    def test_directory_swap_during_lock_open_fails_closed(self) -> None:
        for lock_kind in ("operation", "execution"):
            with self.subTest(lock_kind=lock_kind):
                parent = Path(self.temporary.name) / f"swap-{lock_kind}"
                state_path = parent / "lease.json"
                opener = _Opener()
                adapter, _ = self.adapter(opener, state_path=state_path)
                original_parent = parent.with_name(f"{parent.name}-original")
                trigger = (
                    ".lease.json.lock"
                    if lock_kind == "operation"
                    else ".lease.json.run.lock"
                )
                real_open = os.open
                swapped = False

                def swap_then_open(
                    path: object, *args: object, **kwargs: object
                ) -> int:
                    nonlocal swapped
                    if (
                        path == trigger
                        and kwargs.get("dir_fd") is not None
                        and not swapped
                    ):
                        parent.rename(original_parent)
                        parent.mkdir(mode=0o700)
                        swapped = True
                    return real_open(path, *args, **kwargs)  # type: ignore[arg-type]

                with mock.patch.object(os, "open", side_effect=swap_then_open):
                    with self.assertRaisesRegex(
                        AzureBlobLeaseError,
                        r"^AZURE_BLOB_LEASE_STATE_INVALID$",
                    ):
                        if lock_kind == "operation":
                            adapter.acquire(LEASE_ID)
                        else:
                            with adapter.execution_fence():
                                self.fail("swapped execution directory was accepted")

                self.assertTrue(swapped)
                self.assertEqual(opener.calls, [])
                self.assertFalse(state_path.exists())
                self.assertTrue((original_parent / trigger).exists())

    def test_directory_swap_during_atomic_replace_never_writes_new_path(self) -> None:
        parent = Path(self.temporary.name) / "swap-replace"
        state_path = parent / "lease.json"
        opener = _Opener()
        adapter, _ = self.adapter(opener, state_path=state_path)
        original_parent = parent.with_name(f"{parent.name}-original")
        real_replace = os.replace
        replace_arguments: dict[str, object] = {}

        def swap_then_replace(
            source: object, destination: object, **kwargs: object
        ) -> None:
            replace_arguments.update(kwargs)
            parent.rename(original_parent)
            parent.mkdir(mode=0o700)
            real_replace(source, destination, **kwargs)  # type: ignore[arg-type]

        with mock.patch.object(os, "replace", side_effect=swap_then_replace):
            with self.assertRaisesRegex(
                AzureBlobLeaseError,
                r"^AZURE_BLOB_LEASE_STATE_UNAVAILABLE$",
            ):
                adapter.acquire(LEASE_ID)

        self.assertEqual(opener.calls, [])
        self.assertFalse(state_path.exists())
        self.assertTrue((original_parent / state_path.name).exists())
        self.assertIsInstance(replace_arguments.get("src_dir_fd"), int)
        self.assertEqual(
            replace_arguments.get("src_dir_fd"),
            replace_arguments.get("dst_dir_fd"),
        )

    def test_non_string_lifecycle_is_a_stable_redacted_state_error(self) -> None:
        self.acquire_held()
        document = json.loads(self.state_path.read_text(encoding="ascii"))
        document["payload"]["lifecycle_state"] = ["HELD", str(LEASE_ID)]
        document["payload_sha256"] = "0" * 64
        self.state_path.write_text(json.dumps(document), encoding="ascii")
        os.chmod(self.state_path, 0o600)
        adapter, _ = self.adapter(_Opener())
        with self.assertRaisesRegex(
            AzureBlobLeaseError, r"^AZURE_BLOB_LEASE_STATE_INVALID$"
        ) as raised:
            adapter.assert_held(LEASE_ID)
        self.assertNotIn(str(LEASE_ID), str(raised.exception))

    def test_adapter_has_no_disallowed_lease_or_blob_operations(self) -> None:
        adapter, _ = self.adapter(_Opener())
        for name in (
            "break_lease",
            "break",
            "delete",
            "change",
            "renew",
            "reacquire",
            "create",
            "put_blob",
        ):
            self.assertFalse(hasattr(adapter, name), name)
        public_callables = {
            name
            for name in dir(adapter)
            if not name.startswith("_") and callable(getattr(adapter, name))
        }
        self.assertEqual(
            public_callables,
            {"acquire", "assert_held", "release", "execution_fence"},
        )

    def test_public_methods_require_uuid_objects(self) -> None:
        adapter, _ = self.adapter(_Opener())
        for operation in (adapter.acquire, adapter.assert_held, adapter.release):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(TypeError, r"^lease_id$"):
                    operation(str(LEASE_ID))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
