from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class FakeFunctionContext:
    def __init__(self, *, request_url: str, method: str = "GET") -> None:
        self._request_url = request_url
        self._method = method

    def RequestURL(self) -> str:  # noqa: N802 - FDK API shape
        return self._request_url

    def Method(self) -> str:  # noqa: N802 - FDK API shape
        return self._method

    def Headers(self) -> dict[str, str]:  # noqa: N802 - FDK API shape
        return {"fn-http-method": self._method, "fn-http-request-url": self._request_url}


class FailingBody:
    def read(self) -> bytes:
        raise AssertionError("GET/HEAD-only adapter must not read rejected request bodies")

    def getvalue(self) -> bytes:
        raise AssertionError("GET/HEAD-only adapter must not copy rejected request bodies")


class OCIFunctionsAdapterTests(unittest.TestCase):
    def read(self, path: str) -> str:
        file_path = REPO_ROOT / path
        if not file_path.exists():
            raise AssertionError(f"{path} is missing")
        return file_path.read_text(encoding="utf-8")

    def build_spec_step_command(self, step_name: str) -> str:
        build_spec = self.read("deploy/functions/nac-app/build_spec.yaml")
        marker = f'    name: "{step_name}"'
        step_start = build_spec.index(marker)
        command_start = build_spec.index("    command: |\n", step_start) + len("    command: |\n")
        next_step = build_spec.find("\n  - type:", command_start)
        if next_step == -1:
            next_step = build_spec.find("\noutputArtifacts:", command_start)
        return textwrap.dedent(build_spec[command_start:next_step])

    def test_function_packaging_declares_python_fdk_without_base_dependency(self) -> None:
        func_yaml = self.read("deploy/functions/nac-app/func.yaml")
        func_py = self.read("deploy/functions/nac-app/func.py")
        dockerfile = self.read("deploy/functions/nac-app/Dockerfile")
        requirements = self.read("deploy/functions/nac-app/requirements.txt")
        build_spec = self.read("deploy/functions/nac-app/build_spec.yaml")
        pyproject = self.read("pyproject.toml")

        self.assertIn("runtime: python", func_yaml)
        self.assertIn("entrypoint: /python/bin/fdk /function/func.py handler", func_yaml)
        self.assertIn("from nac_web.oci_functions import handler", func_py)
        self.assertIn("COPY src /function/src", dockerfile)
        self.assertIn("COPY deploy/functions/nac-app/func.py /function/func.py", dockerfile)
        self.assertIn("ENV PYTHONPATH=/python:/function/src", dockerfile)
        self.assertIn("fdk", requirements)
        self.assertIn("exportedVariables:", build_spec)
        self.assertIn("BUILDRUN_HASH", build_spec)
        self.assertIn("resolve_nac_source_dir()", build_spec)
        self.assertIn('for candidate in "${OCI_PRIMARY_SOURCE_DIR:-}" nac .; do', build_spec)
        self.assertIn('test -d "$candidate/tests"', build_spec)
        self.assertIn('test -f "$candidate/deploy/functions/nac-app/Dockerfile"', build_spec)
        self.assertIn('cd "$NAC_SOURCE_DIR"', build_spec)
        self.assertIn('echo "Using NaC source directory: $NAC_SOURCE_DIR"', build_spec)
        self.assertIn('test -f tests/test_oci_functions_adapter.py', build_spec)
        self.assertIn("python3 -m unittest discover -s tests -p 'test_oci_functions_adapter.py' -v", build_spec)
        self.assertNotIn("python3 -m unittest tests.test_oci_functions_adapter -v", build_spec)
        self.assertIn("docker build -f deploy/functions/nac-app/Dockerfile -t nac-app .", build_spec)
        self.assertIn("type: DOCKER_IMAGE", build_spec)
        self.assertIn("location: nac-app", build_spec)
        self.assertIn("dependencies = []", pyproject)

        forbidden_terms = [
            "BEGIN PRIVATE KEY",
            "client_secret",
            "password=",
            "key_file",
            "ocid1.user",
        ]
        for content in (func_yaml, func_py, dockerfile, requirements, build_spec):
            for term in forbidden_terms:
                self.assertNotIn(term, content)

    def test_buildspec_prefers_checked_out_nac_source_when_primary_source_dir_is_unusable(self) -> None:
        command = self.build_spec_step_command("Run Functions adapter tests")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            test_dir = tmp_path / "nac" / "tests"
            test_dir.mkdir(parents=True)
            dockerfile = tmp_path / "nac" / "deploy" / "functions" / "nac-app" / "Dockerfile"
            dockerfile.parent.mkdir(parents=True)
            dockerfile.write_text("FROM scratch\n", encoding="utf-8")
            (test_dir / "test_oci_functions_adapter.py").write_text(
                "\n".join(
                    [
                        "import unittest",
                        "",
                        "class SmokeTests(unittest.TestCase):",
                        "    def test_buildspec_source_dir_resolution(self) -> None:",
                        "        self.assertTrue(True)",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["OCI_PRIMARY_SOURCE_DIR"] = str(tmp_path / "not-the-clone")

            result = subprocess.run(
                ["bash", "-lc", command],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_function_entrypoint_imports_adapter_without_external_pythonpath(self) -> None:
        function_dir = REPO_ROOT / "deploy" / "functions" / "nac-app"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)

        result = subprocess.run(
            [sys.executable, "-c", "import func; print(callable(func.handler))"],
            cwd=function_dir,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("True", result.stdout)

    def test_function_entrypoint_handles_shallow_container_path(self) -> None:
        function_dir = REPO_ROOT / "deploy" / "functions" / "nac-app"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC_ROOT)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            shutil.copy(function_dir / "func.py", tmp_path / "func.py")

            result = subprocess.run(
                [sys.executable, "-c", "import func; print(callable(func.handler))"],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("True", result.stdout)

    def test_function_docker_context_excludes_local_secret_and_vcs_paths(self) -> None:
        dockerignore = self.read(".dockerignore")

        required_patterns = [
            ".git",
            ".venv",
            ".venvs",
            ".oci",
            "*.pem",
            "*.key",
            "*.tfstate",
            "*.tfvars",
            "certificate.zip",
        ]
        for pattern in required_patterns:
            self.assertIn(pattern, dockerignore)

    def test_function_image_grants_runtime_user_read_permissions(self) -> None:
        dockerfile = self.read("deploy/functions/nac-app/Dockerfile")

        self.assertIn("COPY --from=build-stage /function /function", dockerfile)
        self.assertIn("COPY --from=build-stage /python /python", dockerfile)
        self.assertIn("RUN chmod -R a+rX /function /python", dockerfile)

    def test_operations_docs_define_functions_parallel_runtime_gate(self) -> None:
        german = self.read("docs/de/operations/oci-runtime.md")
        english = self.read("docs/en/operations/oci-runtime.md")

        german_terms = [
            "OCI Functions Parallel Runtime",
            "GET/HEAD-only",
            "VM bleibt Fallback",
            "Owner Apply Approval for Apply Block J NaC OCI Functions parallel runtime",
            "keine Mandatsdaten",
            "No-SSH Functions Release",
            "OCI DevOps",
            "OCIR-Digest",
            "API-Gateway-Smoke-Test",
            "keinen Bastion- oder SSH-Zugriff",
        ]
        english_terms = [
            "OCI Functions Parallel Runtime",
            "GET/HEAD-only",
            "VM remains fallback",
            "Owner Apply Approval for Apply Block J NaC OCI Functions parallel runtime",
            "no mandate data",
            "No-SSH Functions Release",
            "OCI DevOps",
            "OCIR digest",
            "API Gateway smoke test",
            "no Bastion or SSH access",
        ]

        for term in german_terms:
            self.assertIn(term, german)
        for term in english_terms:
            self.assertIn(term, english)

    def test_dispatches_healthz_through_existing_web_contract(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        result = dispatch_oci_function_request(
            FakeFunctionContext(request_url="/healthz"),
            io.BytesIO(b""),
            repo_root=REPO_ROOT,
        )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json; charset=utf-8")
        self.assertIn(b'"status": "ok"', result.body)

    def test_dispatches_head_healthz_without_response_body(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        result = dispatch_oci_function_request(
            FakeFunctionContext(request_url="/healthz", method="HEAD"),
            FailingBody(),
            repo_root=REPO_ROOT,
        )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(result.body, b"")

    def test_dispatches_get_request_with_query_string(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        result = dispatch_oci_function_request(
            FakeFunctionContext(
                request_url="/onboarding/readiness?domain_hint=kanzlei-notariat.example",
                method="GET",
            ),
            io.BytesIO(b""),
            repo_root=REPO_ROOT,
        )

        body = result.body.decode("utf-8")
        self.assertEqual(result.status_code, 200)
        self.assertIn("kanzlei-notariat.example", body)
        self.assertIn("Keine Mandatsdaten", body)

    def test_dispatches_login_intent_api_for_function_login_page(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs.example.identity.oraclecloud.com:443",
                "NAC_OIDC_CLIENT_ID": "nac-web-app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
            },
        ):
            result = dispatch_oci_function_request(
                FakeFunctionContext(
                    request_url="/api/tenant/login-intent?tenant_hint=notariat-musterstadt",
                    method="GET",
                ),
                FailingBody(),
                repo_root=REPO_ROOT,
            )
        payload = json.loads(result.body.decode("utf-8"))

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(payload["schema_version"], "nac.oci-login-intent/v0.1")
        self.assertIn("/oauth2/v1/authorize", payload["authorization_url"])
        self.assertFalse(payload["tenant_context"]["tenant_authorized_by_hint"])

    def test_dispatches_auth_callback_without_exposing_callback_values(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        result = dispatch_oci_function_request(
            FakeFunctionContext(
                request_url="/auth/callback?code=secret-code-from-idp&state=state-secret-from-nac",
                method="GET",
            ),
            FailingBody(),
            repo_root=REPO_ROOT,
        )
        body = result.body.decode("utf-8")

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Anmeldung empfangen", body)
        self.assertIn("Rollen- und Vorgangsprüfung", body)
        self.assertIn("Arbeitsbereich bleibt geschlossen", body)
        self.assertIn("Sicherheitsprüfung offen", body)
        self.assertNotIn("secret-code-from-idp", body)
        self.assertNotIn("state-secret-from-nac", body)
        self.assertNotIn("Oracle", body)
        self.assertNotIn("OCI", body)

    def test_rejects_post_routes_in_public_function_runtime(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        result = dispatch_oci_function_request(
            FakeFunctionContext(request_url="/api/gnotkg/quote", method="POST"),
            FailingBody(),
            repo_root=REPO_ROOT,
        )

        self.assertEqual(result.status_code, 405)
        self.assertIn(b"read-only", result.body)

    def test_rejects_non_customer_safe_get_routes(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        blocked_paths = [
            "/admin/onboarding",
            "/admin/onboarding/apply-readiness?domain=myjur.de&admin_email=admin@myjur.de",
            "/bpmn/immobilienkaufvertrag/edit",
            "/api/bpmn/immobilienkaufvertrag/xml",
            "/api/tenant/domain-check?domain=myjur.de&tenant_slug=myjur",
        ]

        for path in blocked_paths:
            with self.subTest(path=path):
                result = dispatch_oci_function_request(
                    FakeFunctionContext(request_url=path, method="GET"),
                    io.BytesIO(b""),
                    repo_root=REPO_ROOT,
                )

                self.assertEqual(result.status_code, 404)
                self.assertIn(b"not exposed", result.body)


if __name__ == "__main__":
    unittest.main()
