from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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

    def test_function_packaging_declares_python_fdk_without_base_dependency(self) -> None:
        func_yaml = self.read("deploy/functions/nac-app/func.yaml")
        func_py = self.read("deploy/functions/nac-app/func.py")
        dockerfile = self.read("deploy/functions/nac-app/Dockerfile")
        requirements = self.read("deploy/functions/nac-app/requirements.txt")
        pyproject = self.read("pyproject.toml")

        self.assertIn("runtime: python", func_yaml)
        self.assertIn("entrypoint: /python/bin/fdk /function/func.py handler", func_yaml)
        self.assertIn("from nac_web.oci_functions import handler", func_py)
        self.assertIn("COPY src /function/src", dockerfile)
        self.assertIn("COPY deploy/functions/nac-app/func.py /function/func.py", dockerfile)
        self.assertIn("ENV PYTHONPATH=/python:/function/src", dockerfile)
        self.assertIn("fdk", requirements)
        self.assertIn("dependencies = []", pyproject)

        forbidden_terms = [
            "BEGIN PRIVATE KEY",
            "client_secret",
            "password=",
            "key_file",
            "ocid1.user",
        ]
        for content in (func_yaml, func_py, dockerfile, requirements):
            for term in forbidden_terms:
                self.assertNotIn(term, content)

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
        ]
        english_terms = [
            "OCI Functions Parallel Runtime",
            "GET/HEAD-only",
            "VM remains fallback",
            "Owner Apply Approval for Apply Block J NaC OCI Functions parallel runtime",
            "no mandate data",
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
