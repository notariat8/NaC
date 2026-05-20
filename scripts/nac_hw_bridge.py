from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import mimetypes
import os
import re
import shutil
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
MAX_UPLOAD_FILE_BYTES = 5 * 1024 * 1024
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
            if route in {"/api/healthz", "/healthz"}:
                self._send_json({"status": "ok", "localhost_only": True})
                return
            if route == "/api/operator-config":
                self._send_json(build_operator_config_payload())
                return
            if route == "/api/matters":
                self._send_json(list_operator_matters())
                return
            if route == "/api/import-proposals":
                self._send_json(list_import_proposals())
                return
            if is_local_web_route(route):
                self._send_local_web_response(local_web_app.handle(self.path))
                return
            self._serve_static(route)

        def do_HEAD(self) -> None:  # noqa: N802
            route = unquote(urlparse(self.path).path)
            if route in {"/api/healthz", "/healthz"}:
                body = json.dumps({"status": "ok", "localhost_only": True}, ensure_ascii=False).encode("utf-8")
                self._send_bytes(HTTPStatus.OK, "application/json; charset=utf-8", body, include_body=False)
                return
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
            if route == "/api/import-proposals":
                try:
                    payload = create_import_proposal_from_body(self._read_request_body())
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(payload, HTTPStatus.CREATED)
                return
            if route == "/api/import-proposals/accept":
                try:
                    payload = accept_import_proposal_from_body(self._read_request_body())
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
IMPORT_STATUS_LABELS = {
    "pending": "neu",
    "accepted": "übernommen",
    "rejected": "abgelehnt",
}


