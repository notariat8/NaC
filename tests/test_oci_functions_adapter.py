from __future__ import annotations

import base64
import io
import json
import hashlib
import logging
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


def bash_executable() -> str:
    candidates = [shutil.which("bash")]
    if os.name == "nt":
        candidates.extend(
            [
                r"C:\Program Files\Git\bin\bash.exe",
                r"C:\Program Files\Git\usr\bin\bash.exe",
            ]
        )

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)

    return "bash"


def git_bash_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if drive:
        return f"/{drive}/{resolved.relative_to(resolved.anchor).as_posix()}"
    return resolved.as_posix()


def add_python3_shim_for_git_bash(env: dict[str, str], parent: Path) -> dict[str, str]:
    if os.name != "nt":
        return env

    shim_dir = parent / "python-shim-bin"
    shim_dir.mkdir(exist_ok=True)
    shim = shim_dir / "python3"
    shim.write_text(
        f'#!/usr/bin/env bash\nexec "{git_bash_path(Path(sys.executable))}" "$@"\n',
        encoding="utf-8",
    )
    os.chmod(shim, 0o755)
    env["PATH"] = f"{git_bash_path(shim_dir)}:{env.get('PATH', '')}"
    return env


class FakeFunctionContext:
    def __init__(self, *, request_url: str, method: str = "GET", headers: dict[str, str] | None = None) -> None:
        self._request_url = request_url
        self._method = method
        self._headers = dict(headers or {})

    def RequestURL(self) -> str:  # noqa: N802 - FDK API shape
        return self._request_url

    def Method(self) -> str:  # noqa: N802 - FDK API shape
        return self._method

    def Headers(self) -> dict[str, str]:  # noqa: N802 - FDK API shape
        headers = {"fn-http-method": self._method, "fn-http-request-url": self._request_url}
        headers.update(self._headers)
        return headers


class FailingBody:
    def read(self) -> bytes:
        raise AssertionError("GET/HEAD-only adapter must not read rejected request bodies")

    def getvalue(self) -> bytes:
        raise AssertionError("GET/HEAD-only adapter must not copy rejected request bodies")


def session_cookie_payload(cookie_header: str) -> dict[str, object]:
    cookie_value = cookie_header.split("=", 1)[1]
    payload_part = cookie_value.split(".", 1)[0]
    padding = "=" * (-len(payload_part) % 4)
    return json.loads(base64.urlsafe_b64decode(f"{payload_part}{padding}".encode("ascii")).decode("utf-8"))


