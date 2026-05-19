from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tenant import tenant_status


QMS_ROOT = Path("qms")
REQUIRED_FILES = (
    "README.md",
    "quality-policy.md",
    "quality-objectives.json",
    "process-map.md",
    "roles-raci.json",
    "iso9001-mapping.md",
    "audit-program.md",
    "nonconformities.schema.json",
    "management-review.md",
)


@dataclass(frozen=True, slots=True)
class QmsStatus:
    repo_root: Path
    files_present: dict[str, bool]
    quality_objectives: int
    raci_roles: int
    iso_mapping_rows: int
    evidence_repo: str | None
    evidence_counts: dict[str, int]

    @property
    def ok(self) -> bool:
        return all(self.files_present.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "nac.qms.status/v0.1",
            "repo_root": str(self.repo_root),
            "ok": self.ok,
            "files_present": self.files_present,
            "quality_objectives": self.quality_objectives,
            "raci_roles": self.raci_roles,
            "iso_mapping_rows": self.iso_mapping_rows,
            "evidence_repo": self.evidence_repo,
            "evidence_counts": self.evidence_counts,
        }


def qms_status(repo_root: Path, evidence_repo: Path | None = None) -> QmsStatus:
    qms_root = repo_root / QMS_ROOT
    files_present = {name: (qms_root / name).is_file() for name in REQUIRED_FILES}
    objectives = _read_json(qms_root / "quality-objectives.json").get("objectives", [])
    roles = _read_json(qms_root / "roles-raci.json").get("roles", [])
    mapping_rows = _count_mapping_rows(qms_root / "iso9001-mapping.md")
    evidence_counts: dict[str, int] = {}
    if evidence_repo is not None:
        status = tenant_status(evidence_repo)
        evidence_counts = {
            "demo_cases": status.demo_cases,
            "matters": status.matters,
            "persons": status.persons,
            "documents": status.documents,
        }
    return QmsStatus(
        repo_root=repo_root,
        files_present=files_present,
        quality_objectives=len(objectives) if isinstance(objectives, list) else 0,
        raci_roles=len(roles) if isinstance(roles, list) else 0,
        iso_mapping_rows=mapping_rows,
        evidence_repo=str(evidence_repo.expanduser().resolve()) if evidence_repo else None,
        evidence_counts=evidence_counts,
    )


def read_qms_text(repo_root: Path, relative_path: str) -> str:
    path = repo_root / QMS_ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _count_mapping_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    rows = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and " | " in line and "---" not in line and "ISO-9001" not in line:
            rows += 1
    return rows