def list_import_proposals(config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    repo = operator_data_repo(config_path)
    proposals = read_import_proposals(repo)
    counts = {"pending": 0, "accepted": 0, "rejected": 0, "total": 0}
    for proposal in proposals:
        status = str(proposal.get("status") or "pending")
        counts[status] = counts.get(status, 0) + 1
        counts["total"] += 1
    return {
        "schema_version": "nac.operator-import-proposals/v1",
        "data_repo_path": str(repo),
        "data_repo_exists": repo.exists(),
        "status_labels": IMPORT_STATUS_LABELS,
        "counts": counts,
        "proposals": proposals,
    }


def create_import_proposal_from_body(body: bytes, config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    payload = parse_request_json(body)
    return create_import_proposal(payload, config_path=config_path)


def create_import_proposal(payload: dict[str, Any], config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    repo = operator_data_repo(config_path)
    ensure_demo_data_repo(repo)
    values = payload.get("values") if isinstance(payload.get("values"), dict) else payload
    title = clean_text(values.get("title") or "Eingang ohne Betreff")
    usecase_slug = clean_text(values.get("usecase_slug") or "unterschriftsbeglaubigung")
    usecase_title = clean_text(values.get("usecase_title") or "Unterschriftsbeglaubigung")
    now = _now_utc()
    proposal_id = next_import_proposal_id(repo, title, now)
    source_files = stage_import_source_files(repo, proposal_id, values.get("source_files", []), values.get("synthetic_test_data"))
    matter_values = {
        "usecase_slug": usecase_slug,
        "usecase_title": usecase_title,
        "title": title,
        "client_name": clean_text(values.get("client_name") or ""),
        "participant_name": clean_text(values.get("participant_name") or values.get("client_name") or ""),
        "document_title": clean_text(values.get("document_title") or "Eingangsdokument"),
        "document_type": clean_text(values.get("document_type") or "input_document"),
        "media_type": clean_text(values.get("media_type") or "application/octet-stream"),
        "data_classification": clean_text(values.get("data_classification") or "synthetic_document_metadata"),
        "status": normalize_matter_status(values.get("status") or "open"),
        "status_reason": clean_text(values.get("status_reason") or ""),
        "metadata": clean_json_payload(values.get("metadata") if isinstance(values.get("metadata"), dict) else {}),
    }
    proposal = {
        "schema_version": "nac.import-proposal/v0.1",
        "proposal_id": proposal_id,
        "status": "pending",
        "created_at": now,
        "source": clean_text(values.get("source") or "codex_prompt"),
        "source_type": clean_text(values.get("source_type") or "prompt"),
        "summary": clean_text(values.get("summary") or title),
        "synthetic_test_data": bool(values.get("synthetic_test_data")),
        "matter_values": matter_values,
        "source_files": source_files,
        "review": {
            "requires_human_confirmation": True,
            "reason": clean_text(values.get("review_reason") or "Import-Vorschlag muss vor Übernahme fachlich geprüft werden."),
        },
        "guardrails": {
            "real_mandate_data_allowed": False,
            "pin_or_card_data_allowed": False,
            "secrets_allowed": False,
        },
    }
    write_json(import_proposal_file(repo, proposal_id), proposal)
    return {
        "schema_version": "nac.operator-import-proposal-write/v1",
        "proposal": summarize_import_proposal(proposal),
    }


def accept_import_proposal_from_body(body: bytes, config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    payload = parse_request_json(body)
    return accept_import_proposal(payload, config_path=config_path)


def accept_import_proposal(payload: dict[str, Any], config_path: Path = OPERATOR_CONFIG) -> dict[str, Any]:
    repo = operator_data_repo(config_path)
    ensure_demo_data_repo(repo)
    proposal_id = required_text(payload, "proposal_id")
    proposal_file = import_proposal_file(repo, proposal_id)
    if not proposal_file.is_file():
        raise ValueError(f"Import-Vorschlag nicht gefunden: {proposal_id}")
    proposal = read_json(proposal_file)
    if proposal.get("status") != "pending":
        raise ValueError("Import-Vorschlag wurde bereits bearbeitet.")
    matter_values = proposal.get("matter_values") if isinstance(proposal.get("matter_values"), dict) else {}
    matter_values["document_files"] = [
        {
            "source": file.get("staged_path"),
            "filename": file.get("filename"),
            "label": file.get("label"),
            "media_type": file.get("media_type"),
        }
        for file in proposal.get("source_files", [])
        if isinstance(file, dict) and file.get("staged_path")
    ]
    matter_payload = create_operator_matter({"values": matter_values}, config_path=config_path)
    matter = matter_payload["matter"]
    now = _now_utc()
    proposal["status"] = "accepted"
    proposal["accepted_at"] = now
    proposal["matter_id"] = matter["matter_id"]
    proposal["aktenzeichen"] = matter["aktenzeichen"]
    write_json(proposal_file, proposal)
    append_import_accepted_event(repo, matter["matter_id"], proposal_id, now)
    rebuild_operator_indexes(repo)
    return {
        "schema_version": "nac.operator-import-proposal-accept/v1",
        "proposal": summarize_import_proposal(proposal),
        "matter": matter,
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
    document_type = clean_text(values.get("document_type") or "input_document")
    media_type = clean_text(values.get("media_type") or "application/octet-stream")
    data_classification = clean_text(values.get("data_classification") or "synthetic_document_metadata")
    extracted_metadata = clean_json_payload(values.get("metadata") if isinstance(values.get("metadata"), dict) else {})
    document_files = values.get("document_files") if isinstance(values.get("document_files"), list) else []
    status = normalize_matter_status(values.get("status") or "open")
    status_reason = clean_text(values.get("status_reason") or "")

    now = _now_utc()
    workflow_binding = build_workflow_binding(usecase_slug, usecase_title, now, values)
    checklist_state = build_checklist_state(usecase_slug, usecase_title, now, workflow_binding)
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
        "document_type": document_type,
        "media_type": media_type,
        "data_classification": data_classification,
        "subject_person_ids": [participant_person_id],
        "storage": {},
        "created_at": now,
    }
    if extracted_metadata:
        document["extracted_metadata"] = extracted_metadata
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
        "workflow_binding": workflow_binding,
        "checklist_state_path": f"akten/{year}/{matter_id}/checkliste.json",
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
        "workflow_binding": workflow_binding,
        "checklist_summary": summarize_checklist_state(checklist_state),
        "affected_ids": {"person_ids": matter["participant_person_ids"], "document_ids": matter["document_ids"]},
    }

    for person in persons:
        write_json(repo / "personen" / f"{person['person_id']}.json", person)
    attach_document_files(repo, document_id, document, document_title, document_files)
    write_json(repo / "dokumente" / document_id / "metadata.json", document)
    write_json(matter_dir / "akte.json", matter)
    write_json(matter_dir / "checkliste.json", checklist_state)
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


def read_import_proposals(repo: Path) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = []
    if not repo.exists():
        return proposals
    for proposal_file in sorted(import_proposals_dir(repo).glob("*.json")):
        try:
            proposal = read_json(proposal_file)
        except (OSError, json.JSONDecodeError):
            continue
        proposals.append(summarize_import_proposal(proposal))
    proposals.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("proposal_id") or "")), reverse=True)
    return proposals


