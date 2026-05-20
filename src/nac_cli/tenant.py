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
MATTER_ROOT = Path("akten")
PERSON_ROOT = Path("personen")
DOCUMENT_ROOT = Path("dokumente")
JOURNAL_ROOT = Path("journal")
INDEX_ROOT = Path("index")
OFFICE_ROOT = Path("notariat")


@dataclass(frozen=True, slots=True)
class TenantStatus:
    repo: Path
    manifest: dict[str, Any] | None
    git_present: bool
    remote_origin: str | None
    demo_cases: int
    matters: int
    persons: int
    documents: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": str(self.repo),
            "manifest_present": self.manifest is not None,
            "manifest": self.manifest,
            "git_present": self.git_present,
            "remote_origin": self.remote_origin,
            "demo_cases": self.demo_cases,
            "matters": self.matters,
            "persons": self.persons,
            "documents": self.documents,
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
        "schema_version": "nac.tenant/v0.2",
        "name": name or repo.name,
        "mode": mode,
        "data_policy": "synthetic_full_case_model" if mode == "demo" else "production_full_case_model",
        "created_at": _now_utc(),
        "nac_contract": {
            "writes_allowed_from": ["nac tenant write-demo", "nac tenant write-sample-akte"],
            "source_of_truth": "NaC product repository",
            "record_layout": "id_pointer_json_plus_binary_blobs",
            "no_real_mandate_data_in_demo_mode": True,
        },
        "data_model": {
            "matters": "akten/<jahr>/<akten_id>/akte.json",
            "persons": "personen/<person_id>.json",
            "documents": "dokumente/<document_id>/metadata.json",
            "binary_files": "dokumente/<document_id>/original/*",
            "events": "akten/<jahr>/<akten_id>/ereignisse.jsonl",
            "global_journal": "journal/<jahr>/<monat>/<datum>.jsonl",
            "indices": "index/*.json",
        },
        "production_note_de": "Produktive Notariatsdaten brauchen einen geprüften Sovereign-/DSGVO-Git-Anbieter.",
        "remote_url": remote_url,
    }

    _write_json(manifest_file, manifest)
    _write_if_missing(repo / ".gitignore", _gitignore_text(), force=force)
    _write_if_missing(repo / "README.md", _readme_text(manifest), force=force)
    _write_if_missing(repo / "MODELL.md", _model_text(), force=force)
    _write_if_missing(repo / "daten" / "README.md", _data_readme_text(), force=force)
    _write_if_missing(repo / "akten" / "README.md", _matters_readme_text(), force=force)
    _write_if_missing(repo / "personen" / "README.md", _persons_readme_text(), force=force)
    _write_if_missing(repo / "dokumente" / "README.md", _documents_readme_text(), force=force)
    _write_if_missing(repo / "nachweise" / "README.md", _evidence_readme_text(), force=force)
    _write_if_missing(repo / "exports" / "README.md", _exports_readme_text(), force=force)
    _write_if_missing(repo / "journal" / "README.md", _journal_readme_text(), force=force)
    _write_if_missing(repo / "index" / "README.md", _index_readme_text(), force=force)
    _write_if_missing(repo / "notariat" / "README.md", _office_readme_text(), force=force)

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
    matters = len(list((repo / MATTER_ROOT).glob("*/*/akte.json")))
    persons = len(list((repo / PERSON_ROOT).glob("*.json")))
    documents = len(list((repo / DOCUMENT_ROOT).glob("*/metadata.json")))
    return TenantStatus(
        repo=repo,
        manifest=manifest,
        git_present=(repo / ".git").exists(),
        remote_origin=_git_origin(repo) if (repo / ".git").exists() else None,
        demo_cases=demo_cases,
        matters=matters,
        persons=persons,
        documents=documents,
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


def write_sample_matter(
    *,
    tenant_repo: Path,
    matter_id: str | None,
    force: bool = False,
) -> dict[str, Any]:
    repo = tenant_repo.expanduser().resolve()
    manifest = _load_manifest(repo)
    if manifest.get("mode") != "demo":
        raise ValueError("Musterakten werden nur im Demo-Modus erzeugt.")

    akten_id = matter_id or "UVZ-2026-0001"
    year = "2026"
    matter_dir = repo / MATTER_ROOT / year / akten_id
    matter_file = matter_dir / "akte.json"
    if matter_file.exists() and not force:
        raise ValueError(f"Musterakte existiert bereits: {matter_file}")

    now = _now_utc()
    office = {
        "schema_version": "nac.office/v0.1",
        "office_id": "NOT-DEMO-0001",
        "name": "Demo-Notariat Funktion8",
        "jurisdiction": "DE",
        "notaries": [
            {
                "person_id": "PER-DEMO-NOTAR-OFUNK",
                "display_name": "Notar Dr. Otto Funk",
                "role": "notary",
            }
        ],
    }
    persons = [
        {
            "schema_version": "nac.person/v0.1",
            "person_id": "PER-DEMO-NOTAR-OFUNK",
            "type": "natural_person",
            "display_name": "Notar Dr. Otto Funk",
            "names": {"given": "Otto", "family": "Funk"},
            "roles": ["notary"],
            "data_classification": "synthetic_personal_data",
        },
        {
            "schema_version": "nac.person/v0.1",
            "person_id": "PER-DEMO-VERKAEUFER-ANNA-BERGER",
            "type": "natural_person",
            "display_name": "Anna Berger",
            "names": {"given": "Anna", "family": "Berger"},
            "roles": ["seller"],
            "data_classification": "synthetic_personal_data",
        },
        {
            "schema_version": "nac.person/v0.1",
            "person_id": "PER-DEMO-KAEUFER-BEN-LANGE",
            "type": "natural_person",
            "display_name": "Ben Lange",
            "names": {"given": "Ben", "family": "Lange"},
            "roles": ["buyer"],
            "data_classification": "synthetic_personal_data",
        },
    ]
    documents = [
        {
            "schema_version": "nac.document/v0.1",
            "document_id": "DOC-DEMO-2026-0001-GRUNDBUCH",
            "matter_id": akten_id,
            "title": "Grundbuchauszug Demo",
            "document_type": "grundbuchauszug",
            "media_type": "application/pdf",
            "data_classification": "synthetic_register_extract",
            "subject_person_ids": [
                "PER-DEMO-VERKAEUFER-ANNA-BERGER",
                "PER-DEMO-KAEUFER-BEN-LANGE",
            ],
            "storage": {
                "original": "dokumente/DOC-DEMO-2026-0001-GRUNDBUCH/original/grundbuchauszug-demo.pdf.placeholder.txt",
                "preview": "dokumente/DOC-DEMO-2026-0001-GRUNDBUCH/preview/grundbuchauszug-demo.jpg.placeholder.txt",
            },
            "created_at": now,
        },
        {
            "schema_version": "nac.document/v0.1",
            "document_id": "DOC-DEMO-2026-0001-AUSWEIS-VERKAEUFER",
            "matter_id": akten_id,
            "title": "Ausweiskopie Verkäuferin Demo",
            "document_type": "id_document_scan",
            "media_type": "image/jpeg",
            "data_classification": "synthetic_identity_document",
            "subject_person_ids": ["PER-DEMO-VERKAEUFER-ANNA-BERGER"],
            "storage": {
                "original": "dokumente/DOC-DEMO-2026-0001-AUSWEIS-VERKAEUFER/original/ausweis-verkaeufer-demo.jpg.placeholder.txt"
            },
            "created_at": now,
        },
    ]
    matter = {
        "schema_version": "nac.matter/v0.1",
        "matter_id": akten_id,
        "aktenzeichen": "UVZ 1/2026",
        "title": "Immobilienkaufvertrag Berger/Lange",
        "case_type": "immobilienkaufvertrag",
        "status": "intake",
        "opened_at": now,
        "notary_person_id": "PER-DEMO-NOTAR-OFUNK",
        "participant_person_ids": [
            "PER-DEMO-VERKAEUFER-ANNA-BERGER",
            "PER-DEMO-KAEUFER-BEN-LANGE",
        ],
        "document_ids": [document["document_id"] for document in documents],
        "event_log": f"akten/{year}/{akten_id}/ereignisse.jsonl",
        "data_classification": "synthetic_full_case",
        "pointers": {
            "persons": "personen/<person_id>.json",
            "documents": "dokumente/<document_id>/metadata.json",
            "binary_files": "dokumente/<document_id>/original/*",
        },
    }
    relationships = {
        "schema_version": "nac.matter-participants/v0.1",
        "matter_id": akten_id,
        "participants": [
            {"person_id": "PER-DEMO-NOTAR-OFUNK", "role": "notary", "signing_required": True},
            {"person_id": "PER-DEMO-VERKAEUFER-ANNA-BERGER", "role": "seller", "signing_required": True},
            {"person_id": "PER-DEMO-KAEUFER-BEN-LANGE", "role": "buyer", "signing_required": True},
        ],
    }
    matter_documents = {
        "schema_version": "nac.matter-documents/v0.1",
        "matter_id": akten_id,
        "documents": [
            {
                "document_id": document["document_id"],
                "role": "source_document" if document["document_type"] == "grundbuchauszug" else "identity_evidence",
                "status": "received",
            }
            for document in documents
        ],
    }
    event = {
        "schema_version": "nac.event/v0.1",
        "event_id": "EVT-DEMO-2026-0001-INTAKE",
        "matter_id": akten_id,
        "timestamp": now,
        "actor_person_id": "PER-DEMO-NOTAR-OFUNK",
        "event_type": "matter_created",
        "summary": "Musterakte für Immobilienkaufvertrag angelegt.",
        "affected_ids": {
            "person_ids": matter["participant_person_ids"],
            "document_ids": matter["document_ids"],
        },
    }

    _write_json(repo / OFFICE_ROOT / "stammdaten.json", office)
    for person in persons:
        _write_json(repo / PERSON_ROOT / f"{person['person_id']}.json", person)
    for document in documents:
        document_dir = repo / DOCUMENT_ROOT / document["document_id"]
        _write_json(document_dir / "metadata.json", document)
        for rel_path in document["storage"].values():
            _write_if_missing(repo / rel_path, _placeholder_text(document), force=force)
    _write_json(matter_file, matter)
    _write_json(matter_dir / "beteiligte.json", relationships)
    _write_json(matter_dir / "dokumente.json", matter_documents)
    _write_json(repo / INDEX_ROOT / "akten.json", {"schema_version": "nac.index-matters/v0.1", "matters": [matter]})
    _write_json(
        repo / INDEX_ROOT / "personen.json",
        {
            "schema_version": "nac.index-persons/v0.1",
            "persons": [
                {"person_id": person["person_id"], "display_name": person["display_name"], "roles": person["roles"]}
                for person in persons
            ],
        },
    )
    _write_json(
        repo / INDEX_ROOT / "dokumente.json",
        {
            "schema_version": "nac.index-documents/v0.1",
            "documents": [
                {
                    "document_id": document["document_id"],
                    "matter_id": document["matter_id"],
                    "title": document["title"],
                    "document_type": document["document_type"],
                }
                for document in documents
            ],
        },
    )
    _append_jsonl(matter_dir / "ereignisse.jsonl", event, force=force)
    _append_jsonl(repo / JOURNAL_ROOT / "2026" / "05" / "2026-05-19.jsonl", event, force=force)

    return {
        "repo": str(repo),
        "matter_id": akten_id,
        "path": matter_file.relative_to(repo).as_posix(),
        "person_count": len(persons),
        "document_count": len(documents),
        "data_classification": matter["data_classification"],
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


def _append_jsonl(path: Path, payload: dict[str, Any], *, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False)
    if force or not path.exists():
        path.write_text(line + "\n", encoding="utf-8")
        return
    existing = path.read_text(encoding="utf-8")
    if line not in existing.splitlines():
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def _placeholder_text(document: dict[str, Any]) -> str:
    return (
        f"Placeholder für {document['title']} ({document['document_id']}).\n"
        "In einer echten Produktivumgebung liegt hier die Binärdatei, zum Beispiel PDF oder JPG.\n"
        "Die Metadaten und Pointer stehen in metadata.json.\n"
    )


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

Dieses Repository ist ein getrenntes NaC-Datenziel für Akten, Beteiligte,
Dokumente, Ereignisse und Exporte.

## Zweck

- Akten- und Testdaten aus NaC aufnehmen.
- Vorgangsstände getrennt vom Produktrepo `ofunk/NaC` versionieren.
- Viele Akten, viele Bearbeiter und viele Generationen lesbar halten.
- Den späteren Wechsel auf einen Sovereign-/DSGVO-Git-Anbieter ermöglichen.

## Modell

- `akten/`: eine Akte pro Ordner mit `akte.json`, Beteiligten, Dokumentliste und Ereignissen.
- `personen/`: eine JSON-Datei pro Person oder Organisation.
- `dokumente/`: Metadaten plus Binärdateien wie PDF, JPG oder Scans.
- `journal/`: chronologische Ereignisse als JSONL.
- `index/`: kleine Leselisten für Suche, Webapp und Codex.

Details stehen in [MODELL.md](MODELL.md).

## NaC-Bedienung

```bash
python scripts/nac.py tenant status --repo ../{name}
python scripts/nac.py tenant write-demo immobilienkaufvertrag --repo ../{name}
python scripts/nac.py tenant write-sample-akte --repo ../{name}
```
"""


def _model_text() -> str:
    return """# NaC-Datenmodell

Dieses Repository speichert Akten als kleine, stabile JSON-Datensätze mit IDs
und Pointer-Beziehungen. Große oder binäre Inhalte liegen als Dateien neben den
Metadaten.

## Leitidee

- JSON hält die fachliche Struktur lesbar.
- IDs verbinden Akte, Personen, Dokumente und Ereignisse.
- Binärdateien wie PDF, JPG oder Scans bleiben als Dateien erhalten.
- Indizes sind Ableitungen für Webapp, Suche und Codex.
- Ereignisse werden zusätzlich als JSONL journalisiert.

## Kernobjekte

| Objekt | Pfad | Zweck |
| --- | --- | --- |
| Akte | `akten/<jahr>/<akten_id>/akte.json` | Aktenzeichen, Status, Notar, Beteiligte, Dokumente, Pointer. |
| Beteiligte | `personen/<person_id>.json` | Person, Organisation, Rollen und Stammdaten. |
| Dokument | `dokumente/<document_id>/metadata.json` | Titel, Typ, Aktenbezug, Dateipfade, Klassifikation. |
| Binärdatei | `dokumente/<document_id>/original/*` | PDF, JPG, Scan oder andere Originaldatei. |
| Aktenereignis | `akten/<jahr>/<akten_id>/ereignisse.jsonl` | Chronologie innerhalb einer Akte. |
| Journal | `journal/<jahr>/<monat>/<datum>.jsonl` | Repo-weite Ereignisfolge. |
| Index | `index/*.json` | Leselisten für Webapp, Suche und Codex. |

## Pointer

Eine Akte speichert nicht alle Person- oder Dokumentdaten inline. Sie verweist
auf IDs:

```json
{
  "matter_id": "UVZ-2026-0001",
  "participant_person_ids": ["PER-DEMO-VERKAEUFER-ANNA-BERGER"],
  "document_ids": ["DOC-DEMO-2026-0001-GRUNDBUCH"]
}
```

Codex und die Webapp lesen zuerst `akte.json` und laden danach die referenzierten
Personen, Dokumente und Ereignisse.
"""


def _data_readme_text() -> str:
    return """# Daten

Legacy-Demoausgaben aus der frühen NaC-CLI liegen unter `daten/demo`. Das
führende Aktenmodell liegt in `akten/`, `personen/`, `dokumente/`, `journal/`
und `index/`.
"""


def _matters_readme_text() -> str:
    return """# Akten

Jede Akte liegt unter `akten/<jahr>/<akten_id>/`. Der Kern ist `akte.json`.
Weitere Dateien verbinden Beteiligte, Dokumente und Ereignisse.
"""


def _persons_readme_text() -> str:
    return """# Personen Und Organisationen

Eine Datei pro Person oder Organisation. Akten verweisen über `person_id` auf
diese Datensätze.
"""


def _documents_readme_text() -> str:
    return """# Dokumente

Jedes Dokument hat einen eigenen Ordner mit `metadata.json`. Originale,
Vorschauen und abgeleitete Dateien liegen darunter als normale Dateien.
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


def _journal_readme_text() -> str:
    return """# Journal

Das Journal enthält chronologische Ereignisse als JSONL. Jede Zeile ist ein
eigenes Ereignisobjekt.
"""


def _index_readme_text() -> str:
    return """# Index

Indizes sind ableitbare Leselisten für Webapp, Suche und Codex. Die Wahrheit
liegt in den Akten-, Personen- und Dokumentdateien.
"""


def _office_readme_text() -> str:
    return """# Notariat

Hier liegen Stammdaten des Notariats, Rollen und spätere Konfigurationen für
die lokale Bürooberfläche.
"""
