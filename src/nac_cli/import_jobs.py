from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST_PATH = ".nac-tenant.json"
IMPORT_PROPOSAL_ROOT = Path("eingang/import-vorschlaege")
IMPORT_JOB_ROOT = Path("eingang/jobs")
IMPORT_EXTRACTION_ROOT = Path("eingang/extraktionen")
IMPORT_EVENT_ROOT = Path("journal/import")
DEFAULT_ACTION = "ocr_metadata_extract"


def create_import_job(
    tenant_repo: Path,
    *,
    proposal_id: str,
    requested_by: str,
    action: str = DEFAULT_ACTION,
) -> dict[str, Any]:
    repo = _tenant_repo(tenant_repo)
    _ensure_demo_tenant(repo)
    if action != DEFAULT_ACTION:
        raise ValueError(f"Unbekannte Import-Job-Aktion: {action}")
    proposal = _read_proposal(repo, proposal_id)
    now = _now_utc()
    job_id = _next_job_id(repo, proposal_id, now)
    input_files = _proposal_input_files(repo, proposal)
    job = {
        "schema_version": "nac.import-job/v0.1",
        "job_id": job_id,
        "proposal_id": str(proposal.get("proposal_id") or proposal_id),
        "action": action,
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "requested_by": _clean_text(requested_by or "nac-local-operator-webapp"),
        "input_files": input_files,
        "result_path": _relative(repo, _extraction_path(repo, job_id)),
        "guardrails": {
            "real_mandate_data_allowed": False,
            "pin_or_card_data_allowed": False,
            "secrets_allowed": False,
            "human_review_required": True,
            "writes_only_proposal_metadata": True,
        },
    }
    _write_json(_job_path(repo, job_id), job)
    _append_event(repo, "import_job_created", job)
    return job


def process_import_job(tenant_repo: Path, *, job_id: str, processed_by: str) -> dict[str, Any]:
    repo = _tenant_repo(tenant_repo)
    _ensure_demo_tenant(repo)
    job = _read_job(repo, job_id)
    if job.get("status") not in {"queued", "failed"}:
        raise ValueError(f"Import-Job kann in Status {job.get('status')!r} nicht verarbeitet werden.")
    proposal = _read_proposal(repo, str(job.get("proposal_id") or ""))
    now = _now_utc()
    job["status"] = "processing"
    job["updated_at"] = now
    job["processed_by"] = _clean_text(processed_by or "codex")
    _write_json(_job_path(repo, str(job["job_id"])), job)

    extraction = _build_extraction(repo, job, proposal, now)
    _write_json(_extraction_path(repo, str(job["job_id"])), extraction)
    job["status"] = "completed"
    job["updated_at"] = now
    job["extraction_path"] = _relative(repo, _extraction_path(repo, str(job["job_id"])))
    _write_json(_job_path(repo, str(job["job_id"])), job)
    _append_event(repo, "import_job_completed", job)
    return {"schema_version": "nac.import-job-process/v0.1", "job": job, "extraction": extraction}


def apply_import_job_result(tenant_repo: Path, *, job_id: str, applied_by: str) -> dict[str, Any]:
    repo = _tenant_repo(tenant_repo)
    _ensure_demo_tenant(repo)
    job = _read_job(repo, job_id)
    if job.get("status") not in {"completed", "applied"}:
        raise ValueError("Import-Job braucht ein fertiges Extraktionsergebnis.")
    extraction = _read_json(_extraction_path(repo, str(job["job_id"])))
    proposal = _read_proposal(repo, str(job.get("proposal_id") or ""))
    matter_values = proposal.setdefault("matter_values", {})
    if not isinstance(matter_values, dict):
        raise ValueError("Import-Vorschlag hat keine gültigen matter_values.")
    metadata = matter_values.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        matter_values["metadata"] = metadata
    metadata.update(extraction.get("metadata") if isinstance(extraction.get("metadata"), dict) else {})
    metadata["ocr_review_status"] = "ready_for_human_review"
    metadata["ocr_job_id"] = str(job["job_id"])
    metadata["ocr_extraction_method"] = str(extraction.get("method") or "")
    metadata["ocr_text_preview"] = str(extraction.get("ocr_text") or "")[:240]
    proposal["latest_extraction_job_id"] = str(job["job_id"])
    proposal["latest_extraction_path"] = _relative(repo, _extraction_path(repo, str(job["job_id"])))
    review = proposal.setdefault("review", {})
    if not isinstance(review, dict):
        review = {}
        proposal["review"] = review
    review["requires_human_confirmation"] = True
    review["latest_extraction_status"] = "ready_for_human_review"
    review["latest_extraction_applied_by"] = _clean_text(applied_by or "nac-local-operator-webapp")
    proposal["status"] = "pending"
    _write_json(_proposal_path(repo, str(proposal["proposal_id"])), proposal)

    now = _now_utc()
    job["status"] = "applied"
    job["updated_at"] = now
    job["applied_by"] = _clean_text(applied_by or "nac-local-operator-webapp")
    _write_json(_job_path(repo, str(job["job_id"])), job)
    _append_event(repo, "import_job_result_applied", job)
    return {
        "schema_version": "nac.import-job-apply/v0.1",
        "job": job,
        "proposal": proposal,
        "extraction": extraction,
    }


