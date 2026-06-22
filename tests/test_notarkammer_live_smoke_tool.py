from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_observability.demo_smoke import (  # noqa: E402
    DEFAULT_NOTARKAMMER_DEMO_TARGETS,
    DEMO_LATENCY_WARNING_MS,
    SmokeTarget,
    build_smoke_report,
    build_smoke_summary,
    evaluate_smoke_result,
    redact_url_for_report,
    run_smoke,
)


class NotarkammerLiveSmokeToolTests(unittest.TestCase):
    def test_default_targets_are_demo_safe_and_cover_public_app_and_workspace_boundary(self) -> None:
        urls = [target.url for target in DEFAULT_NOTARKAMMER_DEMO_TARGETS]

        self.assertIn("https://notariat8.de/", urls)
        self.assertIn("https://notariat8.de/prozessmodell.html", urls)
        self.assertIn("https://app.notariat8.de/healthz", urls)
        self.assertIn("https://app.notariat8.de/workspace", urls)
        self.assertNotIn("/auth/callback", "\n".join(urls))
        self.assertNotIn("code=", "\n".join(urls))
        self.assertNotIn("state=", "\n".join(urls))

    def test_workspace_accepts_fail_closed_http_status_as_expected_demo_boundary(self) -> None:
        result = evaluate_smoke_result(
            target_name="workspace_fail_closed",
            status=401,
            content_type="text/html; charset=utf-8",
            body_preview="notariat8 Anmeldung erforderlich. Keine Mandatsdaten geladen.",
        )

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["classification"], "fail_closed_expected")

    def test_report_redacts_query_values_and_remains_machine_readable(self) -> None:
        report = build_smoke_report(
            [
                {
                    "name": "login_intent",
                    "url": "https://app.notariat8.de/api/tenant/login-intent?tenant_hint=myjur",
                    "status": 200,
                    "content_type": "application/json",
                    "body_preview": '{"authorization_url":"https://idcs.example/authorize?state=secret&nonce=secret"}',
                    "elapsed_ms": 123,
                }
            ]
        )
        encoded = json.dumps(report, ensure_ascii=False)

        self.assertEqual(report["schema_version"], "nac.notarkammer-demo-smoke/v0.1")
        self.assertIn("https://app.notariat8.de/api/tenant/login-intent?<redacted>", encoded)
        self.assertNotIn("tenant_hint=myjur", encoded)
        self.assertNotIn("state=secret", encoded)
        self.assertNotIn("nonce=secret", encoded)
        self.assertNotIn("idcs.example", encoded)

    def test_summary_report_omits_body_previews_for_demo_evidence(self) -> None:
        report = build_smoke_report(
            [
                {
                    "name": "public_home",
                    "url": "https://notariat8.de/",
                    "status": 200,
                    "content_type": "text/html; charset=utf-8",
                    "body_preview": "<html>public page preview</html>",
                    "elapsed_ms": 44,
                }
            ]
        )

        summary = build_smoke_summary(report)
        encoded = json.dumps(summary, ensure_ascii=False)

        self.assertEqual(summary["schema_version"], "nac.notarkammer-demo-smoke/v0.1")
        self.assertEqual(summary["overall"], "pass")
        self.assertEqual(summary["results"][0]["name"], "public_home")
        self.assertEqual(summary["results"][0]["result"], "pass")
        self.assertNotIn("body_preview", summary["results"][0])
        self.assertNotIn("public page preview", encoded)

    def test_workspace_fail_closed_latency_warning_does_not_fail_demo_smoke(self) -> None:
        report = build_smoke_report(
            [
                {
                    "name": "workspace_fail_closed",
                    "url": "https://app.notariat8.de/workspace",
                    "status": 401,
                    "content_type": "text/html; charset=utf-8",
                    "body_preview": "Anmeldung erforderlich. Keine Mandatsdaten geladen.",
                    "elapsed_ms": DEMO_LATENCY_WARNING_MS + 1,
                }
            ]
        )

        self.assertEqual(report["overall"], "pass")
        self.assertEqual(report["warnings"], ["workspace_fail_closed:slow_fail_closed_response"])
        self.assertEqual(report["results"][0]["classification"], "fail_closed_expected")
        self.assertEqual(report["results"][0]["latency_warning"], "slow_fail_closed_response")

    def test_url_redaction_keeps_path_and_drops_query(self) -> None:
        self.assertEqual(
            redact_url_for_report("https://app.notariat8.de/auth/callback?code=secret&state=secret"),
            "https://app.notariat8.de/auth/callback?<redacted>",
        )

    def test_timeout_is_reported_as_single_failed_target_instead_of_aborting(self) -> None:
        with patch("nac_observability.demo_smoke.urlopen", side_effect=TimeoutError("read timed out")):
            report = run_smoke(
                [SmokeTarget("public_home", "https://notariat8.de/", "http_200")],
                timeout_seconds=1,
            )

        self.assertEqual(report["overall"], "fail")
        self.assertEqual(report["results"][0]["name"], "public_home")
        self.assertEqual(report["results"][0]["status"], 0)
        self.assertEqual(report["results"][0]["classification"], "unexpected_status")
        self.assertIn("timeout", report["results"][0]["body_preview"])


if __name__ == "__main__":
    unittest.main()
