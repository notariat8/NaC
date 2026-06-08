from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_web.server import NaCLocalWebApp  # noqa: E402


def read(path: str) -> str:
    file_path = REPO_ROOT / path
    if not file_path.exists():
        raise AssertionError(f"{path} is missing")
    return file_path.read_text(encoding="utf-8")


class NaCRuntimeDeploymentContractTests(unittest.TestCase):
    def test_systemd_service_runs_nac_web_on_lb_backend_port(self) -> None:
        service = read("deploy/systemd/nac-web.service")

        required_terms = [
            "User=nac",
            "EnvironmentFile=-/etc/nac/nac-web.env",
            "WorkingDirectory=/opt/nac/current",
            "ExecStart=/opt/nac/venv/bin/nac-web --repo-root /opt/nac/current --host 0.0.0.0 --port 8768",
            "Restart=on-failure",
        ]

        for term in required_terms:
            self.assertIn(term, service)

        forbidden_terms = [
            "BEGIN PRIVATE KEY",
            "key_file",
            "client_secret",
            "password=",
        ]

        for term in forbidden_terms:
            self.assertNotIn(term, service)

    def test_runtime_operations_docs_name_first_live_endpoints_and_gate(self) -> None:
        german_content = read("docs/de/operations/oci-runtime.md")
        english_content = read("docs/en/operations/oci-runtime.md")

        required_terms = [
            "Owner Apply Approval for Apply Block G NaC runtime deployment",
            "nac-web --repo-root /opt/nac/current --host 0.0.0.0 --port 8768",
            "/healthz",
            "/admin/onboarding",
            "Keine Mandatsdaten",
            "OCI Bastion",
        ]

        for term in required_terms:
            self.assertIn(term, german_content)

        self.assertIn("No mandate data", english_content)
        self.assertIn("/admin/onboarding", english_content)
        self.assertNotEqual(german_content, english_content)

    def test_healthz_contract_returns_ok_json_for_load_balancer(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, content_type, body = app.handle("/healthz")

        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json; charset=utf-8")
        self.assertIn(b'"status": "ok"', body)

    def test_release_overlay_script_promotes_checked_archive_without_secrets(self) -> None:
        script = read("deploy/runtime/nac-web-release.sh")

        required_terms = [
            "NAC_RELEASE_ARCHIVE",
            "NAC_RELEASE_SHA256",
            "NAC_RELEASE_COMMIT",
            "/opt/nac/releases",
            "/opt/nac/current",
            "sha256sum -c",
            "tar -xzf",
            "ln -sfn",
            "systemctl restart",
            "rollback",
            "previous_target",
            "NAC_RELEASE_HEALTH_ATTEMPTS",
            "NAC_RELEASE_HEALTH_SLEEP_SECONDS",
            'for attempt in $(seq 1 "$NAC_RELEASE_HEALTH_ATTEMPTS")',
            'sleep "$NAC_RELEASE_HEALTH_SLEEP_SECONDS"',
            "http://127.0.0.1:8768/healthz",
            '"status": "ok"',
        ]

        for term in required_terms:
            self.assertIn(term, script)

        forbidden_terms = [
            "BEGIN PRIVATE KEY",
            "key_file",
            "client_secret",
            "password=",
        ]

        for term in forbidden_terms:
            self.assertNotIn(term, script)

    def test_runtime_docs_separate_app_release_overlay_from_vm_replacement(self) -> None:
        german_content = read("docs/de/operations/oci-runtime.md")
        english_content = read("docs/en/operations/oci-runtime.md")

        german_required_terms = [
            "App-Release-Overlay",
            "kein VM-Replacement",
            "VM-Replacement bleibt",
            "Basisimage",
            "Firewall",
            "Owner Apply Approval for Apply Block H NaC app release overlay",
            "Commit",
            "SHA-256",
            "systemd-Restart",
            "Rollback",
        ]

        for term in german_required_terms:
            self.assertIn(term, german_content)

        english_required_terms = [
            "App Release Overlay",
            "does not require VM replacement",
            "VM replacement remains",
            "base image",
            "firewall",
            "Owner Apply Approval for Apply Block H NaC app release overlay",
            "commit",
            "SHA-256",
            "systemd restart",
            "rollback",
        ]

        for term in english_required_terms:
            self.assertIn(term, english_content)


if __name__ == "__main__":
    unittest.main()