def import_job_status(tenant_repo: Path, *, job_id: str | None = None) -> dict[str, Any]:
    repo = _tenant_repo(tenant_repo)
    _ensure_demo_tenant(repo)
    jobs = [_summarize_job(repo, _read_job(repo, job_id))] if job_id else _list_job_summaries(repo)
    counts: dict[str, int] = {
        "queued": 0,
        "processing": 0,
        "completed": 0,
        "failed": 0,
        "applied": 0,
        "total": 0,
    }
    for job in jobs:
        status = str(job.get("status") or "queued")
        counts[status] = counts.get(status, 0) + 1
        counts["total"] += 1
    return {
        "schema_version": "nac.import-job-status/v0.1",
        "repo": str(repo),
        "counts": counts,
        "jobs": jobs,
    }


def _build_extraction(repo: Path, job: dict[str, Any], proposal: dict[str, Any], timestamp: str) -> dict[str, Any]:
    matter_values = proposal.get("matter_values") if isinstance(proposal.get("matter_values"), dict) else {}
    metadata = matter_values.get("metadata") if isinstance(matter_values.get("metadata"), dict) else {}
    input_files = job.get("input_files") if isinstance(job.get("input_files"), list) else []
    participant = str(matter_values.get("participant_name") or matter_values.get("client_name") or "").strip()
    document_title = str(matter_values.get("document_title") or proposal.get("summary") or "Eingangsdokument").strip()
    filenames = ", ".join(str(file.get("filename") or file.get("path") or "") for file in input_files if isinstance(file, dict))
    ocr_text = f"Synthetische OCR-Zusammenfassung: {document_title}"
    if participant:
        ocr_text += f" für {participant}"
    if filenames:
        ocr_text += f". Dateien: {filenames}"
    fields = []
    for key, value in sorted(metadata.items()):
        if isinstance(value, (str, int, float, bool)) and str(value):
            fields.append(
                {
                    "field": key,
                    "value": value,
                    "confidence": 0.95 if metadata.get("extraction_source") == "synthetic_demo_profile" else 0.7,
                    "source": "proposal_metadata",
                }
            )
    if participant and "participant_name" not in metadata:
        fields.append({"field": "participant_name", "value": participant, "confidence": 0.8, "source": "proposal"})
    extraction = {
        "schema_version": "nac.import-extraction/v0.1",
        "extraction_id": f"EXT-{job['job_id']}",
        "job_id": str(job["job_id"]),
        "proposal_id": str(job["proposal_id"]),
        "status": "ready_for_review",
        "extracted_at": timestamp,
        "method": "nac-local-deterministic-demo",
        "manual_review_required": True,
        "ocr_text": ocr_text,
        "metadata": dict(metadata),
        "fields": fields,
        "sources": [
            {
                "path": str(file.get("path") or ""),
                "filename": str(file.get("filename") or ""),
                "sha256": str(file.get("sha256") or ""),
            }
            for file in input_files
            if isinstance(file, dict)
        ],
        "guardrails": {
            "real_mandate_data_allowed": False,
            "pin_or_card_data_allowed": False,
            "secrets_allowed": False,
            "human_review_required": True,
        },
    }
    return extraction


