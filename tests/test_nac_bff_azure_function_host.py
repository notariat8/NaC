from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
import subprocess
import sys
import threading
import time
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
AZURE_HOST_ROOT = REPO_ROOT / "deploy/runtime/azure/nac-bff"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.bpmn_asset import (  # noqa: E402
    CANONICAL_BPMN_MODEL_KEY,
    CANONICAL_BPMN_SHA256,
)
from nac_bff.composition import (  # noqa: E402
    BffSettings,
    CompositionError,
    ConfiguredGraphRestPort,
    ManagedIdentityGraphTokenProvider,
    create_app_from_env,
    managed_identity_token_provider_from_env,
)
from nac_bff.synthetic_workspace_graph import (  # noqa: E402
    SyntheticWorkspaceGraphRestAdapter,
)
from nac_bff.test_environment import (  # noqa: E402
    ALLOWED_MATTER_ID,
    ALLOWED_PURPOSE,
    ALLOWED_TENANT_ID,
    ALLOWED_WORKSPACE_ID,
    AccessDecision,
    ValidatedClaims,
)
from nac_mvp_test_environment import (  # noqa: E402
    DEADLINE,
    MATTER_STATUS,
    TASKS,
)


TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _environment() -> dict[str, str]:
    return {
        "NAC_BFF_TENANT_ID": TENANT_ID,
        "M365_TENANT_ID": TENANT_ID,
        "NAC_BFF_GRAPH_MANAGED_IDENTITY_CLIENT_ID": "uami-client-id",
        "NAC_BFF_AUDIENCE": "api://00000000-0000-0000-0000-000000000002",
        "NAC_BFF_REQUIRED_SCOPE": "Matter.Read",
    }


def _projection() -> dict:
    return {
        "status": MATTER_STATUS,
        "deadline": DEADLINE,
        "tasks": [
            {
                "taskId": task["task_id"],
                "title": task["title"],
                "stepCode": task["step_code"],
                "status": task["status"],
                "requiresNotaryApproval": task["requires_notary_approval"],
                "dueAt": task["due_at"],
            }
            for task in TASKS
        ],
    }


class _AllowAssigned:
    def decide(self, **_: str) -> AccessDecision:
        return AccessDecision.assigned()


class _WorkspacePort:
    def read_synthetic_workspace(self, **_: str) -> dict:
        return _projection()