class OCIFunctionsAdapterTests(unittest.TestCase):
    def read(self, path: str) -> str:
        file_path = REPO_ROOT / path
        if not file_path.exists():
            raise AssertionError(f"{path} is missing")
        return file_path.read_text(encoding="utf-8")

    def build_spec_step_command(
        self,
        step_name: str,
        build_spec_path: str = "deploy/functions/nac-app/build_spec.yaml",
    ) -> str:
        build_spec = self.read(build_spec_path)
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
        self.assertTrue(
            (
                REPO_ROOT
                / "src"
                / "nac_runtime"
                / "demo_data"
                / "notarkammer-first-immobilienkaufvertrag.metadata.json"
            ).is_file()
        )
        self.assertIn("COPY deploy/functions/nac-app/func.py /function/func.py", dockerfile)
        self.assertIn("ENV PYTHONPATH=/python:/function/src", dockerfile)
        self.assertIn("fdk", requirements)
        self.assertIn("exportedVariables:", build_spec)
        self.assertIn("BUILDRUN_HASH", build_spec)
        self.assertIn("NAC_RELEASE_COMMIT", build_spec)
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
        self.assertIn("[tool.setuptools.package-data]", pyproject)
        self.assertIn('nac_runtime = ["demo_data/*.json"]', pyproject)
        self.assertNotIn("tests/fixtures", self.read("src/nac_web/server.py"))

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

    def create_minimal_git_checkout(self, parent: Path) -> tuple[Path, str]:
        checkout = parent / "nac"
        test_dir = checkout / "tests"
        test_dir.mkdir(parents=True)
        dockerfile = checkout / "deploy" / "functions" / "nac-app" / "Dockerfile"
        dockerfile.parent.mkdir(parents=True)
        dockerfile.write_text("FROM scratch\n", encoding="utf-8")
        public_dockerfile = checkout / "deploy" / "functions" / "nac-public-app" / "Dockerfile"
        public_dockerfile.parent.mkdir(parents=True)
        public_dockerfile.write_text("FROM scratch\n", encoding="utf-8")
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
        subprocess.run(["git", "init"], cwd=checkout, check=True, capture_output=True, text=True)
        subprocess.run(["git", "add", "."], cwd=checkout, check=True, capture_output=True, text=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=NaC Test",
                "-c",
                "user.email=nac@example.invalid",
                "commit",
                "-m",
                "initial test checkout",
            ],
            cwd=checkout,
            check=True,
            capture_output=True,
            text=True,
        )
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
        return checkout, commit

    def build_spec_fixture_env(self, checkout: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["OCI_PRIMARY_SOURCE_DIR"] = str(checkout)
        return add_python3_shim_for_git_bash(env, checkout.parent)

    def test_buildspec_requires_owner_approved_release_commit(self) -> None:
        command = self.build_spec_step_command("Prepare immutable image tag")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            checkout, _ = self.create_minimal_git_checkout(tmp_path)
            env = self.build_spec_fixture_env(checkout)
            env.pop("NAC_RELEASE_COMMIT", None)
            env["OCI_PRIMARY_SOURCE_COMMIT_HASH"] = "f" * 40

            result = subprocess.run(
                [bash_executable(), "-lc", command],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NAC_RELEASE_COMMIT", result.stderr + result.stdout)

    def test_buildspec_checks_out_owner_approved_release_commit(self) -> None:
        command = self.build_spec_step_command("Prepare immutable image tag")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            checkout, commit = self.create_minimal_git_checkout(tmp_path)
            env = self.build_spec_fixture_env(checkout)
            env["NAC_RELEASE_COMMIT"] = commit
            env["OCI_PRIMARY_SOURCE_COMMIT_HASH"] = "f" * 40

            result = subprocess.run(
                [bash_executable(), "-lc", command],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            active_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(active_commit, commit)
        self.assertIn(commit[:12], result.stdout)

    def test_buildspec_rejects_unavailable_release_commit(self) -> None:
        command = self.build_spec_step_command("Prepare immutable image tag")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            checkout, _ = self.create_minimal_git_checkout(tmp_path)
            env = self.build_spec_fixture_env(checkout)
            env["NAC_RELEASE_COMMIT"] = "0" * 40

            result = subprocess.run(
                [bash_executable(), "-lc", command],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Owner-approved release commit is not available", result.stderr + result.stdout)

    def test_function_adapter_suppresses_provider_sdk_debug_logs(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        logger_names = ("oci", "oci.circuit_breaker", "urllib3", "urllib3.connectionpool")
        previous_levels = {name: logging.getLogger(name).level for name in logger_names}
        try:
            for name in logger_names:
                logging.getLogger(name).setLevel(logging.DEBUG)

            dispatch_oci_function_request(FakeFunctionContext(request_url="/healthz"))

            for name in logger_names:
                self.assertGreaterEqual(logging.getLogger(name).getEffectiveLevel(), logging.WARNING)
        finally:
            for name, level in previous_levels.items():
                logging.getLogger(name).setLevel(level)

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
            env = add_python3_shim_for_git_bash(env, tmp_path)

            result = subprocess.run(
                [bash_executable(), "-lc", command],
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

    def test_public_get_function_packaging_is_lean_and_state_free(self) -> None:
        func_yaml = self.read("deploy/functions/nac-public-app/func.yaml")
        func_py = self.read("deploy/functions/nac-public-app/func.py")
        dockerfile = self.read("deploy/functions/nac-public-app/Dockerfile")
        requirements = self.read("deploy/functions/nac-public-app/requirements.txt")
        adapter = self.read("src/nac_web/oci_public_functions.py")

        self.assertIn("name: nac-public-app", func_yaml)
        self.assertIn("runtime: python", func_yaml)
        self.assertIn("entrypoint: /python/bin/fdk /function/func.py handler", func_yaml)
        self.assertIn("from nac_web.oci_public_functions import handler", func_py)
        self.assertIn("dispatch_minimal_public_get_request", adapter)
        self.assertNotIn("from nac_web.oci_functions import", adapter)
        self.assertNotIn("dispatch_oci_function_request", adapter)
        self.assertNotIn("NaCLocalWebApp", adapter)
        self.assertIn("COPY src /function/src", dockerfile)
        self.assertIn("COPY deploy/functions/nac-public-app/func.py /function/func.py", dockerfile)
        self.assertIn("COPY deploy/functions/nac-public-app/requirements.txt /function/requirements.txt", dockerfile)
        self.assertIn("ENV PYTHONPATH=/python:/function/src", dockerfile)
        self.assertIn("fdk", requirements)
        self.assertIn("oci>=2,<3", requirements)
        self.assertNotIn("oracledb", requirements)

        forbidden_terms = [
            "BEGIN PRIVATE KEY",
            "client_secret",
            "password=",
            "key_file",
            "ocid1.user",
            "NAC_ATP_",
            "NAC_ONBOARDING_STORE",
        ]
        for content in (func_yaml, func_py, dockerfile, requirements):
            for term in forbidden_terms:
                self.assertNotIn(term, content)

    def test_public_get_buildspec_builds_only_lean_public_image(self) -> None:
        build_spec = self.read("deploy/functions/nac-public-app/build_spec.yaml")

        self.assertIn("exportedVariables:", build_spec)
        self.assertIn("BUILDRUN_HASH", build_spec)
        self.assertIn("NAC_RELEASE_COMMIT", build_spec)
        self.assertIn("resolve_nac_source_dir()", build_spec)
        self.assertIn('test -f "$candidate/deploy/functions/nac-public-app/Dockerfile"', build_spec)
        self.assertIn('cd "$NAC_SOURCE_DIR"', build_spec)
        self.assertIn('test -f tests/test_oci_functions_adapter.py', build_spec)
        self.assertIn("python3 -m unittest discover -s tests -p 'test_oci_functions_adapter.py' -v", build_spec)
        self.assertIn("docker build -f deploy/functions/nac-public-app/Dockerfile -t nac-public-app .", build_spec)
        self.assertIn("name: nac_public_app_image", build_spec)
        self.assertIn("type: DOCKER_IMAGE", build_spec)
        self.assertIn("location: nac-public-app", build_spec)
        self.assertNotIn("nac_app_image", build_spec)

        forbidden_terms = [
            "BEGIN PRIVATE KEY",
            "client_secret",
            "password=",
            "key_file",
            "ocid1.user",
            "NAC_ATP_",
            "NAC_ONBOARDING_STORE",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, build_spec)

    def test_public_get_buildspec_checks_out_owner_approved_release_commit(self) -> None:
        command = self.build_spec_step_command(
            "Prepare immutable public image tag",
            "deploy/functions/nac-public-app/build_spec.yaml",
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            checkout, commit = self.create_minimal_git_checkout(tmp_path)
            env = self.build_spec_fixture_env(checkout)
            env["NAC_RELEASE_COMMIT"] = commit
            env["OCI_PRIMARY_SOURCE_COMMIT_HASH"] = "f" * 40

            result = subprocess.run(
                [bash_executable(), "-lc", command],
                cwd=tmp_path,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            active_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(active_commit, commit)
        self.assertIn(commit[:12], result.stdout)

    def test_public_get_function_entrypoint_imports_adapter_without_external_pythonpath(self) -> None:
        function_dir = REPO_ROOT / "deploy" / "functions" / "nac-public-app"
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
            "NAC_RELEASE_COMMIT",
            "commit-info",
            "pinnt den Build-Checkout nicht",
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
            "NAC_RELEASE_COMMIT",
            "commit-info",
            "does not pin the build",
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

    def test_minimal_public_get_runtime_serves_healthz_without_webapp_boot(self) -> None:
        from nac_web.oci_public_functions import dispatch_oci_public_function_request

        result = dispatch_oci_public_function_request(
            FakeFunctionContext(request_url="/healthz", method="GET"),
            FailingBody(),
            repo_root=REPO_ROOT,
        )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(result.body.decode("utf-8")), {"status": "ok"})

    def test_minimal_public_get_runtime_serves_customer_readiness_without_vendor_copy(self) -> None:
        from nac_web.oci_public_functions import dispatch_oci_public_function_request

        result = dispatch_oci_public_function_request(
            FakeFunctionContext(
                request_url=(
                    "/onboarding/readiness?audience=customer&domain_hint=myjur.de"
                    "&tenant_slug=myjur&admin_email=ofunk%40myjur.de"
                ),
                method="GET",
            ),
            FailingBody(),
            repo_root=REPO_ROOT,
        )
        body = result.body.decode("utf-8")

        self.assertEqual(result.status_code, 200)
        self.assertIn("notariat8", body)
        self.assertIn("myjur.de", body)
        self.assertIn("_nac.myjur.de", body)
        self.assertIn("Keine Mandatsdaten", body)
        self.assertNotIn("Oracle", body)
        self.assertNotIn("OCI", body)

    def test_minimal_public_get_runtime_marks_missing_customer_email_as_open(self) -> None:
        from nac_web.oci_public_functions import dispatch_oci_public_function_request

        result = dispatch_oci_public_function_request(
            FakeFunctionContext(
                request_url="/onboarding/readiness?audience=customer&domain_hint=myjur.de&tenant_slug=myjur",
                method="GET",
            ),
            FailingBody(),
            repo_root=REPO_ROOT,
        )
        body = result.body.decode("utf-8")

        self.assertEqual(result.status_code, 200)
        self.assertIn("E-Mail offen", body)
        self.assertNotIn("<strong>Status:</strong> blockiert", body)

    def test_minimal_public_get_runtime_serves_signed_login_intent(self) -> None:
        from nac_web.oci_public_functions import dispatch_oci_public_function_request

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                "NAC_OIDC_CLIENT_ID": "notariat8_nac_app",
                "NAC_OIDC_REDIRECT_URI": "https://app.notariat8.de/auth/callback",
                "NAC_OIDC_STATE_SIGNING_KEY": "test-signing-key",
            },
        ):
            result = dispatch_oci_public_function_request(
                FakeFunctionContext(
                    request_url="/api/tenant/login-intent?tenant_hint=myjur",
                    method="GET",
                ),
                FailingBody(),
                repo_root=REPO_ROOT,
            )
        payload = json.loads(result.body.decode("utf-8"))

        self.assertEqual(result.status_code, 200)
        self.assertEqual(payload["schema_version"], "nac.oci-login-intent/v0.1")
        self.assertEqual(payload["tenant_context"]["tenant_hint"], "myjur")
        self.assertEqual(payload["state_binding"]["status"], "signed")
        self.assertFalse(payload["guardrails"]["contains_credentials"])

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

    def test_public_customer_get_pages_do_not_initialize_onboarding_store(self) -> None:
        from nac_identity.customer_onboarding import build_dns_check_result
        from nac_web.oci_functions import dispatch_oci_function_request

        dns_result = build_dns_check_result(
            expected_name="_nac.kanzlei-notariat.example",
            expected_value="nac-domain-verification=test-token",
            observed_name="_nac.kanzlei-notariat.example",
            observed_values=["nac-domain-verification=test-token"],
        )
        public_routes = [
            "/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example",
            (
                "/onboarding/dns-check?audience=customer&domain=kanzlei-notariat.example"
                "&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example"
            ),
        ]

        with patch(
            "nac_web.oci_functions.build_onboarding_request_store_from_env",
            side_effect=AssertionError("public GET route must not initialize onboarding store"),
        ), patch("nac_web.server.build_live_dns_check_result", return_value=dns_result):
            for route in public_routes:
                with self.subTest(route=route):
                    result = dispatch_oci_function_request(
                        FakeFunctionContext(request_url=route, method="GET"),
                        FailingBody(),
                        repo_root=REPO_ROOT,
                    )

                    self.assertEqual(result.status_code, 200)

    def test_dispatches_login_intent_api_for_function_login_page(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        with patch.dict(
            os.environ,
            {
                "NAC_OCI_IDENTITY_DOMAIN_URL": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
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

    def test_dispatches_public_login_page_without_visible_json_intent_link(self) -> None:
        from nac_web.oci_public_functions import dispatch_oci_public_function_request

        result = dispatch_oci_public_function_request(
            FakeFunctionContext(
                request_url="/login?tenant_hint=notariat-musterstadt",
                method="GET",
            ),
            FailingBody(),
            repo_root=REPO_ROOT,
        )
        body = result.body.decode("utf-8")

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("notariat8 Anmeldung", body)
        self.assertIn("Anmeldung starten", body)
        self.assertIn("fetch(", body)
        self.assertIn("window.location.assign", body)
        self.assertIn("/api/tenant/login-intent?tenant_hint=notariat-musterstadt", body)
        self.assertNotIn('href="/api/tenant/login-intent', body)
        self.assertNotIn("Oracle", body)
        self.assertNotIn("OCI", body)

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
        self.assertIn("Anmeldung und Berechtigung", body)
        self.assertIn("Arbeitsbereich bleibt geschlossen", body)
        self.assertIn("Sicherheitsprüfung offen", body)
        self.assertNotIn("secret-code-from-idp", body)
        self.assertNotIn("state-secret-from-nac", body)
        self.assertNotIn("Oracle", body)
        self.assertNotIn("OCI", body)

    def test_dispatches_workspace_as_protected_stateful_get_route(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary
        from nac_web.oci_functions import dispatch_oci_function_request

        session = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256("nonce-from-id-token".encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                    "aud": "notariat8_nac_app",
                    "nonce": "nonce-from-id-token",
                    "groups": ["nac-tenant-admin"],
                    "email": "admin@example.test",
                },
            },
            expected_issuer="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            expected_audience="notariat8_nac_app",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = session["session"]["set_cookie"].split(";", 1)[0]

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            result = dispatch_oci_function_request(
                FakeFunctionContext(
                    request_url="/workspace",
                    method="GET",
                    headers={
                        "Cookie": cookie_header,
                        "X-NaC-Role": "nac-tenant-admin",
                        "X-NaC-Tenant-Bound": "true",
                        "X-NaC-Case-Bound": "true",
                        "X-NaC-Purpose-Bound": "true",
                        "X-NaC-Case-Id": "case-secret-1",
                        "X-NaC-Tenant-Hint": "myjur",
                    },
                ),
                FailingBody(),
                repo_root=REPO_ROOT,
            )
        body = result.body.decode("utf-8")

        self.assertEqual(result.status_code, 401)
        self.assertEqual(result.headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("notariat8 Anmeldung erforderlich", body)
        self.assertIn("Sitzung nicht geprüft", body)
        self.assertIn("Keine Mandatsdaten geladen", body)
        self.assertNotIn(cookie_header, body)
        self.assertNotIn("case-secret-1", body)
        self.assertNotIn("myjur", body)
        self.assertNotIn("admin@example.test", body)
        self.assertNotIn("notariat8_nac_app", body)
        self.assertNotIn("idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com", body)
        self.assertNotIn("Oracle", body)
        self.assertNotIn("OCI", body)

    def test_stateful_auth_routes_initialize_session_store_from_env(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        class DummySessionStore:
            def get_session_record(self, _session_id: str) -> None:
                return None

        with patch("nac_web.oci_functions.build_session_store_from_env", return_value=DummySessionStore()) as factory:
            result = dispatch_oci_function_request(
                FakeFunctionContext(request_url="/workspace", method="GET"),
                FailingBody(),
                repo_root=REPO_ROOT,
            )

        self.assertEqual(result.status_code, 401)
        factory.assert_called_once_with()

    def test_first_matter_status_route_initializes_session_store_from_env(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        class DummySessionStore:
            def get_session_record(self, _session_id: str) -> None:
                return None

        with patch("nac_web.oci_functions.build_session_store_from_env", return_value=DummySessionStore()) as factory:
            result = dispatch_oci_function_request(
                FakeFunctionContext(request_url="/workspace/immobilienkaufvertrag", method="GET"),
                FailingBody(),
                repo_root=REPO_ROOT,
            )

        self.assertEqual(result.status_code, 401)
        self.assertIn(b"notariat8 Anmeldung erforderlich", result.body)
        factory.assert_called_once_with()

    def test_first_matter_status_route_uses_packaged_runtime_source_without_repo_tests(self) -> None:
        from nac_identity.oidc_session import evaluate_oidc_session_boundary
        from nac_identity.session_store import MappingSessionStoreAdapter
        from nac_web.oci_functions import dispatch_oci_function_request

        session = evaluate_oidc_session_boundary(
            state_validation={
                "status": "valid",
                "tenant_hint": "myjur",
                "nonce_bound": True,
                "nonce_hash": hashlib.sha256("nonce-from-id-token".encode("utf-8")).hexdigest(),
            },
            token_exchange_result={
                "status": "verified",
                "claims": {
                    "iss": "https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
                    "aud": "notariat8_nac_app",
                    "nonce": "nonce-from-id-token",
                    "groups": ["nac-notary"],
                    "email": "notar@example.test",
                },
            },
            expected_issuer="https://idcs-c98667d9d2e74ab288ad6bcd0830c774.identity.oraclecloud.com",
            expected_audience="notariat8_nac_app",
            required_role="nac-notary",
            session_signing_key="unit-test-session-signing-key",
            now=1_800_000_000,
            session_ttl_seconds=600,
        )
        cookie_header = session["session"]["set_cookie"].split(";", 1)[0]
        payload = session_cookie_payload(cookie_header)
        session_store = MappingSessionStoreAdapter(
            {
                str(payload["sid"]): {
                    "schema_version": "nac.server-session/v0.1",
                    "session_id": payload["sid"],
                    "issued_at": payload["iat"],
                    "expires_at": payload["exp"],
                    "revoked_at": None,
                    "audit_event_id": "audit-event-secret",
                    "contains_credentials": False,
                    "tokens_stored": False,
                    "claims_stored": False,
                    "tenant_bound": True,
                    "subject_bound": True,
                    "role_bound": True,
                    "case_bound": True,
                    "purpose_bound": True,
                }
            }
        )

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"},
            clear=False,
        ), patch("nac_web.oci_functions.build_session_store_from_env", return_value=session_store):
            result = dispatch_oci_function_request(
                FakeFunctionContext(
                    request_url="/workspace/immobilienkaufvertrag",
                    method="GET",
                    headers={"Cookie": cookie_header},
                ),
                FailingBody(),
                repo_root=Path(tmp),
            )
        body = result.body.decode("utf-8")

        self.assertEqual(result.status_code, 200)
        self.assertIn("Immobilienkaufvertrag Status", body)
        self.assertIn("Vorgangsstatus ohne Mandatsdaten", body)
        self.assertIn("Keine Mandatsdaten geladen", body)
        self.assertNotIn("tests/fixtures", body)
        self.assertNotIn("notar@example.test", body)
        self.assertNotIn("Oracle", body)
        self.assertNotIn("OCI", body)

    def test_dispatches_workspace_fail_closed_without_cookie(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        with patch.dict(os.environ, {"NAC_SESSION_SIGNING_KEY": "unit-test-session-signing-key"}, clear=False):
            result = dispatch_oci_function_request(
                FakeFunctionContext(request_url="/workspace", method="GET"),
                FailingBody(),
                repo_root=REPO_ROOT,
            )
        body = result.body.decode("utf-8")

        self.assertEqual(result.status_code, 401)
        self.assertEqual(result.headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("notariat8 Anmeldung erforderlich", body)
        self.assertIn("Keine Mandatsdaten geladen", body)
        self.assertNotIn("Oracle", body)
        self.assertNotIn("OCI", body)

    def test_public_function_does_not_expose_auth_callback(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request
        from nac_web.oci_public_functions import dispatch_oci_public_function_request

        request = FakeFunctionContext(
            request_url="/auth/callback?code=secret-code-from-idp&state=state-secret-from-nac",
            method="GET",
        )

        public_result = dispatch_oci_public_function_request(request, repo_root=REPO_ROOT)
        stateful_result = dispatch_oci_function_request(request, repo_root=REPO_ROOT)

        self.assertEqual(public_result.status_code, 404)
        self.assertNotIn(b"secret-code-from-idp", public_result.body)
        self.assertNotIn(b"state-secret-from-nac", public_result.body)
        self.assertEqual(stateful_result.status_code, 200)
        self.assertIn(b"Anmeldung empfangen", stateful_result.body)
        self.assertNotIn(b"secret-code-from-idp", stateful_result.body)
        self.assertNotIn(b"state-secret-from-nac", stateful_result.body)

    def test_rejects_post_routes_in_public_function_runtime(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        result = dispatch_oci_function_request(
            FakeFunctionContext(request_url="/api/gnotkg/quote", method="POST"),
            FailingBody(),
            repo_root=REPO_ROOT,
        )

        self.assertEqual(result.status_code, 405)
        self.assertIn(b"read-only", result.body)

    def test_rejects_admin_review_post_in_public_function_runtime(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        result = dispatch_oci_function_request(
            FakeFunctionContext(request_url="/admin/onboarding/review", method="POST"),
            io.BytesIO(b"request_id=onr_myjur_20260611_182453&decision=approve"),
            repo_root=REPO_ROOT,
        )

        self.assertEqual(result.status_code, 405)
        self.assertEqual(result.headers["Content-Type"], "application/json; charset=utf-8")
        self.assertIn(b"read-only", result.body)
        self.assertNotIn(b"onr_myjur_20260611_182453", result.body)
        self.assertNotIn(b"client_secret", result.body.lower())

    def test_allows_customer_onboarding_request_post_without_exposing_other_writes(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        result = dispatch_oci_function_request(
            FakeFunctionContext(request_url="/onboarding/requests", method="POST"),
            io.BytesIO(
                b"domain=kanzlei-notariat.example"
                b"&tenant_slug=kanzlei-notariat"
                b"&admin_email=admin%40kanzlei-notariat.example"
            ),
            repo_root=REPO_ROOT,
        )

        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.headers["Content-Type"], "application/json; charset=utf-8")
        self.assertIn(b"onboarding_request_store_disabled", result.body)
        self.assertNotIn(b"client_secret", result.body.lower())
        self.assertNotIn(b"private_key", result.body.lower())

    def test_public_get_runtime_rejects_stateful_onboarding_routes_without_store(self) -> None:
        from nac_web.oci_public_functions import dispatch_oci_public_function_request

        with patch(
            "nac_web.oci_functions.build_onboarding_request_store_from_env",
            side_effect=AssertionError("public GET runtime must never initialize onboarding store"),
        ):
            post_result = dispatch_oci_public_function_request(
                FakeFunctionContext(request_url="/onboarding/requests", method="POST"),
                FailingBody(),
                repo_root=REPO_ROOT,
            )
            status_result = dispatch_oci_public_function_request(
                FakeFunctionContext(
                    request_url="/onboarding/requests/onr_myjur_20260610_111500?audience=customer",
                    method="GET",
                ),
                FailingBody(),
                repo_root=REPO_ROOT,
            )

        self.assertEqual(post_result.status_code, 405)
        self.assertIn(b"read-only", post_result.body)
        self.assertEqual(status_result.status_code, 404)
        self.assertIn(b"not exposed", status_result.body)

    def test_public_get_runtime_does_not_expose_workspace(self) -> None:
        from nac_web.oci_public_functions import dispatch_oci_public_function_request

        result = dispatch_oci_public_function_request(
            FakeFunctionContext(request_url="/workspace", method="GET"),
            FailingBody(),
            repo_root=REPO_ROOT,
        )

        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.headers["Content-Type"], "application/json; charset=utf-8")
        self.assertIn(b"not exposed", result.body)
        self.assertNotIn(b"workspace", result.body.lower())
        self.assertNotIn(b"session", result.body.lower())

    def test_configured_store_accepts_customer_onboarding_request_post(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        class FakeStore:
            def create_request(self, payload: dict[str, object]) -> dict[str, object]:
                return dict(payload)

            def list_requests(self, limit: int = 50) -> list[dict[str, object]]:
                return []

        with patch("nac_web.oci_functions.build_onboarding_request_store_from_env", return_value=FakeStore()):
            result = dispatch_oci_function_request(
                FakeFunctionContext(request_url="/onboarding/requests", method="POST"),
                io.BytesIO(b"domain=myjur.de&tenant_slug=myjur&admin_email=ofunk%40myjur.de"),
                repo_root=REPO_ROOT,
            )
        payload = json.loads(result.body.decode("utf-8"))

        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(payload["request_id"][:10], "onr_myjur_")
        self.assertEqual(payload["domain"], "myjur.de")
        self.assertEqual(payload["admin_email"], "ofunk@myjur.de")
        self.assertNotIn("client_secret", result.body.decode("utf-8").lower())
        self.assertNotIn("private_key", result.body.decode("utf-8").lower())

    def test_customer_onboarding_request_post_redirects_to_status_page(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        class FakeStore:
            def __init__(self) -> None:
                self.requests: dict[str, dict[str, object]] = {}

            def create_request(self, payload: dict[str, object]) -> dict[str, object]:
                created = {
                    **payload,
                    "request_id": "onr_myjur_20260610_111500",
                    "created_at": "2026-06-10T11:15:00Z",
                }
                self.requests[str(created["request_id"])] = created
                return created

            def get_request(self, request_id: str) -> dict[str, object] | None:
                return self.requests.get(request_id)

            def list_requests(self, limit: int = 50) -> list[dict[str, object]]:
                return []

        store = FakeStore()
        with patch("nac_web.oci_functions.build_onboarding_request_store_from_env", return_value=store):
            result = dispatch_oci_function_request(
                FakeFunctionContext(request_url="/onboarding/requests?audience=customer", method="POST"),
                io.BytesIO(b"domain=myjur.de&tenant_slug=myjur&admin_email=ofunk%40myjur.de"),
                repo_root=REPO_ROOT,
            )
            status_result = dispatch_oci_function_request(
                FakeFunctionContext(
                    request_url="/onboarding/requests/onr_myjur_20260610_111500?audience=customer",
                    method="GET",
                ),
                repo_root=REPO_ROOT,
            )

        self.assertEqual(result.status_code, 303)
        self.assertEqual(
            result.headers["Location"],
            "/onboarding/requests/onr_myjur_20260610_111500?audience=customer",
        )
        self.assertNotIn("ofunk", result.headers["Location"])
        self.assertEqual(status_result.status_code, 200)
        self.assertEqual(status_result.headers["Content-Type"], "text/html; charset=utf-8")
        html = status_result.body.decode("utf-8")
        self.assertIn("Einrichtung angefragt", html)
        self.assertIn("myjur.de", html)
        self.assertIn("ofunk@myjur.de", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("OCI", html)

    def test_rejects_non_customer_safe_get_routes(self) -> None:
        from nac_web.oci_functions import dispatch_oci_function_request

        blocked_paths = [
            "/admin/onboarding",
            "/admin/onboarding/apply-readiness?domain=myjur.de&admin_email=admin@myjur.de",
            "/bpmn/immobilienkaufvertrag/edit",
            "/api/bpmn/immobilienkaufvertrag/xml",
            "/api/tenant/domain-check?domain=myjur.de&tenant_slug=myjur",
            "/onboarding/requests/onr_myjur_20260610_111500?admin_email=ofunk@myjur.de",
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
