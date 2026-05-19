from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from notary_kg.editor import build_editor_view


MANIFEST_PATH = ".nac-tenant.json"
DEMO_DATA_ROOT = Path("daten/demo")


@dataclass(frozen=True, slots=True)
class TenantStatus:
    repo: Path
    manifest: dict[str, Any] | None
    git_present: bool
    remote_origin: str | None
    demo_cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": str(self.repo),
            "manifest_present": self.manifest is not None,
            "manifest": self.manifest,
            "git_present": self.git_present,
            "remote_origin": self.remote_origin,
            "demo_cases": self.demo_cases,
        }


def init_tenant_repo(
    repo_path: Path,
    *,
    name: str | None,
    mode: str,
    remote_url: str | None,
    force: bool = False,
) -> dict[str, Any]:
    repo = repo_path.expanduser().resolve()
    repo.mkdir(parents=True, exist_ok=True)

    manifest_file = repo / MANIFEST_PATH
    if manifest_file.exists() and not force:
        raise ValueError(f"Tenant-Manifest existiert bereits: {manifest_file}")

    _ensure_git_repo(repo)
    if remote_url:
        _ensure_origin(repo, remote_url)

    manifest = {
        "schema_version": "nac.tenant/v0.1",
        "name": name or repo.name,
        "mode": mode,
        "data_policy": "synthetic_demo_only" if mode == "demo" else "production_requires_sovereign_git",
        "created_at": _now_utc(),
        "nac_contract": {
            "writes_allowed_from": "nac tenant write-demo",
            "source_of_truth": "NaC product repository",
            "no_secrets_in_git": True,
            "no_pin_or_card_data_in_git": True,
            "no_real_mandate_data_in_demo_mode": True,
        },
        "production_note_de": (
            "Produktive Notariatsdaten dürfen nicht in dieses GitHub-Demorepo. "
            "Für Produktion ist ein geprüfter Sovereign-/DSGVO-Git-Anbieter erforderlich."
        ),
        "remote_url": remote_url,
    }

    _write_json(manifest_file, manifest)
    _write_if_missing(repo / ".gitignore", _gitignore_text(), force=force)
    _write_if_missing(repo / "README.md", _readme_text(manifest), force=force)
    _write_if_missing(repo / "daten" / "README.md", _data_readme_text(), force=force)
    _write_if_missing(repo / "nachweise" / "README.md", _evidence_readme_text(), force=force)
    _write_if_missing(repo / "exports" / "README.md", _exports_readme_text(), force=force)

    return {
        "repo": str(repo),
        "manifest": str(manifest_file),
        "mode": mode,
        "remote_origin": _git_origin(repo),
    }


def tenant_status(repo_path: Path) -> TenantStatus:
    repo = repo_path.expanduser().resolve()
    manifest_file = repo / MANIFEST_PATH
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.is_file() else None
    demo_cases = len(list((repo / DEMO_DATA_ROOT).glob("*/case.json")))
    return TenantStatus(
        repo=repo,
        manifest=manifest,
        git_present=(repo / ".git").exists(),
        remote_origin=_git_origin(repo) if (repo / ".git").exists() else None,
        demo_cases=demo_cases,
    )


