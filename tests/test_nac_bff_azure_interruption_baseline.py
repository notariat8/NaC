from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from nac_bff.azure_activation import FUNCTION_APP, RESOURCE_GROUP, SUBSCRIPTION_ID
from nac_bff.azure_interruption_baseline import (
    DEPLOYMENT_NAME,
    EXPECTED_DEPLOYMENT_TYPE_COUNTS,
    RESOURCE_TAGS,
    exact_baseline_matches,
    load_expectation,
)


ACTIVATION_HASH = "a" * 64
COMMIT = "b" * 40
TREE = "c" * 40
RESOURCE_SUFFIX = "43o765p7uslni"
CLIENT_ID = "11111111-1111-4111-8111-111111111111"
PRINCIPAL_ID = "22222222-2222-4222-8222-222222222222"


def _write_secure_json(path: Path, value: object) -> bytes:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    os.chmod(path, 0o600)
    return raw


def _prepared(
    run_dir: Path,
    *,
    activation_hash: str = ACTIVATION_HASH,
    commit: str = COMMIT,
    tree: str = TREE,
) -> dict:
    resources = []
    for resource_type, count in EXPECTED_DEPLOYMENT_TYPE_COUNTS.items():
        for index in range(count):
            resources.append({
                "type": resource_type,
                "name": f"resource-{index}",
                "dependsOn": [],
            })
    template = {
        "metadata": {"_generator": {"templateHash": "13643045116711268849"}},
        "resources": resources,
    }
    parameters = {
        "parameters": {
            "location": {"value": "germanywestcentral"},
            "environmentName": {"value": "test"},
            "m365TenantId": {
                "value": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
            },
            "bffApiAudience": {
                "value": "33333333-3333-4333-8333-333333333333"
            },
            "bffRequiredDelegatedScope": {"value": "Matter.Read"},
            "functionAppName": {"value": FUNCTION_APP},
            "maximumInstanceCount": {"value": 4},
            "httpPerInstanceConcurrency": {"value": 16},
            "tags": {"value": {}},
        }
    }
    prepared = run_dir / "prepared"
    template_path = prepared / "main.json"
    template_raw = _write_secure_json(template_path, template)
    template_path.chmod(0o400)
    tree_template_path = (
        prepared
        / "approved-tree"
        / "deploy/runtime/azure/nac-bff/infra/compiled/main.json"
    )
    _write_secure_json(tree_template_path, template)
    tree_template_path.chmod(0o400)
    parameters_raw = _write_secure_json(
        prepared / "main.parameters.json", parameters
    )
    manifest_base = {
        "schema_version": "nac.m365-azure-bff-prepared-inputs/v1",
        "approved_commit_sha": commit,
        "approved_tree_sha": tree,
        "activation_hash": activation_hash,
        "approved_tree_snapshot_sha256": "d" * 64,
        "bicep_snapshot_sha256": hashlib.sha256(template_raw).hexdigest(),
        "bicep_parameters_snapshot_sha256": hashlib.sha256(
            parameters_raw
        ).hexdigest(),
        "function_package_sha256": "e" * 64,
        "spfx_package_sha256": "f" * 64,
    }
    manifest_raw = json.dumps(
        manifest_base, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    manifest = {
        **manifest_base,
        "prepared_inputs_sha256": hashlib.sha256(
            manifest_raw.encode("utf-8")
        ).hexdigest(),
    }
    _write_secure_json(prepared / "prepared-inputs.redacted.json", manifest)
    return manifest


class _ApprovedTreeSource:
    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir

    def inspect(self, _repo_root, *, approved_commit, approved_tree):
        del approved_commit, approved_tree
        path = (
            self._run_dir
            / "prepared/approved-tree"
            / "deploy/runtime/azure/nac-bff/infra/compiled/main.json"
        )
        return SimpleNamespace(
            manifest_sha256="d" * 64,
            file_count=1,
            file_sha256={
                "deploy/runtime/azure/nac-bff/infra/compiled/main.json": (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                )
            },
        )


def _load_expectation(run_dir: Path, state: dict, request):
    return load_expectation(
        run_dir,
        state,
        request,
        repo_root=run_dir,
        approved_tree_source=_ApprovedTreeSource(run_dir),
    )


def _resource_id(resource_type: str, name: str) -> str:
    return (
        f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/{resource_type}/{name}"
    )


def _inventory() -> list[dict]:
    specifications = (
        ("Microsoft.ManagedIdentity/userAssignedIdentities", f"id-nac-bff-test-{RESOURCE_SUFFIX}", None),
        ("Microsoft.Storage/storageAccounts", f"stnacbff{RESOURCE_SUFFIX}", "StorageV2"),
        ("Microsoft.OperationalInsights/workspaces", f"log-nac-bff-test-{RESOURCE_SUFFIX}", None),
        ("Microsoft.Insights/components", f"appi-nac-bff-test-{RESOURCE_SUFFIX}", "web"),
        ("Microsoft.Web/serverfarms", f"plan-nac-bff-test-{RESOURCE_SUFFIX}", "functionapp"),
        ("Microsoft.Web/sites", FUNCTION_APP, "functionapp,linux"),
        ("Microsoft.Insights/ActionGroups", "Application Insights Smart Detection", None),
    )
    rows = []
    for resource_type, name, kind in specifications:
        smart = resource_type.lower() == "microsoft.insights/actiongroups"
        sku = (
            {"name": "Standard_LRS", "tier": "Standard"}
            if resource_type.lower() == "microsoft.storage/storageaccounts"
            else {"name": "FC1", "tier": "FlexConsumption"}
            if resource_type.lower() == "microsoft.web/serverfarms"
            else None
        )
        smart_properties = (
            {
                "groupShortName": "SmartDetect",
                "enabled": True,
                "armRoleReceivers": [
                    {
                        "name": "Monitoring Contributor",
                        "roleId": "749f88d5-cbae-40b8-bcfc-e573ddc772fa",
                        "useCommonAlertSchema": True,
                    },
                    {
                        "name": "Monitoring Reader",
                        "roleId": "43d0d8ad-25c7-4714-9337-8ba259a9fe05",
                        "useCommonAlertSchema": True,
                    },
                ],
                "emailReceivers": [],
                "smsReceivers": [],
                "webhookReceivers": [],
                "eventHubReceivers": [],
                "itsmReceivers": [],
                "azureAppPushReceivers": [],
                "automationRunbookReceivers": [],
                "voiceReceivers": [],
                "logicAppReceivers": [],
                "azureFunctionReceivers": [],
            }
            if smart else None
        )
        rows.append({
            "id": _resource_id(resource_type, name),
            "name": name,
            "type": resource_type.lower(),
            "resource_group": RESOURCE_GROUP,
            "location": "global" if smart else "germanywestcentral",
            "kind": kind,
            "sku": sku,
            "tags": None if smart else RESOURCE_TAGS,
            "managed_by": None,
            "properties": smart_properties,
        })
    return sorted(rows, key=lambda row: (row["type"], row["name"]))


def _deployment(expectation: dict) -> dict:
    inventory = _inventory()
    by_type = {row["type"]: row for row in inventory}
    return {
        "name": DEPLOYMENT_NAME,
        "resource_group": RESOURCE_GROUP,
        "provisioning_state": "Succeeded",
        "mode": "Incremental",
        "template_hash": expectation["azure_template_hash"],
        "parameters_sha256": expectation["deployment_parameters_sha256"],
        "bff_api_audience": expectation["bff_api_audience"],
        "outputs": {
            "function_app_resource_id": by_type["microsoft.web/sites"]["id"],
            "function_app_host_name": f"{FUNCTION_APP}.azurewebsites.net",
            "managed_identity_resource_id": by_type[
                "microsoft.managedidentity/userassignedidentities"
            ]["id"],
            "managed_identity_client_id": CLIENT_ID,
            "managed_identity_principal_id": PRINCIPAL_ID,
        },
    }


def _identity_binding() -> dict:
    identity = next(
        item
        for item in _inventory()
        if item["type"]
        == "microsoft.managedidentity/userassignedidentities"
    )
    return {
        "managed_identity": {
            "id": identity["id"],
            "name": identity["name"],
            "client_id": CLIENT_ID,
            "principal_id": PRINCIPAL_ID,
            "tenant_id": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
        },
        "function_app": {
            "type": "UserAssigned",
            "user_assigned_identities": [{
                "id": identity["id"],
                "client_id": CLIENT_ID,
                "principal_id": PRINCIPAL_ID,
            }],
        },
    }


def _operations() -> list[dict]:
    by_type = {row["type"]: row for row in _inventory()}
    identity_id = by_type[
        "microsoft.managedidentity/userassignedidentities"
    ]["id"].lower()
    storage_id = by_type["microsoft.storage/storageaccounts"]["id"].lower()
    workspace_id = by_type["microsoft.operationalinsights/workspaces"]["id"].lower()
    component_id = by_type["microsoft.insights/components"]["id"].lower()
    plan_id = by_type["microsoft.web/serverfarms"]["id"].lower()
    site_id = by_type["microsoft.web/sites"]["id"].lower()
    targets = [
        ("microsoft.managedidentity/userassignedidentities", identity_id),
        ("microsoft.storage/storageaccounts", storage_id),
        ("microsoft.storage/storageaccounts/blobservices", f"{storage_id}/blobservices/default"),
        ("microsoft.storage/storageaccounts/blobservices/containers", f"{storage_id}/blobservices/default/containers/function-releases"),
        ("microsoft.operationalinsights/workspaces", workspace_id),
        ("microsoft.insights/components", component_id),
        ("microsoft.insights/components/currentbillingfeatures", f"{component_id}/currentbillingfeatures/basic"),
        ("microsoft.web/serverfarms", plan_id),
        ("microsoft.web/sites", site_id),
        ("microsoft.web/sites/config", f"{site_id}/config/appsettings"),
        ("microsoft.authorization/roleassignments", f"{storage_id}/providers/microsoft.authorization/roleassignments/33333333-3333-4333-8333-333333333333"),
        ("microsoft.authorization/roleassignments", f"{component_id}/providers/microsoft.authorization/roleassignments/44444444-4444-4444-8444-444444444444"),
    ]
    return sorted(
        [
            {
                "id": target_id,
                "type": resource_type,
                "provisioning_state": "Succeeded",
            }
            for resource_type, target_id in targets
        ],
        key=lambda row: (row["type"], row["id"]),
    )


def _live_resource_state() -> dict:
    targets = sorted(
        (
            {"id": item["id"].lower(), "type": item["type"]}
            for item in _operations()
        ),
        key=lambda item: (item["type"], item["id"]),
    )
    graph_targets = sorted(
        (
            {"id": resource_id, "type": resource_type}
            for resource_id, resource_type in {
                (item["id"].lower(), item["type"].lower())
                for item in [*_inventory(), *_operations()]
            }
        ),
        key=lambda item: (item["type"], item["id"]),
    )
    from nac_bff.azure_interruption_contract import compact_sha256_json

    return {
        "schema_version": "nac.azure-interruption-live-resource-state/v1",
        "resource_count": 12,
        "resource_targets_sha256": compact_sha256_json(targets),
        "resource_graph_count": len(graph_targets),
        "resource_graph_targets_sha256": compact_sha256_json(graph_targets),
        "security_properties_exact": True,
    }


class AzureInterruptionBaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.temporary.name)
        self.request = SimpleNamespace(
            expected_activation_hash=ACTIVATION_HASH,
            approved_commit=COMMIT,
            approved_tree=TREE,
        )
        self.state = {"activation_hash": ACTIVATION_HASH}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_absent_prepared_inputs_preserve_resource_group_only_mode(self):
        expectation, error = _load_expectation(
            self.run_dir, self.state, self.request
        )
        self.assertIsNone(error)
        self.assertIsNone(expectation)

    def test_expectation_is_bound_to_manifest_template_parameters_and_graph(self):
        from nac_bff.azure_activation_composition import (
            _deployment_name,
            _sha256_json as activation_sha256_json,
        )

        manifest = _prepared(self.run_dir)
        expectation, error = _load_expectation(
            self.run_dir, self.state, self.request
        )
        self.assertIsNone(error)
        self.assertIsNotNone(expectation)
        assert expectation is not None
        self.assertEqual(
            expectation["prepared_inputs_sha256"],
            manifest["prepared_inputs_sha256"],
        )
        self.assertEqual(expectation["deployment_name"], DEPLOYMENT_NAME)
        self.assertEqual(expectation["deployment_name"], _deployment_name(None))
        self.assertEqual(
            expectation["deployment_parameters_sha256"],
            activation_sha256_json({
                "bffApiAudience": {
                    "value": "33333333-3333-4333-8333-333333333333"
                },
                "bffRequiredDelegatedScope": {"value": "Matter.Read"},
                "environmentName": {"value": "test"},
                "functionAppName": {"value": FUNCTION_APP},
                "httpPerInstanceConcurrency": {"value": 16},
                "location": {"value": "germanywestcentral"},
                "m365TenantId": {
                    "value": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
                },
                "maximumInstanceCount": {"value": 4},
                "tags": {"value": {}},
            }),
        )
        self.assertEqual(
            expectation["deployment_type_counts"],
            EXPECTED_DEPLOYMENT_TYPE_COUNTS,
        )
        from nac_bff.azure_activation_runner import _sha256_json
        from nac_bff.azure_interruption_contract import newline_sha256_json

        self.assertEqual(
            newline_sha256_json(expectation), _sha256_json(expectation)
        )
        self.assertTrue(
            exact_baseline_matches(
                _inventory(),
                _deployment(expectation),
                _operations(),
                _identity_binding(),
                _live_resource_state(),
                expectation,
            )
        )

    def test_api_audience_must_differ_from_managed_identity_client_id(self):
        _prepared(self.run_dir)
        expectation, error = _load_expectation(
            self.run_dir, self.state, self.request
        )
        self.assertIsNone(error)
        assert expectation is not None
        deployment = _deployment(expectation)
        expectation = {**expectation, "bff_api_audience": CLIENT_ID}
        deployment["bff_api_audience"] = CLIENT_ID

        self.assertFalse(
            exact_baseline_matches(
                _inventory(),
                deployment,
                _operations(),
                _identity_binding(),
                _live_resource_state(),
                expectation,
            )
        )

    def test_world_readable_prepared_input_is_rejected(self):
        _prepared(self.run_dir)
        template_path = self.run_dir / "prepared" / "main.json"
        template_path.chmod(0o644)

        expectation, error = _load_expectation(
            self.run_dir, self.state, self.request
        )

        self.assertIsNone(expectation)
        self.assertEqual(error, "INTERRUPTION_BASELINE_BINDING_INVALID")

    def test_partial_or_tampered_prepared_inputs_fail_closed(self):
        _prepared(self.run_dir)
        (self.run_dir / "prepared" / "main.parameters.json").unlink()
        expectation, error = _load_expectation(
            self.run_dir, self.state, self.request
        )
        self.assertIsNone(expectation)
        self.assertEqual(error, "INTERRUPTION_BASELINE_BINDING_INVALID")

    def test_self_consistent_manifest_with_incomplete_parameters_is_rejected(self):
        _prepared(self.run_dir)
        prepared = self.run_dir / "prepared"
        parameters_path = prepared / "main.parameters.json"
        parameters = json.loads(parameters_path.read_text(encoding="utf-8"))
        parameters["parameters"].pop("tags")
        parameters_raw = _write_secure_json(parameters_path, parameters)
        manifest_path = prepared / "prepared-inputs.redacted.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["bicep_parameters_snapshot_sha256"] = hashlib.sha256(
            parameters_raw
        ).hexdigest()
        manifest_base = {
            key: value
            for key, value in manifest.items()
            if key != "prepared_inputs_sha256"
        }
        manifest_raw = json.dumps(
            manifest_base,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        manifest["prepared_inputs_sha256"] = hashlib.sha256(
            manifest_raw.encode("utf-8")
        ).hexdigest()
        _write_secure_json(manifest_path, manifest)

        expectation, error = _load_expectation(
            self.run_dir, self.state, self.request
        )

        self.assertIsNone(expectation)
        self.assertEqual(error, "INTERRUPTION_BASELINE_BINDING_INVALID")

    def test_parent_directory_symlink_is_rejected(self):
        _prepared(self.run_dir)
        prepared = self.run_dir / "prepared"
        actual = self.run_dir / "prepared-real"
        prepared.rename(actual)
        prepared.symlink_to(actual, target_is_directory=True)

        expectation, error = _load_expectation(
            self.run_dir, self.state, self.request
        )

        self.assertIsNone(expectation)
        self.assertEqual(error, "INTERRUPTION_BASELINE_BINDING_INVALID")

    def test_self_consistent_manifest_with_false_git_provenance_is_rejected(self):
        _prepared(self.run_dir)

        class WrongTreeSource:
            def inspect(self, *_args, **_kwargs):
                return SimpleNamespace(
                    manifest_sha256="0" * 64,
                    file_count=1,
                    file_sha256={
                        "deploy/runtime/azure/nac-bff/infra/compiled/main.json": (
                            "0" * 64
                        )
                    },
                )

        expectation, error = load_expectation(
            self.run_dir,
            self.state,
            self.request,
            repo_root=self.run_dir,
            approved_tree_source=WrongTreeSource(),
        )

        self.assertIsNone(expectation)
        self.assertEqual(
            error, "INTERRUPTION_BASELINE_GIT_PROVENANCE_MISMATCH"
        )

    def test_inventory_deployment_and_operation_drift_are_rejected(self):
        _prepared(self.run_dir)
        expectation, error = _load_expectation(
            self.run_dir, self.state, self.request
        )
        self.assertIsNone(error)
        assert expectation is not None
        cases = []
        partial = _inventory()[:-1]
        cases.append((
            partial, _deployment(expectation), _operations(),
            _identity_binding(),
        ))
        deployment = _deployment(expectation)
        deployment["template_hash"] = "1"
        cases.append((
            _inventory(), deployment, _operations(), _identity_binding()
        ))
        operations = _operations()
        operations[0]["provisioning_state"] = "Running"
        cases.append((
            _inventory(), _deployment(expectation), operations,
            _identity_binding(),
        ))
        duplicate_operations = _operations()
        duplicate_operations[1]["id"] = duplicate_operations[0]["id"]
        cases.append((
            _inventory(), _deployment(expectation), duplicate_operations,
            _identity_binding(),
        ))
        extra = _inventory() + [copy.deepcopy(_inventory()[0])]
        cases.append((
            extra, _deployment(expectation), _operations(),
            _identity_binding(),
        ))
        kind_drift = _inventory()
        next(
            item for item in kind_drift
            if item["type"] == "microsoft.web/sites"
        )["kind"] = "app"
        cases.append((
            kind_drift, _deployment(expectation), _operations(),
            _identity_binding(),
        ))
        sku_drift = _inventory()
        next(
            item for item in sku_drift
            if item["type"] == "microsoft.web/serverfarms"
        )["sku"] = {"name": "P1V3", "tier": "PremiumV3"}
        cases.append((
            sku_drift, _deployment(expectation), _operations(),
            _identity_binding(),
        ))
        foreign_target = _operations()
        next(
            item for item in foreign_target
            if item["type"] == "microsoft.web/sites/config"
        )["id"] = "/subscriptions/foreign/resourcegroups/foreign/providers/microsoft.web/sites/foreign/config/appsettings"
        cases.append((
            _inventory(), _deployment(expectation), foreign_target,
            _identity_binding(),
        ))
        smart_drift = _inventory()
        next(
            item for item in smart_drift
            if item["type"] == "microsoft.insights/actiongroups"
        )["properties"]["enabled"] = False
        cases.append((
            smart_drift, _deployment(expectation), _operations(),
            _identity_binding(),
        ))
        identity_drift = _identity_binding()
        identity_drift["function_app"]["user_assigned_identities"][0][
            "principal_id"
        ] = "9" * 36
        cases.append((
            _inventory(), _deployment(expectation), _operations(),
            identity_drift,
        ))
        for inventory, deployment, operations, identity_binding in cases:
            with self.subTest(case=len(inventory)):
                self.assertFalse(
                    exact_baseline_matches(
                        inventory, deployment, operations,
                        identity_binding, _live_resource_state(), expectation
                    )
                )


if __name__ == "__main__":
    unittest.main()
