from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class SmokeTarget:
    name: str
    url: str
    expected: str


DEFAULT_NOTARKAMMER_DEMO_TARGETS = (
    SmokeTarget("public_home", "https://notariat8.de/", "http_200"),
    SmokeTarget("public_process_model", "https://notariat8.de/prozessmodell.html", "http_200"),
    SmokeTarget("app_healthz", "https://app.notariat8.de/healthz", "http_200"),
    SmokeTarget("workspace_fail_closed", "https://app.notariat8.de/workspace", "fail_closed_expected"),
)

DEMO_LATENCY_WARNING_MS = 10_000

SENSITIVE_BODY_MARKERS = (
    "authorization_url",
    "access_token",
    "id_token",
    "refresh_token",
    "client_secret",
    "state=",
    "nonce=",
    "/auth/callback",
)


def redact_url_for_report(url: str) -> str:
    parts = urlsplit(url)
    if parts.query:
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "<redacted>", ""))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def evaluate_smoke_result(
    *,
    target_name: str,
    status: int,
    content_type: str,
    body_preview: str,
) -> dict[str, str]:
    if target_name == "workspace_fail_closed":
        if status in {401, 403}:
            return {"status": "pass", "classification": "fail_closed_expected"}
        closed_markers = ("Anmeldung erforderlich", "Keine Mandatsdaten", "Arbeitsbereich bleibt geschlossen")
        if status == 200 and any(marker in body_preview for marker in closed_markers):
            return {"status": "pass", "classification": "fail_closed_expected"}
        return {"status": "fail", "classification": "workspace_open_or_unexpected"}
    if status == 200:
        return {"status": "pass", "classification": "http_200"}
    return {"status": "fail", "classification": "unexpected_status"}


def build_smoke_report(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    sanitized_results = []
    warnings = []
    overall = "pass"
    for result in results:
        evaluation = evaluate_smoke_result(
            target_name=str(result["name"]),
            status=int(result["status"]),
            content_type=str(result.get("content_type", "")),
            body_preview=str(result.get("body_preview", "")),
        )
        if evaluation["status"] != "pass":
            overall = "fail"
        latency_warning = ""
        elapsed_ms = int(result.get("elapsed_ms", 0))
        if (
            str(result["name"]) == "workspace_fail_closed"
            and evaluation["classification"] == "fail_closed_expected"
            and elapsed_ms > DEMO_LATENCY_WARNING_MS
        ):
            latency_warning = "slow_fail_closed_response"
            warnings.append(f"{result['name']}:{latency_warning}")
        sanitized_results.append(
            {
                "name": str(result["name"]),
                "url": redact_url_for_report(str(result["url"])),
                "status": int(result["status"]),
                "content_type": str(result.get("content_type", ""))[:120],
                "elapsed_ms": elapsed_ms,
                "classification": evaluation["classification"],
                "result": evaluation["status"],
                "latency_warning": latency_warning,
                "body_preview": _redacted_body_preview(str(result.get("body_preview", ""))),
            }
        )
    return {
        "schema_version": "nac.notarkammer-demo-smoke/v0.1",
        "scope": "notarkammer_demo_readiness",
        "overall": overall,
        "guardrails": {
            "contains_credentials": False,
            "contains_callback_values": False,
            "contains_mandate_data": False,
            "performs_writes": False,
        },
        "warnings": warnings,
        "results": sanitized_results,
    }


def build_smoke_summary(report: dict[str, Any]) -> dict[str, Any]:
    summarized_results = []
    for result in report.get("results", []):
        summarized_results.append(
            {
                key: value
                for key, value in dict(result).items()
                if key != "body_preview"
            }
        )
    return {
        "schema_version": str(report.get("schema_version", "nac.notarkammer-demo-smoke/v0.1")),
        "scope": str(report.get("scope", "notarkammer_demo_readiness")),
        "overall": str(report.get("overall", "fail")),
        "guardrails": dict(report.get("guardrails", {})),
        "warnings": list(report.get("warnings", [])),
        "results": summarized_results,
    }


def run_smoke(targets: Iterable[SmokeTarget] = DEFAULT_NOTARKAMMER_DEMO_TARGETS, *, timeout_seconds: int = 15) -> dict[str, Any]:
    results = []
    for target in targets:
        started = time.monotonic()
        status = 0
        content_type = ""
        body_preview = ""
        try:
            request = Request(target.url, headers={"User-Agent": "notariat8-demo-smoke/0.1"})
            with urlopen(request, timeout=timeout_seconds) as response:
                status = int(response.status)
                content_type = response.headers.get("Content-Type", "")
                body_preview = response.read(4096).decode("utf-8", errors="replace")
        except HTTPError as exc:
            status = int(exc.code)
            content_type = exc.headers.get("Content-Type", "")
            try:
                body_preview = exc.read(4096).decode("utf-8", errors="replace")
            except Exception:
                body_preview = ""
        except URLError as exc:
            body_preview = f"network_error:{exc.reason.__class__.__name__}"
        except TimeoutError:
            body_preview = "network_error:timeout"
        elapsed_ms = int((time.monotonic() - started) * 1000)
        results.append(
            {
                "name": target.name,
                "url": target.url,
                "status": status,
                "content_type": content_type,
                "body_preview": body_preview,
                "elapsed_ms": elapsed_ms,
            }
        )
    return build_smoke_report(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the read-only notariat8 Notarkammer demo smoke check.")
    parser.add_argument("--timeout-seconds", type=int, default=15)
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Omit response body previews from the JSON output for demo evidence.",
    )
    args = parser.parse_args(argv)
    report = run_smoke(timeout_seconds=args.timeout_seconds)
    if args.summary_only:
        report = build_smoke_summary(report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["overall"] == "pass" else 1


def _redacted_body_preview(value: str) -> str:
    if any(marker in value for marker in SENSITIVE_BODY_MARKERS):
        return "<redacted>"
    return value.strip()[:500]


if __name__ == "__main__":
    raise SystemExit(main())