def summarize_import_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    matter_values = proposal.get("matter_values") if isinstance(proposal.get("matter_values"), dict) else {}
    source_files = proposal.get("source_files") if isinstance(proposal.get("source_files"), list) else []
    return {
        "proposal_id": str(proposal.get("proposal_id") or ""),
        "status": str(proposal.get("status") or "pending"),
        "status_label": IMPORT_STATUS_LABELS.get(str(proposal.get("status") or "pending"), str(proposal.get("status") or "pending")),
        "created_at": str(proposal.get("created_at") or ""),
        "accepted_at": str(proposal.get("accepted_at") or ""),
        "source": str(proposal.get("source") or ""),
        "source_type": str(proposal.get("source_type") or ""),
        "summary": str(proposal.get("summary") or matter_values.get("title") or "Import-Vorschlag"),
        "synthetic_test_data": bool(proposal.get("synthetic_test_data")),
        "matter_id": str(proposal.get("matter_id") or ""),
        "aktenzeichen": str(proposal.get("aktenzeichen") or ""),
        "matter_values": matter_values,
        "source_file_count": len(source_files),
        "source_files": [
            {
                "label": str(file.get("label") or ""),
                "filename": str(file.get("filename") or ""),
                "media_type": str(file.get("media_type") or ""),
                "staged_path": str(file.get("staged_path") or ""),
            }
            for file in source_files
            if isinstance(file, dict)
        ],
        "review": proposal.get("review") if isinstance(proposal.get("review"), dict) else {},
    }