def _proposal_input_files(repo: Path, proposal: dict[str, Any]) -> list[dict[str, Any]]:
    source_files = proposal.get("source_files") if isinstance(proposal.get("source_files"), list) else []
    inputs = []
    for file in source_files:
        if not isinstance(file, dict):
            continue
        rel_path = _clean_text(file.get("staged_path") or "")
        if not rel_path:
            continue
        path = _resolve_repo_relative(repo, rel_path)
        if not path.is_file():
            raise ValueError(f"Import-Datei fehlt: {rel_path}")
        inputs.append(
            {
                "label": _clean_text(file.get("label") or ""),
                "filename": _clean_text(file.get("filename") or path.name),
                "media_type": _clean_text(file.get("media_type") or "application/octet-stream"),
                "path": _relative(repo, path),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    if not inputs:
        raise ValueError("Import-Vorschlag enthält keine gestagten Dateien.")
    return inputs


def _summarize_job(repo: Path, job: dict[str, Any]) -> dict[str, Any]:
    summary = dict(job)
    extraction_path = _extraction_path(repo, str(job.get("job_id") or ""))
    if extraction_path.is_file():
        extraction = _read_json(extraction_path)
        summary["extraction"] = {
            "status": str(extraction.get("status") or ""),
            "path": _relative(repo, extraction_path),
            "metadata_field_count": len(
                extraction.get("metadata") if isinstance(extraction.get("metadata"), dict) else {}
            ),
            "ocr_text_preview": str(extraction.get("ocr_text") or "")[:160],
        }
    return summary


def _list_job_summaries(repo: Path) -> list[dict[str, Any]]:
    jobs = []
    for path in sorted((repo / IMPORT_JOB_ROOT).glob("*.json")):
        try:
            jobs.append(_summarize_job(repo, _read_json(path)))
        except (OSError, ValueError):
            continue
    jobs.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("job_id") or "")), reverse=True)
    return jobs


def _ensure_demo_tenant(repo: Path) -> dict[str, Any]:
    manifest = _read_json(repo / MANIFEST_PATH)
    if manifest.get("mode") != "demo":
        raise ValueError("Import-Jobs schreiben aktuell nur in Demo-Datenrepos.")
    return manifest


def _read_proposal(repo: Path, proposal_id: str) -> dict[str, Any]:
    proposal = _read_json(_proposal_path(repo, proposal_id))
    if proposal.get("status") != "pending":
        raise ValueError("Nur offene Import-Vorschläge können verarbeitet werden.")
    return proposal


def _read_job(repo: Path, job_id: str | None) -> dict[str, Any]:
    if not job_id:
        raise ValueError("Pflichtfeld fehlt: job_id")
    return _read_json(_job_path(repo, job_id))


def _next_job_id(repo: Path, proposal_id: str, timestamp: str) -> str:
    base = f"JOB-{timestamp[:10].replace('-', '')}-{_safe_identifier(proposal_id)[:42]}"
    candidate = base
    counter = 2
    while _job_path(repo, candidate).exists():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def _proposal_path(repo: Path, proposal_id: str) -> Path:
    return repo / IMPORT_PROPOSAL_ROOT / f"{_safe_identifier(proposal_id)}.json"


def _job_path(repo: Path, job_id: str) -> Path:
    return repo / IMPORT_JOB_ROOT / f"{_safe_identifier(job_id)}.json"


def _extraction_path(repo: Path, job_id: str) -> Path:
    return repo / IMPORT_EXTRACTION_ROOT / f"{_safe_identifier(job_id)}.json"


def _append_event(repo: Path, event_type: str, job: dict[str, Any]) -> None:
    timestamp = str(job.get("updated_at") or job.get("created_at") or _now_utc())
    event = {
        "schema_version": "nac.import-event/v0.1",
        "event_id": f"EVT-{_safe_identifier(str(job.get('job_id') or 'JOB'))}-{_safe_identifier(event_type)}",
        "timestamp": timestamp,
        "event_type": event_type,
        "job_id": str(job.get("job_id") or ""),
        "proposal_id": str(job.get("proposal_id") or ""),
        "status": str(job.get("status") or ""),
    }
    path = repo / IMPORT_EVENT_ROOT / timestamp[:4] / timestamp[5:7] / f"{timestamp[:10]}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _tenant_repo(tenant_repo: Path) -> Path:
    return tenant_repo.expanduser().resolve()


def _resolve_repo_relative(repo: Path, value: str) -> Path:
    candidate = (repo / value).resolve()
    repo_root = repo.resolve()
    if candidate != repo_root and repo_root not in candidate.parents:
        raise ValueError("Pfad liegt außerhalb des Datenrepos.")
    return candidate


def _relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"JSON-Datei fehlt: {_clean_text(str(path))}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON-Datei ist ungültig: {_clean_text(str(path))}") from exc


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_identifier(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "")).strip("-").upper()
    return normalized or "UNBENANNT"


def _clean_text(value: Any, max_length: int = 512) -> str:
    text = str(value or "").strip()
    if len(text) > max_length:
        raise ValueError("Eingabewert ist zu lang.")
    if any(ord(char) < 32 and char not in {"\t"} for char in text):
        raise ValueError("Eingabewert enthält Steuerzeichen.")
    return text


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
