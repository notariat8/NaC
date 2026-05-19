from __future__ import annotations

import argparse
import json
import mimetypes
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SRC_ROOT_TEXT = str(SRC_ROOT)
if SRC_ROOT_TEXT in sys.path:
    sys.path.remove(SRC_ROOT_TEXT)
sys.path.insert(0, SRC_ROOT_TEXT)

from nac_web.server import NaCLocalWebApp  # noqa: E402

SITE_ROOT = REPO_ROOT / "web" / "local-operator"
READINESS_SCRIPT = REPO_ROOT / "plugins" / "nac-cyberjack-rfid" / "scripts" / "check_readiness.py"
STARTUP_SCRIPT = REPO_ROOT / "scripts" / "startup_check.py"
TEST_LOG = REPO_ROOT / "logs" / "test-log.jsonl"
ALLOWED_ORIGINS = {
    "https://funktion8.de",
    "https://www.funktion8.de",
    "http://localhost",
    "http://127.0.0.1",
    "null",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local NaC hardware-readiness web bridge.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address. Default: 127.0.0.1.")
    parser.add_argument("--port", type=int, default=8766, help="Port. Default: 8766.")
    parser.add_argument("--open", action="store_true", help="Open the local webapp after server start.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    server = build_server(args.host, args.port)
    url = f"http://{args.host}:{server.server_port}/"
    print(f"NaC hardware bridge: {url}")
    print("Abbrechen mit Ctrl+C.")
    if args.open:
        threading.Timer(0.2, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nNaC hardware bridge beendet.")
    finally:
        server.server_close()
    return 0


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    local_web_app = NaCLocalWebApp(REPO_ROOT)

    class Handler(BaseHTTPRequestHandler):
        def do_OPTIONS(self) -> None:  # noqa: N802
            if not self._origin_allowed():
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            self.send_response(HTTPStatus.NO_CONTENT)
            self._send_cors_headers()
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            route = unquote(urlparse(self.path).path)
            if route == "/api/healthz":
                self._send_json({"status": "ok", "localhost_only": True})
                return
            if is_local_web_route(route):
                self._send_local_web_response(local_web_app.handle(self.path))
                return
            self._serve_static(route)

        def do_HEAD(self) -> None:  # noqa: N802
            route = unquote(urlparse(self.path).path)
            if is_local_web_route(route):
                self._send_local_web_response(local_web_app.handle(self.path), include_body=False)
                return
            self._serve_static(route, include_body=False)

        def do_POST(self) -> None:  # noqa: N802
            route = unquote(urlparse(self.path).path)
            if not self._origin_allowed():
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            if route.startswith("/api/bpmn/"):
                self._send_local_web_response(local_web_app.handle_post(self.path, self._read_request_body()))
                return
            if route != "/api/hardware-readiness":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._discard_request_body()
            self._send_json(run_hardware_readiness(), HTTPStatus.OK)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _serve_static(self, route: str, include_body: bool = True) -> None:
            if not SITE_ROOT.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "Website root not found")
                return
            requested = "index.html" if route in {"", "/"} else route.lstrip("/")
            if requested.endswith("/"):
                requested += "index.html"
            target = (SITE_ROOT / requested).resolve()
            if not target.is_file() or SITE_ROOT.resolve() not in target.parents:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            body = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self._send_cors_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self._send_bytes(int(status), "application/json; charset=utf-8", body)

        def _send_local_web_response(self, response: tuple[int, str, bytes], include_body: bool = True) -> None:
            status, content_type, body = response
            self._send_bytes(status, content_type, body, include_body=include_body)

        def _send_bytes(self, status: int, content_type: str, body: bytes, include_body: bool = True) -> None:
            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def _send_cors_headers(self) -> None:
            origin = self.headers.get("Origin")
            if origin and self._origin_allowed():
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")

        def _origin_allowed(self) -> bool:
            origin = self.headers.get("Origin")
            if not origin:
                return True
            if origin in ALLOWED_ORIGINS:
                return True
            return any(origin.startswith(prefix + ":") for prefix in {"http://localhost", "http://127.0.0.1"})

        def _discard_request_body(self) -> None:
            self._read_request_body()

        def _read_request_body(self) -> bytes:
            length = int(self.headers.get("Content-Length") or "0")
            return self.rfile.read(length) if length else b""

    return ThreadingHTTPServer((host, port), Handler)


def is_local_web_route(route: str) -> bool:
    return route == "/api/bpmn-moddle" or route.startswith(("/bpmn/", "/kg/", "/api/bpmn/", "/api/kg/"))


def run_hardware_readiness() -> dict[str, Any]:
    startup = run_command([sys.executable, str(STARTUP_SCRIPT), "--profile", "notary-workstation", "--ide", "auto"], 45)
    readiness = run_command([sys.executable, str(READINESS_SCRIPT), "--json", "--probe-morris-api"], 90)
    readiness_payload = parse_json(readiness["stdout"])
    payload = {
        "schema_version": "nac.hardware-readiness-bridge/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "localhost_only": True,
        "startup_check": summarize_startup(startup),
        "readiness": readiness_payload,
        "readiness_command": {
            "exit_code": readiness["exit_code"],
            "stderr": readiness["stderr"],
            "json_parsed": readiness_payload is not None,
        },
        "overall_status": readiness_payload.get("overall_status") if isinstance(readiness_payload, dict) else "failed",
    }
    payload["test_log"] = append_test_log(build_test_log_entry(payload))
    return payload


def run_command(command: list[str], timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": "Command timed out.",
        }


def parse_json(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def summarize_startup(result: dict[str, Any]) -> dict[str, Any]:
    lines = [line.strip() for line in result["stdout"].splitlines() if line.strip()]
    return {
        "exit_code": result["exit_code"],
        "status_lines": [line for line in lines if line.startswith("STATUS:")],
        "warnings": [line for line in lines if line.startswith("WARN:")],
        "errors": [line for line in lines if line.startswith("ERROR:")],
        "stderr": result["stderr"],
    }


def build_test_log_entry(payload: dict[str, Any]) -> dict[str, Any]:
    readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}
    checks = readiness.get("checks") if isinstance(readiness, dict) else []
    check_counts: dict[str, int] = {}
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            status = str(check.get("status") or "unknown")
            check_counts[status] = check_counts.get(status, 0) + 1
    status = str(payload.get("overall_status") or "failed")
    return {
        "schema_version": "nac.test-log/v1",
        "timestamp": payload.get("generated_at"),
        "source": "nac_hw_bridge",
        "scope": "hardware-readiness",
        "result": result_from_status(status),
        "status": status,
        "summary": {
            "check_counts": check_counts,
            "startup_warnings": len(payload.get("startup_check", {}).get("warnings", [])),
            "localhost_only": payload.get("localhost_only") is True,
            "secrets_captured": False,
        },
    }


def result_from_status(status: str) -> str:
    if status in {"ready", "passed"}:
        return "success"
    return "fail"


def append_test_log(entry: dict[str, Any]) -> dict[str, Any]:
    try:
        TEST_LOG.parent.mkdir(parents=True, exist_ok=True)
        with TEST_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as exc:
        return {"written": False, "path": str(TEST_LOG.relative_to(REPO_ROOT)), "error": str(exc)}
    return {"written": True, "path": str(TEST_LOG.relative_to(REPO_ROOT))}


if __name__ == "__main__":
    raise SystemExit(main())