def next_import_proposal_id(repo: Path, title: str, timestamp: str) -> str:
    base = f"IMP-{timestamp[:10].replace('-', '')}-{safe_identifier(title)[:44]}"
    candidate = base
    counter = 2
    while import_proposal_file(repo, candidate).exists():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def stage_import_source_files(repo: Path, proposal_id: str, source_files: Any, synthetic_test_data: Any) -> list[dict[str, Any]]:
    if not isinstance(source_files, list):
        return []
    staged_files: list[dict[str, Any]] = []
    for index, file in enumerate(source_files, start=1):
        if not isinstance(file, dict):
            continue
        label = clean_text(file.get("label") or f"Datei {index}")
        filename = safe_filename(clean_text(file.get("filename") or Path(str(file.get("path") or f"datei-{index}")).name))
        media_type = clean_text(file.get("media_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream")
        staged = {
            "label": label,
            "filename": filename,
            "media_type": media_type,
            "staged_path": "",
        }
        source_path_text = clean_text(file.get("path") or "")
        if source_path_text:
            if not bool(synthetic_test_data):
                raise ValueError("Lokale Dateien dürfen nur für ausdrücklich synthetische Testdaten übernommen werden.")
            source_path = Path(source_path_text).expanduser().resolve()
            if not source_path.is_file():
                raise ValueError(f"Quelldatei nicht gefunden: {source_path}")
            target = repo / "eingang" / "dateien" / proposal_id / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
            staged["staged_path"] = relative_to_repo(repo, target)
        else:
            uploaded = uploaded_file_bytes(file)
            if uploaded is not None:
                if not bool(synthetic_test_data):
                    raise ValueError("Browser-Uploads dürfen nur für ausdrücklich synthetische Testdaten übernommen werden.")
                target = repo / "eingang" / "dateien" / proposal_id / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(uploaded)
                staged["staged_path"] = relative_to_repo(repo, target)
                staged["size_bytes"] = len(uploaded)
        staged_files.append(staged)
    return staged_files


def uploaded_file_bytes(file: dict[str, Any]) -> bytes | None:
    content = file.get("content_base64")
    data_url = file.get("data_url")
    if content is None and data_url is None:
        return None

    encoded = str(content or "")
    if data_url is not None:
        data_url_text = str(data_url)
        if "," not in data_url_text:
            raise ValueError("Ungültige Data-URL für Upload.")
        encoded = data_url_text.split(",", maxsplit=1)[1]

    encoded = "".join(encoded.split())
    if not encoded:
        raise ValueError("Upload-Datei ist leer.")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Upload-Datei ist nicht gültig base64-kodiert.") from exc
    if len(decoded) > MAX_UPLOAD_FILE_BYTES:
        raise ValueError(f"Upload-Datei ist größer als {MAX_UPLOAD_FILE_BYTES // (1024 * 1024)} MB.")
    return decoded


def attach_document_files(
    repo: Path,
    document_id: str,
    document: dict[str, Any],
    document_title: str,
    document_files: list[Any],
) -> None:
    originals: list[dict[str, str]] = []
    for index, file in enumerate(document_files, start=1):
        if not isinstance(file, dict):
            continue
        source_relative = clean_text(file.get("source") or "")
        if not source_relative:
            continue
        source = resolve_repo_relative(repo, source_relative)
        if not source.is_file():
            raise ValueError(f"Import-Datei fehlt: {source_relative}")
        filename = safe_filename(clean_text(file.get("filename") or source.name))
        label = clean_text(file.get("label") or f"Original {index}")
        media_type = clean_text(file.get("media_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream")
        target = repo / "dokumente" / document_id / "original" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        originals.append(
            {
                "label": label,
                "path": relative_to_repo(repo, target),
                "media_type": media_type,
            }
        )
    if originals:
        document["storage"] = {"originals": originals}
        return
    placeholder = repo / "dokumente" / document_id / "original" / f"{safe_identifier(document_title).lower()}.placeholder.txt"
    write_if_missing(placeholder, f"Placeholder für {document_title} ({document_id}).\n")
    document["storage"] = {"original": relative_to_repo(repo, placeholder)}


def append_import_accepted_event(repo: Path, matter_id: str, proposal_id: str, timestamp: str) -> None:
    matter_file = find_matter_file(repo, matter_id)
    if matter_file is None:
        return
    event = {
        "schema_version": "nac.event/v0.1",
        "event_id": f"EVT-{safe_identifier(matter_id)}-IMPORT-{safe_identifier(proposal_id)}",
        "matter_id": matter_id,
        "timestamp": timestamp,
        "actor": "nac_operator",
        "event_type": "import_proposal_accepted",
        "summary": f"Import-Vorschlag {proposal_id} übernommen.",
        "affected_ids": {"proposal_id": proposal_id},
    }
    append_jsonl(matter_file.parent / "ereignisse.jsonl", event)
    append_jsonl(journal_path(repo, timestamp), event)


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
    checklist_state = load_matter_checklist_state(repo, matter)
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
        "workflow_binding": matter.get("workflow_binding") if isinstance(matter.get("workflow_binding"), dict) else {},
        "checklist_summary": summarize_checklist_state(checklist_state),
        "data_classification": str(matter.get("data_classification") or ""),
    }


def build_workflow_binding(
    usecase_slug: str,
    usecase_title: str,
    timestamp: str,
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow_version = clean_text((values or {}).get("workflow_version") or "v1", max_length=64)
    artifacts = workflow_binding_artifacts(usecase_slug)
    revision_source = "|".join(
        f"{artifact['path']}:{artifact['sha256']}" for artifact in artifacts if artifact.get("sha256")
    )
    revision_hash = hashlib.sha256(revision_source.encode("utf-8")).hexdigest()[:16] if revision_source else "untracked"
    return {
        "schema_version": "nac.workflow-binding/v0.1",
        "workflow_id": f"{usecase_slug}:kanzlei-standard",
        "usecase_slug": usecase_slug,
        "usecase_title": usecase_title,
        "workflow_version": workflow_version,
        "workflow_revision_hash": revision_hash,
        "bound_at": timestamp,
        "approval_state": "approved_for_demo",
        "binding_policy": "Akte bleibt auf dieser Workflow-Version, bis ein dokumentierter Versionswechsel erfasst wird.",
        "new_matter_policy": "Neue Akten nutzen die aktuell freigegebene Kanzlei-Workflow-Version.",
        "artifacts": artifacts,
    }


def workflow_binding_artifacts(usecase_slug: str) -> list[dict[str, str]]:
    candidates = [
        ("bpmn", REPO_ROOT / "bpmn" / "usecases" / f"{usecase_slug}.bpmn"),
        ("bpmn", REPO_ROOT / "bpmn" / f"{usecase_slug}.bpmn"),
        ("checklist", REPO_ROOT / "usecases" / usecase_slug / "knowledge-graph.graph.json"),
    ]
    artifacts: list[dict[str, str]] = []
    seen: set[Path] = set()
    for artifact_type, path in candidates:
        resolved = path.resolve()
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        artifacts.append(
            {
                "type": artifact_type,
                "path": relative_to_repo(REPO_ROOT, resolved),
                "sha256": sha256_file(resolved),
            }
        )
    return artifacts


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


CHECKLIST_SECTIONS = (
    ("required_information", "Offene Angaben", "information"),
    ("documents", "Dokumente", "document"),
    ("decisions", "Entscheidungen", "decision"),
    ("gates", "Prüfgates", "gate"),
    ("evidence", "Nachweise", "evidence"),
)


def build_checklist_state(
    usecase_slug: str,
    usecase_title: str,
    timestamp: str,
    workflow_binding: dict[str, Any],
) -> dict[str, Any]:
    graph_path = usecase_knowledge_graph_path(usecase_slug)
    sections: list[dict[str, Any]] = []
    source_sha256 = ""
    source_path = ""
    if graph_path is not None:
        source_sha256 = sha256_file(graph_path)
        source_path = relative_to_repo(REPO_ROOT, graph_path)
        graph = read_json(graph_path)
        case = find_usecase_case(graph, usecase_slug)
        if case is not None:
            for source_key, label, item_type in CHECKLIST_SECTIONS:
                items = build_checklist_items(case.get(source_key), source_key, item_type)
                if items:
                    sections.append({"id": source_key, "label": label, "items": items})
    return {
        "schema_version": "nac.matter-checklist-state/v0.1",
        "usecase_slug": usecase_slug,
        "usecase_title": usecase_title,
        "status": "open",
        "bound_at": timestamp,
        "workflow_id": workflow_binding.get("workflow_id", ""),
        "workflow_version": workflow_binding.get("workflow_version", ""),
        "workflow_revision_hash": workflow_binding.get("workflow_revision_hash", ""),
        "source": {
            "type": "knowledge_graph",
            "path": source_path,
            "sha256": source_sha256,
        },
        "version_policy": "Dieser Checklistenstand ist aktenbezogen eingefroren und folgt nicht automatisch späteren Kanzlei-Workflow-Versionen.",
        "sections": sections,
    }


def usecase_knowledge_graph_path(usecase_slug: str) -> Path | None:
    candidate = REPO_ROOT / "usecases" / usecase_slug / "knowledge-graph.graph.json"
    return candidate if candidate.is_file() else None


def find_usecase_case(graph: dict[str, Any], usecase_slug: str) -> dict[str, Any] | None:
    cases = graph.get("cases")
    if not isinstance(cases, list):
        return None
    for candidate in cases:
        if isinstance(candidate, dict) and candidate.get("slug") == usecase_slug:
            return candidate
    for candidate in cases:
        if isinstance(candidate, dict):
            return candidate
    return None


def build_checklist_items(raw_items: Any, source_key: str, item_type: str) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(raw_items, start=1):
        if not isinstance(raw_item, dict):
            continue
        item_id = clean_text(raw_item.get("id") or f"{source_key}.{index}", max_length=128)
        status = normalize_checklist_status(raw_item.get("status") or "open")
        item = {
            "id": item_id,
            "label": clean_text(raw_item.get("label") or item_id),
            "type": item_type,
            "source_key": source_key,
            "status": status,
            "owner_role": clean_text(raw_item.get("owner_role") or ""),
        }
        question = clean_text(raw_item.get("question") or "")
        if question:
            item["question"] = question
        required_for = raw_item.get("required_for")
        if isinstance(required_for, list):
            item["required_for"] = [clean_text(value, max_length=128) for value in required_for if clean_text(value, max_length=128)]
        options = raw_item.get("options")
        if isinstance(options, list):
            item["options"] = [clean_text(value, max_length=128) for value in options if clean_text(value, max_length=128)]
        items.append(item)
    return items


def normalize_checklist_status(value: Any) -> str:
    status = str(value or "open").strip().lower()
    if status in {"done", "complete", "completed", "closed", "erledigt", "abgeschlossen"}:
        return "completed"
    if status in {"waiting", "blocked", "warten", "wartet"}:
        return "waiting"
    return "open"


def load_matter_checklist_state(repo: Path, matter: dict[str, Any]) -> dict[str, Any]:
    path_text = clean_text(matter.get("checklist_state_path") or "")
    if not path_text:
        return {}
    try:
        checklist_path = resolve_repo_relative(repo, path_text)
    except ValueError:
        return {}
    if not checklist_path.is_file():
        return {}
    try:
        checklist_state = read_json(checklist_path)
    except (OSError, json.JSONDecodeError):
        return {}
    return checklist_state if isinstance(checklist_state, dict) else {}


def summarize_checklist_state(checklist_state: dict[str, Any]) -> dict[str, Any]:
    sections = checklist_state.get("sections") if isinstance(checklist_state.get("sections"), list) else []
    total_count = 0
    open_count = 0
    completed_count = 0
    next_step: dict[str, Any] = {}
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_label = clean_text(section.get("label") or section.get("id") or "")
        items = section.get("items") if isinstance(section.get("items"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            total_count += 1
            status = normalize_checklist_status(item.get("status") or "open")
            if status == "completed":
                completed_count += 1
                continue
            open_count += 1
            if not next_step:
                next_step = {
                    "id": clean_text(item.get("id") or ""),
                    "label": clean_text(item.get("label") or item.get("id") or "Nächster Schritt"),
                    "status": status,
                    "section": section_label,
                    "owner_role": clean_text(item.get("owner_role") or ""),
                }
    return {
        "schema_version": "nac.matter-checklist-summary/v0.1",
        "status": "completed" if total_count and completed_count == total_count else "open",
        "open_count": open_count,
        "completed_count": completed_count,
        "total_count": total_count,
        "next_step": next_step,
        "bound_at": clean_text(checklist_state.get("bound_at") or ""),
        "workflow_version": clean_text(checklist_state.get("workflow_version") or ""),
        "workflow_revision_hash": clean_text(checklist_state.get("workflow_revision_hash") or ""),
        "source_sha256": clean_text((checklist_state.get("source") or {}).get("sha256") if isinstance(checklist_state.get("source"), dict) else ""),
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


def clean_json_payload(value: Any, max_length: int = 4096) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    encoded = json.dumps(value, ensure_ascii=False)
    if len(encoded) > max_length:
        raise ValueError("Metadaten sind zu lang.")
    return json.loads(encoded)


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


def safe_filename(value: str) -> str:
    name = Path(value).name
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return normalized or "datei.bin"


def import_proposals_dir(repo: Path) -> Path:
    return repo / "eingang" / "import-vorschlaege"


def import_proposal_file(repo: Path, proposal_id: str) -> Path:
    return import_proposals_dir(repo) / f"{safe_identifier(proposal_id)}.json"


def resolve_repo_relative(repo: Path, value: str) -> Path:
    candidate = (repo / value).resolve()
    repo_root = repo.resolve()
    if candidate != repo_root and repo_root not in candidate.parents:
        raise ValueError("Pfad liegt außerhalb des Datenrepos.")
    return candidate


def relative_to_repo(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


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