def write_demo_case(
    *,
    nac_repo_root: Path,
    tenant_repo: Path,
    slug: str,
    case_id: str | None,
    force: bool = False,
) -> dict[str, Any]:
    repo = tenant_repo.expanduser().resolve()
    manifest = _load_manifest(repo)
    if manifest.get("mode") != "demo":
        raise ValueError("Demo-Schreibläufe sind nur für Tenant-Repos im Modus 'demo' erlaubt.")

    editor_view = build_editor_view(nac_repo_root, slug)
    demo_id = case_id or f"DEMO-{slug}"
    target = repo / DEMO_DATA_ROOT / demo_id / "case.json"
    if target.exists() and not force:
        raise ValueError(f"Demo-Vorgang existiert bereits: {target}")

    payload = {
        "schema_version": "nac.demo-case/v0.1",
        "case_id": demo_id,
        "usecase_slug": slug,
        "title": editor_view["title"],
        "data_classification": "synthetic_demo_only",
        "created_at": _now_utc(),
        "source": {
            "nac_usecase_path": editor_view["usecase_path"],
            "kg_schema_version": editor_view["schema_version"],
        },
        "guardrails": {
            "real_mandate_data_allowed": False,
            "pin_or_card_data_allowed": False,
            "secrets_allowed": False,
            "production_git_required": "sovereign_gdpr_provider",
        },
        "office_view": {
            "open_information": _tab_items(editor_view, "open_information"),
            "documents": _tab_items(editor_view, "documents"),
            "decisions": _tab_items(editor_view, "decisions"),
            "gates_evidence": _gate_groups(editor_view),
        },
    }
    _write_json(target, payload)
    return {
        "repo": str(repo),
        "case_id": demo_id,
        "path": target.relative_to(repo).as_posix(),
        "usecase_slug": slug,
        "data_classification": payload["data_classification"],
    }


def _load_manifest(repo: Path) -> dict[str, Any]:
    manifest_file = repo / MANIFEST_PATH
    if not manifest_file.is_file():
        raise ValueError(f"Kein NaC-Tenant-Manifest gefunden: {manifest_file}")
    return json.loads(manifest_file.read_text(encoding="utf-8"))


def _tab_items(editor_view: dict[str, Any], tab_id: str) -> list[dict[str, Any]]:
    for tab in editor_view["editor_model"]["tabs"]:
        if tab["id"] == tab_id:
            return list(tab.get("items", []))
    return []


def _gate_groups(editor_view: dict[str, Any]) -> list[dict[str, Any]]:
    for tab in editor_view["editor_model"]["tabs"]:
        if tab["id"] == "gates_evidence":
            return list(tab.get("groups", []))
    return []


def _ensure_git_repo(repo: Path) -> None:
    if (repo / ".git").exists():
        return
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)


def _ensure_origin(repo: Path, remote_url: str) -> None:
    current = _git_origin(repo)
    if current is None:
        subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=repo, check=True, capture_output=True, text=True)
        return
    if current != remote_url:
        raise ValueError(f"Git-Remote origin zeigt auf {current}, erwartet {remote_url}")


def _git_origin(repo: Path) -> str | None:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_if_missing(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _gitignore_text() -> str:
    return """# Lokale Arbeitsdateien
.DS_Store
*.tmp
*.log

# Keine Secrets oder echten Mandatsdaten ablegen.
secrets/
private/
"""


def _readme_text(manifest: dict[str, Any]) -> str:
    name = manifest["name"]
    return f"""# {name}

Dieses Repository ist ein getrenntes NaC-Datenziel.

## Zweck

- Demo- und Testdaten aus NaC aufnehmen.
- Vorgangsstände getrennt vom Produktrepo `ofunk/NaC` versionieren.
- Den späteren Wechsel auf einen Sovereign-/DSGVO-Git-Anbieter vorbereiten.

## Grenze

Dieses GitHub-Repository ist nur für synthetische Demo-Daten gedacht. Produktive
Notariatsdaten, PINs, Kartenrohdaten, Zugangsdaten, Registerauszüge,
Ausweisdaten und Mandatsdokumente gehören nicht hierher.

## NaC-Bedienung

```bash
python scripts/nac.py tenant status --repo ../{name}
python scripts/nac.py tenant write-demo immobilienkaufvertrag --repo ../{name}
```
"""


def _data_readme_text() -> str:
    return """# Daten

Hier liegen synthetische Demo-Vorgänge, die über die NaC-CLI geschrieben
werden. Echte Mandatsdaten sind in diesem Demo-Repository verboten.
"""


def _evidence_readme_text() -> str:
    return """# Nachweise

Dieser Ordner ist für synthetische oder metadata-only Nachweise vorgesehen.
Produktive Nachweise gehören in einen geprüften Evidence Store.
"""


def _exports_readme_text() -> str:
    return """# Exporte

Hier können Demo-Exporte abgelegt werden. Produktive Exporte müssen außerhalb
dieses GitHub-Demorepositories verarbeitet werden.
"""