class AzureBffCompositionTests(unittest.TestCase):
    def test_configured_graph_port_export_keeps_the_fixed_adapter(self) -> None:
        self.assertIs(ConfiguredGraphRestPort, SyntheticWorkspaceGraphRestAdapter)

    def test_settings_require_matching_tenant_audience_and_one_scope(self) -> None:
        settings = BffSettings.from_env(_environment())

        self.assertEqual(settings.tenant_id, TENANT_ID)
        self.assertEqual(settings.audience, _environment()["NAC_BFF_AUDIENCE"])
        self.assertEqual(settings.required_scope, "Matter.Read")
        self.assertEqual(
            settings.issuer,
            f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",
        )
        self.assertEqual(
            settings.jwks_uri,
            "https://login.microsoftonline.com/common/discovery/v2.0/keys",
        )

        for missing_name in (
            "M365_TENANT_ID",
            "NAC_BFF_AUDIENCE",
            "NAC_BFF_REQUIRED_SCOPE",
        ):
            with self.subTest(missing=missing_name):
                invalid = _environment()
                invalid.pop(missing_name)
                with self.assertRaises(CompositionError):
                    BffSettings.from_env(invalid)

        mismatched = _environment()
        mismatched["M365_TENANT_ID"] = "00000000-0000-0000-0000-000000000099"
        with self.assertRaises(CompositionError):
            BffSettings.from_env(mismatched)

        multiple_scopes = _environment()
        multiple_scopes["NAC_BFF_REQUIRED_SCOPE"] = "Matter.Read Matter.Write"
        with self.assertRaises(CompositionError):
            BffSettings.from_env(multiple_scopes)

    def test_managed_identity_provider_uses_uami_and_caches_graph_token(self) -> None:
        captured: dict[str, object] = {}

        class _Credential:
            def get_token(self, scope: str):
                captured.setdefault("scopes", []).append(scope)
                return types.SimpleNamespace(
                    token="offline-managed-identity-token",
                    expires_on=4_000_000_000,
                )

        def credential_factory(*, client_id: str):
            captured["client_id"] = client_id
            return _Credential()

        provider = managed_identity_token_provider_from_env(
            _environment(),
            credential_factory=credential_factory,
        )

        self.assertIsInstance(provider, ManagedIdentityGraphTokenProvider)
        self.assertEqual(
            provider.fetch_access_token_with_timeout(timeout_seconds=1.0),
            "offline-managed-identity-token",
        )
        self.assertEqual(provider.fetch_access_token(), "offline-managed-identity-token")
        self.assertEqual(captured["client_id"], "uami-client-id")
        self.assertEqual(
            captured["scopes"],
            ["https://graph.microsoft.com/.default"],
        )
        with self.assertRaises(CompositionError):
            provider.fetch_access_token_with_timeout(timeout_seconds=6.0)
        with self.assertRaises(CompositionError):
            managed_identity_token_provider_from_env(
                {},
                credential_factory=credential_factory,
            )

    def test_missing_configuration_stays_live_but_never_ready(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI runtime dependencies are not installed")

        client = TestClient(create_app_from_env({}))
        health = client.get(
            "/healthz", headers={"X-Correlation-ID": "offline-health"}
        )
        readiness = client.get("/readyz")
        data = client.get(
            f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/{ALLOWED_MATTER_ID}",
            params={"purpose": ALLOWED_PURPOSE},
        )

        self.assertEqual((health.status_code, health.json()), (200, {"status": "ok"}))
        self.assertEqual(health.headers["x-correlation-id"], "offline-health")
        self.assertEqual(
            (readiness.status_code, readiness.json()),
            (503, {"status": "unavailable"}),
        )
        self.assertEqual(
            (data.status_code, data.json()),
            (401, {"status": 401, "error": {"code": "AUTHENTICATION_REQUIRED"}}),
        )

    def test_configured_workbench_treats_wrong_tenant_claim_as_authentication_failure(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI runtime dependencies are not installed")

        port_calls: list[str] = []

        class _Access:
            def decide(self, **_: str) -> AccessDecision:
                port_calls.append("access")
                return AccessDecision.deny()

        class _Workspace:
            def read_synthetic_workspace(self, **_: str) -> dict:
                port_calls.append("workspace")
                return _projection()

        def validator_factory(**_: object):
            def validate(_authorization: object) -> ValidatedClaims:
                return ValidatedClaims(
                    object_id="wrong-tenant-actor",
                    tenant_id="00000000-0000-0000-0000-000000000099",
                    subject="wrong-tenant-actor",
                )

            return validate

        app = create_app_from_env(
            _environment(),
            validator_factory=validator_factory,
            token_provider_factory=lambda _: object(),
            graph_client_factory=lambda _: object(),
            access_port_factory=lambda *_args, **_kwargs: _Access(),
            workspace_port_factory=lambda _: _Workspace(),
        )
        client = TestClient(app)
        response = client.get(
            f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/"
            f"{ALLOWED_MATTER_ID}/workbench-snapshot",
            params={"purpose": ALLOWED_PURPOSE},
            headers={"Authorization": "Bearer wrong-tenant-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.content,
            b'{"status":401,"error":{"code":"AUTHENTICATION_REQUIRED"}}',
        )
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["www-authenticate"], "Bearer")
        self.assertEqual(port_calls, [])

    def test_configured_app_stages_readiness_until_dependency_backed_success(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI runtime dependencies are not installed")

        validator_configuration: dict[str, object] = {}
        validator_thread_ids: set[int] = set()
        bff_thread_ids: set[int] = set()
        event_loop_thread_ids: set[int] = set()

        class _RecordingAccess:
            def decide(self, **request: str) -> AccessDecision:
                bff_thread_ids.add(threading.get_ident())
                issued = datetime.now(UTC)
                expires = issued + timedelta(minutes=5)
                return AccessDecision.assigned(
                    decision_id=f"access:{ALLOWED_MATTER_ID}:1",
                    decision_version="policy-v1",
                    subject_id=request["actor_id"],
                    role="notary",
                    workspace_id=ALLOWED_WORKSPACE_ID,
                    matter_id=ALLOWED_MATTER_ID,
                    purpose=ALLOWED_PURPOSE,
                    issued_at=issued.isoformat(timespec="seconds").replace("+00:00", "Z"),
                    expires_at=expires.isoformat(timespec="seconds").replace("+00:00", "Z"),
                )

        class _RecordingWorkspace:
            def read_synthetic_workspace(self, **_: str) -> dict:
                bff_thread_ids.add(threading.get_ident())
                return _projection()

        def validator_factory(**configuration: object):
            validator_configuration.update(configuration)

            def validate(authorization: object) -> ValidatedClaims:
                validator_thread_ids.add(threading.get_ident())
                if authorization != "Bearer test-token":
                    raise ValueError("authentication failed")
                return ValidatedClaims(
                    object_id="assigned-object-id",
                    tenant_id=ALLOWED_TENANT_ID,
                    subject="assigned-object-id",
                )

            return validate

        environment = _environment()
        environment["NAC_BFF_TENANT_ID"] = ALLOWED_TENANT_ID
        environment["M365_TENANT_ID"] = ALLOWED_TENANT_ID
        app = create_app_from_env(
            environment,
            validator_factory=validator_factory,
            token_provider_factory=lambda _: object(),
            graph_client_factory=lambda _: object(),
            access_port_factory=lambda *_args, **_kwargs: _RecordingAccess(),
            workspace_port_factory=lambda _: _RecordingWorkspace(),
        )

        @app.middleware("http")
        async def record_event_loop_thread(request, call_next):
            event_loop_thread_ids.add(threading.get_ident())
            return await call_next(request)

        client = TestClient(app)

        readiness = client.get("/readyz")
        unauthorized = client.get(
            f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/{ALLOWED_MATTER_ID}",
            params={"purpose": ALLOWED_PURPOSE},
        )
        event_loop_thread_ids.clear()
        validator_thread_ids.clear()
        bff_thread_ids.clear()
        allowed = client.get(
            f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/{ALLOWED_MATTER_ID}",
            params={"purpose": ALLOWED_PURPOSE},
            headers={
                "Authorization": "Bearer test-token",
                "X-Correlation-ID": "request.620",
            },
        )
        workbench = client.get(
            f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/"
            f"{ALLOWED_MATTER_ID}/workbench-snapshot",
            params={"purpose": ALLOWED_PURPOSE},
            headers={"Authorization": "Bearer test-token"},
        )
        allowed_event_loop_thread_ids = set(event_loop_thread_ids)

        self.assertEqual(
            (readiness.status_code, readiness.json()), (503, {"status": "unavailable"})
        )
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(unauthorized.headers["www-authenticate"], "Bearer")
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.headers["x-correlation-id"], "request.620")
        self.assertEqual(allowed.json()["matter"]["matterId"], ALLOWED_MATTER_ID)
        self.assertEqual(workbench.status_code, 200)
        self.assertEqual(workbench.headers["cache-control"], "no-store")
        self.assertEqual(workbench.json()["schemaVersion"], "nac.workbench.snapshot/v1")
        self.assertEqual(workbench.json()["matter"]["id"], ALLOWED_MATTER_ID)
        self.assertTrue(
            allowed_event_loop_thread_ids.isdisjoint(
                validator_thread_ids | bff_thread_ids
            )
        )
        activated_readiness = client.get("/readyz")
        self.assertEqual(
            (activated_readiness.status_code, activated_readiness.json()),
            (200, {"status": "ready"}),
        )
        self.assertEqual(
            validator_configuration["expected_tenant_id"], ALLOWED_TENANT_ID
        )
        self.assertEqual(validator_configuration["required_scopes"], {"Matter.Read"})
        self.assertTrue(validator_thread_ids)
        self.assertTrue(bff_thread_ids)

    def test_request_timeout_bounds_authentication_and_bff_work(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI runtime dependencies are not installed")

        class _Access:
            def decide(self, **_: str) -> AccessDecision:
                return AccessDecision.assigned()

        class _Workspace:
            def read_synthetic_workspace(self, **_: str) -> dict:
                return _projection()

        def validator_factory(**_: object):
            def validate(_authorization: object) -> ValidatedClaims:
                time.sleep(0.2)
                return ValidatedClaims(
                    object_id="assigned-object-id",
                    tenant_id=TENANT_ID,
                    subject="assigned-object-id",
                )
            return validate

        app = create_app_from_env(
            _environment(),
            validator_factory=validator_factory,
            token_provider_factory=lambda _: object(),
            graph_client_factory=lambda _: object(),
            access_port_factory=lambda *_args, **_kwargs: _Access(),
            workspace_port_factory=lambda _: _Workspace(),
        )
        with (
            patch("nac_bff.fastapi_adapter.REQUEST_TIMEOUT_SECONDS", 0.01),
            TestClient(app) as client,
        ):
            started = time.monotonic()
            response = client.get(
                f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/{ALLOWED_MATTER_ID}",
                params={"purpose": ALLOWED_PURPOSE},
                headers={"Authorization": "Bearer test-token"},
            )
            elapsed = time.monotonic() - started
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "service unavailable"})
        self.assertLess(elapsed, 0.1)

    def test_invalid_correlation_id_is_not_reflected(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI runtime dependencies are not installed")

        response = TestClient(create_app_from_env({})).get(
            "/healthz",
            headers={"X-Correlation-ID": "contains spaces"},
        )

        generated = response.headers["x-correlation-id"]
        self.assertNotEqual(generated, "contains spaces")
        self.assertRegex(generated, r"^[0-9a-f]{32}$")
        self.assertEqual(response.headers["cache-control"], "no-store")


class AzureFunctionHostFilesTests(unittest.TestCase):
    def test_python_v2_host_import_is_stub_friendly(self) -> None:
        function_app_path = AZURE_HOST_ROOT / "function_app.py"
        captured: dict[str, object] = {}
        asgi_sentinel = object()

        class _AuthLevel:
            ANONYMOUS = object()

        class _AsgiFunctionApp:
            def __init__(self, *, app: object, http_auth_level: object) -> None:
                captured["app"] = app
                captured["http_auth_level"] = http_auth_level

        azure_module = types.ModuleType("azure")
        functions_module = types.ModuleType("azure.functions")
        functions_module.AuthLevel = _AuthLevel
        functions_module.AsgiFunctionApp = _AsgiFunctionApp
        azure_module.functions = functions_module

        spec = importlib.util.spec_from_file_location(
            "nac_bff_test_function_app", function_app_path
        )
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        with (
            patch.dict(
                sys.modules,
                {"azure": azure_module, "azure.functions": functions_module},
            ),
            patch("nac_bff.composition.create_app_from_env", return_value=asgi_sentinel),
        ):
            spec.loader.exec_module(module)

        self.assertIsInstance(module.app, _AsgiFunctionApp)
        self.assertIs(captured["app"], asgi_sentinel)
        self.assertIs(captured["http_auth_level"], _AuthLevel.ANONYMOUS)

    def test_host_metadata_and_dependencies_are_minimal_and_pinned(self) -> None:
        host = json.loads(
            (AZURE_HOST_ROOT / "host.json").read_text(encoding="utf-8")
        )
        requirements = (AZURE_HOST_ROOT / "requirements.txt").read_text(
            encoding="utf-8"
        )
        funcignore = (AZURE_HOST_ROOT / ".funcignore").read_text(encoding="utf-8")

        self.assertEqual(host["version"], "2.0")
        self.assertEqual(host["extensions"]["http"]["routePrefix"], "")
        self.assertIn("azure-functions==", requirements)
        self.assertIn("fastapi==", requirements)
        self.assertIn("cryptography==", requirements)
        self.assertNotIn("uvicorn", requirements.lower())
        self.assertIn("local.settings.json", funcignore)
        self.assertIn("tests", funcignore)
        self.assertIn("OneDeploy --build-remote true", funcignore)

    def test_one_deploy_source_package_is_reproducible_and_closes_first_party_imports(
        self,
    ) -> None:
        builder = AZURE_HOST_ROOT / "build_package.py"
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            first_package = temporary_root / "first.zip"
            second_package = temporary_root / "second.zip"

            for output in (first_package, second_package):
                subprocess.run(
                    [sys.executable, str(builder), "--output", str(output)],
                    cwd=temporary_root,
                    check=True,
                    capture_output=True,
                    text=True,
                )

            self.assertEqual(
                first_package.read_bytes(),
                second_package.read_bytes(),
            )
            builder_spec = importlib.util.spec_from_file_location(
                "nac_bff_build_package_test", builder
            )
            self.assertIsNotNone(builder_spec)
            assert builder_spec is not None and builder_spec.loader is not None
            builder_module = importlib.util.module_from_spec(builder_spec)
            builder_spec.loader.exec_module(builder_module)
            self.assertEqual(
                builder_module.validate_package(first_package.read_bytes()), []
            )

            with zipfile.ZipFile(first_package) as package:
                names = set(package.namelist())
                manifest = json.loads(package.read("package-manifest.json"))
                packaged_files = {
                    item["path"]: package.read(item["path"])
                    for item in manifest["files"]
                }
                extracted_root = temporary_root / "extracted"
                package.extractall(extracted_root)

            self.assertIn("function_app.py", names)
            self.assertIn("nac_bff/composition.py", names)
            self.assertIn("nac_m365_graph/auth.py", names)
            self.assertIn("nac_mvp_test_environment.py", names)
            self.assertIn("bpmn/immobilienkaufvertrag.bpmn", names)
            self.assertEqual(
                hashlib.sha256(
                    packaged_files["bpmn/immobilienkaufvertrag.bpmn"]
                ).hexdigest(),
                CANONICAL_BPMN_SHA256,
            )
            self.assertEqual(
                manifest["deployment"],
                {
                    "technology": "oneDeploy",
                    "remoteBuildRequired": True,
                    "remoteBuildFlag": "--build-remote true",
                    "sourcePackage": True,
                },
            )
            self.assertFalse(any(name.startswith("src/") for name in names))
            self.assertFalse(any("__pycache__" in name for name in names))
            self.assertFalse(any(name.endswith(".pyc") for name in names))
            self.assertEqual(
                {item["path"] for item in manifest["files"]},
                names - {"package-manifest.json"},
            )
            for item in manifest["files"]:
                self.assertEqual(
                    item["sha256"],
                    hashlib.sha256(packaged_files[item["path"]]).hexdigest(),
                )
            self.assertNotIn(
                "sys.path", packaged_files["function_app.py"].decode("utf-8")
            )

            import_check = r"""
import importlib
from pathlib import Path
import sys
import types

package_root = Path(sys.argv[1]).resolve()
repo_src = Path(sys.argv[2]).resolve()
sys.path[:] = [
    entry
    for entry in sys.path
    if not entry or Path(entry).resolve() != repo_src
]
assert repo_src not in (Path(entry).resolve() for entry in sys.path if entry)
sys.path.insert(0, str(package_root))

import nac_bff
import nac_bff.composition as composition
from nac_bff.bpmn_asset import CanonicalBpmnAssetFilePort
import nac_m365_graph
import nac_m365_graph.auth
import nac_mvp_test_environment

asset = CanonicalBpmnAssetFilePort().read_canonical_bpmn()
assert asset.model_key == "Process_immobilienkaufvertrag"
assert asset.sha256 == "02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0"

for module in (
    nac_bff,
    composition,
    nac_m365_graph,
    nac_m365_graph.auth,
    nac_mvp_test_environment,
):
    assert package_root in Path(module.__file__).resolve().parents

sentinel = object()
captured = {}
composition.create_app_from_env = lambda: sentinel

class AuthLevel:
    ANONYMOUS = object()

class AsgiFunctionApp:
    def __init__(self, *, app, http_auth_level):
        captured["app"] = app
        captured["http_auth_level"] = http_auth_level

azure = types.ModuleType("azure")
functions = types.ModuleType("azure.functions")
functions.AuthLevel = AuthLevel
functions.AsgiFunctionApp = AsgiFunctionApp
azure.functions = functions
sys.modules["azure"] = azure
sys.modules["azure.functions"] = functions

function_app = importlib.import_module("function_app")
assert Path(function_app.__file__).resolve().parent == package_root
assert captured == {
    "app": sentinel,
    "http_auth_level": AuthLevel.ANONYMOUS,
}
"""
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    import_check,
                    str(extracted_root),
                    str(SRC_ROOT),
                ],
                cwd=temporary_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                completed.returncode,
                0,
                msg=completed.stderr or completed.stdout,
            )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
