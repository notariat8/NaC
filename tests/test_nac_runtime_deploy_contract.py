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


if __name__ == "__main__":
    unittest.main()
