from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
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
DEFAULT_DATA_REPO = REPO_ROOT.parent / "funktion8-demo8notariat"
DEFAULT_DATA_REPO_URL = "https://github.com/funktion8/demo8notariat.git"
OPERATOR_CONFIG = (Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".nac") / "NaC" / "operator-config.json")
LOCAL_NO_STORE_HEADERS = (
    ("Cache-Control", "no-store, max-age=0"),
    ("Pragma", "no-cache"),
)
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
            if route == "/api/operator-config":
                self._send_json(build_operator_config_payload())
                return
            if route == "/api/matters":
                self._send_json(list_operator_matters())
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
            if route == "/api/operator-config":
                try:
                    payload = save_operator_config_from_body(self._read_request_body())
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(payload)
                return
            if route == "/api/matters":
                try:
                    payload = create_operator_matter_from_body(self._read_request_body())
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(payload, HTTPStatus.CREATED)
                return
            if route == "/api/matters/status":
                try:
                    payload = update_operator_matter_status_from_body(self._read_request_body())
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(payload)
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
            self._send_no_store_headers()
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
            self._send_no_store_headers()
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def _send_no_store_headers(self) -> None:
            for name, value in LOCAL_NO_STORE_HEADERS:
                self.send_header(name, value)

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


def build_operator_config_payload(config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    values = load_operator_config(config_path)
    data_repo = Path(values["data_repo_path"]).expanduser()
    data_repo_exists = data_repo.exists()
    data_repo_git = data_repo / ".git"
    return {
        "schema_version": "nac.operator-config/v1",
        "config_path": str(config_path),
        "values": values,
        "status": {
            "nac_repo_path": str(REPO_ROOT),
            "nac_git_origin": git_origin(REPO_ROOT),
            "data_repo_exists": data_repo_exists,
            "data_repo_git_present": data_repo_git.exists(),
            "data_repo_remote": git_origin(data_repo) if data_repo_git.exists() else None,
            "demo_data_repo_default": str(DEFAULT_DATA_REPO),
        },
    }


def load_operator_config(config_path: Path = OPERATOR_CONFIG) -> dict[str, str]:
    values = default_operator_config()
    if config_path.is_file():
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        configured = raw.get("values") if isinstance(raw, dict) else None
        if isinstance(configured, dict):
            for key in values:
                if key in configured:
                    values[key] = clean_config_value(configured[key])
    return values


def default_operator_config() -> dict[str, str]:
    return {
        "nac_fork_git_url": git_origin(REPO_ROOT) or "",
        "data_git_url": git_origin(DEFAULT_DATA_REPO) or tenant_manifest_remote(DEFAULT_DATA_REPO) or DEFAULT_DATA_REPO_URL,
        "data_repo_path": str(DEFAULT_DATA_REPO),
    }


def save_operator_config_from_body(body: bytes, config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8") if body else "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Ungültiges JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Konfiguration muss ein JSON-Objekt sein.")
    return save_operator_config(payload, config_path=config_path)


def save_operator_config(payload: dict[str, Any], config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    current = load_operator_config(config_path)
    values = payload.get("values") if isinstance(payload.get("values"), dict) else payload
    for key in current:
        if key in values:
            current[key] = clean_config_value(values[key])
    document = {
        "schema_version": "nac.operator-config/v1",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "values": current,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return build_operator_config_payload(config_path)


def clean_config_value(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) > 2048:
        raise ValueError("Konfigurationswert ist zu lang.")
    if any(ord(char) < 32 for char in text):
        raise ValueError("Konfigurationswert enthält Steuerzeichen.")
    return text


def tenant_manifest_remote(repo: Path) -> str | None:
    manifest = repo / ".nac-tenant.json"
    if not manifest.is_file():
        return None
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    remote = payload.get("remote_url") if isinstance(payload, dict) else None
    return str(remote) if remote else None


def git_origin(repo: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


MATTER_STATUS_ALIASES = {
    "intake": "open",
    "open": "open",
    "offen": "open",
    "active": "open",
    "waiting": "waiting",
    "warten": "waiting",
    "blocked": "waiting",
    "completed": "completed",
    "abgeschlossen": "completed",
    "closed": "completed",
}
MATTER_STATUS_LABELS = {
    "open": "offen",
    "waiting": "warten",
    "completed": "abgeschlossen",
}


def list_operator_matters(config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    repo = operator_data_repo(config_path)
    matters = read_operator_matter_summaries(repo)
    counts: dict[str, dict[str, int]] = {}
    for matter in matters:
        usecase_slug = str(matter.get("usecase_slug") or "unknown")
        bucket = counts.setdefault(usecase_slug, {"open": 0, "waiting": 0, "completed": 0, "total": 0})
        status = str(matter.get("status") or "open")
        bucket[status] = bucket.get(status, 0) + 1
        bucket["total"] += 1
    return {
        "schema_version": "nac.operator-matters/v1",
        "data_repo_path": str(repo),
        "data_repo_exists": repo.exists(),
        "status_labels": MATTER_STATUS_LABELS,
        "counts": counts,
        "matters": matters,
    }


def create_operator_matter_from_body(body: bytes, config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    payload = parse_request_json(body)
    return create_operator_matter(payload, config_path=config_path)


def create_operator_matter(payload: dict[str, Any], config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    repo = operator_data_repo(config_path)
    ensure_demo_data_repo(repo)
    values = payload.get("values") if isinstance(payload.get("values"), dict) else payload
    usecase_slug = required_text(values, "usecase_slug")
    usecase_title = clean_text(values.get("usecase_title") or usecase_slug)
    matter_title = clean_text(values.get("title") or f"{usecase_title} Demo-Vorgang")
    client_name = clean_text(values.get("client_name") or "Demo Mandant")
    participant_name = clean_text(values.get("participant_name") or client_name)
    document_title = clean_text(values.get("document_title") or f"{usecase_title} Unterlage")
    status = normalize_matter_status(values.get("status") or "open")
    status_reason = clean_text(values.get("status_reason") or "")

    now = _now_utc()
    year = now[:4]
    matter_id = next_matter_id(repo, year)
    sequence = int(matter_id.rsplit("-", maxsplit=1)[1])
    safe_matter_id = safe_identifier(matter_id)
    client_person_id = f"PER-{safe_matter_id}-MANDANT"
    participant_person_id = f"PER-{safe_matter_id}-BETEILIGT"
    document_id = f"DOC-{safe_matter_id}-UNTERLAGE"
    matter_dir = repo / "akten" / year / matter_id

    persons = [
        {
            "schema_version": "nac.person/v0.1",
            "person_id": client_person_id,
            "type": "natural_person",
            "display_name": client_name,
            "roles": ["client"],
            "data_classification": "synthetic_personal_data",
        },
        {
            "schema_version": "nac.person/v0.1",
            "person_id": participant_person_id,
            "type": "natural_person",
            "display_name": participant_name,
            "roles": ["participant"],
            "data_classification": "synthetic_personal_data",
        },
    ]
    document = {
        "schema_version": "nac.document/v0.1",
        "document_id": document_id,
        "matter_id": matter_id,
        "title": document_title,
        "document_type": "input_document",
        "media_type": "application/octet-stream",
        "data_classification": "synthetic_document_metadata",
        "subject_person_ids": [participant_person_id],
        "storage": {
            "original": f"dokumente/{document_id}/original/{safe_identifier(document_title).lower()}.placeholder.txt"
        },
        "created_at": now,
    }
    matter = {
        "schema_version": "nac.matter/v0.2",
        "matter_id": matter_id,
        "aktenzeichen": f"UVZ {sequence}/{year}",
        "title": matter_title,
        "case_type": usecase_slug,
        "usecase_slug": usecase_slug,
        "status": status,
        "status_reason": status_reason,
        "owner_role": "notary_clerk",
        "opened_at": now,
        "updated_at": now,
        "participant_person_ids": [client_person_id, participant_person_id],
        "document_ids": [document_id],
        "event_log": f"akten/{year}/{matter_id}/ereignisse.jsonl",
        "data_classification": "synthetic_full_case",
        "guardrails": {
            "real_mandate_data_allowed": False,
            "pin_or_card_data_allowed": False,
            "secrets_allowed": False,
        },
        "pointers": {
            "persons": "personen/<person_id>.json",
            "documents": "dokumente/<document_id>/metadata.json",
            "binary_files": "dokumente/<document_id>/original/*",
        },
    }
    participants = {
        "schema_version": "nac.matter-participants/v0.1",
        "matter_id": matter_id,
        "participants": [
            {"person_id": client_person_id, "role": "client", "signing_required": False},
            {"person_id": participant_person_id, "role": "participant", "signing_required": True},
        ],
    }
    matter_documents = {
        "schema_version": "nac.matter-documents/v0.1",
        "matter_id": matter_id,
        "documents": [{"document_id": document_id, "role": "input_document", "status": "expected"}],
    }
    event = {
        "schema_version": "nac.event/v0.1",
        "event_id": f"EVT-{safe_matter_id}-CREATED",
        "matter_id": matter_id,
        "timestamp": now,
        "actor": "nac_operator",
        "event_type": "matter_created",
        "summary": f"Demo-Akte für {usecase_title} angelegt.",
        "status": status,
        "affected_ids": {"person_ids": matter["participant_person_ids"], "document_ids": matter["document_ids"]},
    }

    for person in persons:
        write_json(repo / "personen" / f"{person['person_id']}.json", person)
    write_json(repo / "dokumente" / document_id / "metadata.json", document)
    write_if_missing(repo / document["storage"]["original"], f"Placeholder für {document_title} ({document_id}).\n")
    write_json(matter_dir / "akte.json", matter)
    write_json(matter_dir / "beteiligte.json", participants)
    write_json(matter_dir / "dokumente.json", matter_documents)
    append_jsonl(matter_dir / "ereignisse.jsonl", event)
    append_jsonl(journal_path(repo, now), event)
    rebuild_operator_indexes(repo)
    return {"schema_version": "nac.operator-matter-write/v1", "matter": summarize_matter(repo, matter)}


def update_operator_matter_status_from_body(body: bytes, config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    payload = parse_request_json(body)
    return update_operator_matter_status(payload, config_path=config_path)


def update_operator_matter_status(payload: dict[str, Any], config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    repo = operator_data_repo(config_path)
    ensure_demo_data_repo(repo)
    matter_id = required_text(payload, "matter_id")
    status = normalize_matter_status(payload.get("status") or "open")
    status_reason = clean_text(payload.get("status_reason") or "")
    matter_file = find_matter_file(repo, matter_id)
    if matter_file is None:
        raise ValueError(f"Akte nicht gefunden: {matter_id}")
    matter = read_json(matter_file)
    previous_status = normalize_matter_status(matter.get("status") or "open")
    now = _now_utc()
    matter["status"] = status
    matter["status_reason"] = status_reason
    matter["updated_at"] = now
    write_json(matter_file, matter)
    event = {
        "schema_version": "nac.event/v0.1",
        "event_id": f"EVT-{safe_identifier(matter_id)}-STATUS-{safe_identifier(now)}",
        "matter_id": matter_id,
        "timestamp": now,
        "actor": "nac_operator",
        "event_type": "matter_status_changed",
        "summary": f"Status von {MATTER_STATUS_LABELS[previous_status]} auf {MATTER_STATUS_LABELS[status]} gesetzt.",
        "previous_status": previous_status,
        "status": status,
        "status_reason": status_reason,
    }
    append_jsonl(matter_file.parent / "ereignisse.jsonl", event)
    append_jsonl(journal_path(repo, now), event)
    rebuild_operator_indexes(repo)
    return {"schema_version": "nac.operator-matter-status/v1", "matter": summarize_matter(repo, matter)}


def operator_data_repo(config_path: Path = OPERATOR_CONFIG) -> Path:
    return Path(load_operator_config(config_path)["data_repo_path"]).expanduser().resolve()


def ensure_demo_data_repo(repo: Path) -> None:
    manifest = repo / ".nac-tenant.json"
    if not manifest.is_file():
        raise ValueError(f"Kein NaC-Datenrepo gefunden: {repo}")
    payload = read_json(manifest)
    if payload.get("mode") != "demo":
        raise ValueError("Schreiben über die lokale Operator-Webapp ist aktuell nur für Demo-Datenrepos erlaubt.")


def read_operator_matter_summaries(repo: Path) -> list[dict[str, Any]]:
    matters: list[dict[str, Any]] = []
    if not repo.exists():
        return matters
    for matter_file in sorted((repo / "akten").glob("*/*/akte.json")):
        try:
            matter = read_json(matter_file)
        except (OSError, json.JSONDecodeError):
            continue
        matters.append(summarize_matter(repo, matter))
    matters.sort(key=lambda item: (str(item.get("opened_at") or ""), str(item.get("matter_id") or "")), reverse=True)
    return matters


def summarize_matter(repo: Path, matter: dict[str, Any]) -> dict[str, Any]:
    person_ids = [str(value) for value in matter.get("participant_person_ids", []) if value]
    document_ids = [str(value) for value in matter.get("document_ids", []) if value]
    return {
        "matter_id": str(matter.get("matter_id") or ""),
        "aktenzeichen": str(matter.get("aktenzeichen") or matter.get("matter_id") or ""),
        "title": str(matter.get("title") or "Unbenannte Akte"),
        "usecase_slug": str(matter.get("usecase_slug") or matter.get("case_type") or ""),
        "status": normalize_matter_status(matter.get("status") or "open"),
        "status_label": MATTER_STATUS_LABELS[normalize_matter_status(matter.get("status") or "open")],
        "status_reason": str(matter.get("status_reason") or ""),
        "opened_at": str(matter.get("opened_at") or ""),
        "updated_at": str(matter.get("updated_at") or ""),
        "participants": load_person_display_names(repo, person_ids),
        "document_count": len(document_ids),
        "data_classification": str(matter.get("data_classification") or ""),
    }


def load_person_display_names(repo: Path, person_ids: list[str]) -> list[str]:
    names: list[str] = []
    for person_id in person_ids:
        person_file = repo / "personen" / f"{person_id}.json"
        if not person_file.is_file():
            names.append(person_id)
            continue
        try:
            person = read_json(person_file)
        except (OSError, json.JSONDecodeError):
            names.append(person_id)
            continue
        names.append(str(person.get("display_name") or person_id))
    return names


def rebuild_operator_indexes(repo: Path) -> None:
    matter_payloads = []
    for matter_file in sorted((repo / "akten").glob("*/*/akte.json")):
        try:
            matter_payloads.append(read_json(matter_file))
        except (OSError, json.JSONDecodeError):
            continue
    person_payloads = []
    for person_file in sorted((repo / "personen").glob("*.json")):
        try:
            person = read_json(person_file)
        except (OSError, json.JSONDecodeError):
            continue
        person_payloads.append(
            {
                "person_id": person.get("person_id"),
                "display_name": person.get("display_name"),
                "roles": person.get("roles", []),
            }
        )
    document_payloads = []
    for document_file in sorted((repo / "dokumente").glob("*/metadata.json")):
        try:
            document = read_json(document_file)
        except (OSError, json.JSONDecodeError):
            continue
        document_payloads.append(
            {
                "document_id": document.get("document_id"),
                "matter_id": document.get("matter_id"),
                "title": document.get("title"),
                "document_type": document.get("document_type"),
            }
        )
    write_json(repo / "index" / "akten.json", {"schema_version": "nac.index-matters/v0.1", "matters": matter_payloads})
    write_json(repo / "index" / "personen.json", {"schema_version": "nac.index-persons/v0.1", "persons": person_payloads})
    write_json(repo / "index" / "dokumente.json", {"schema_version": "nac.index-documents/v0.1", "documents": document_payloads})


def parse_request_json(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8") if body else "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Ungültiges JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Request muss ein JSON-Objekt sein.")
    return payload


def required_text(values: dict[str, Any], key: str) -> str:
    text = clean_text(values.get(key))
    if not text:
        raise ValueError(f"Pflichtfeld fehlt: {key}")
    return text


def clean_text(value: Any, max_length: int = 512) -> str:
    text = str(value or "").strip()
    if len(text) > max_length:
        raise ValueError("Eingabewert ist zu lang.")
    if any(ord(char) < 32 and char not in {"\t"} for char in text):
        raise ValueError("Eingabewert enthält Steuerzeichen.")
    return text


def normalize_matter_status(value: Any) -> str:
    status = str(value or "open").strip().lower()
    if status not in MATTER_STATUS_ALIASES:
        raise ValueError(f"Unbekannter Aktenstatus: {value}")
    return MATTER_STATUS_ALIASES[status]


def next_matter_id(repo: Path, year: str) -> str:
    highest = 0
    pattern = re.compile(rf"^UVZ-{re.escape(year)}-(\d{{4}})$")
    for matter_file in (repo / "akten" / year).glob("*/akte.json"):
        match = pattern.match(matter_file.parent.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"UVZ-{year}-{highest + 1:04d}"


def find_matter_file(repo: Path, matter_id: str) -> Path | None:
    for matter_file in (repo / "akten").glob("*/*/akte.json"):
        if matter_file.parent.name == matter_id:
            return matter_file
    return None


def safe_identifier(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").upper()
    return normalized or "UNBENANNT"


def journal_path(repo: Path, timestamp: str) -> Path:
    year = timestamp[:4]
    month = timestamp[5:7]
    day = timestamp[:10]
    return repo / "journal" / year / month / f"{day}.jsonl"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
