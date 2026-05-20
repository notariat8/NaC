# Issue Backlog: Public Release

Diese Liste ist als Vorlage für GitHub Issues gedacht.

## P0 (Blocker, erledigt)

### 1) Lizenz für Public Nutzung festlegen - erledigt
- **Typ:** Governance
- **Status:** erledigt
- **Umsetzung:** `AGPL-3.0-or-later` für Software und `CC-BY-4.0` für Dokumentation festgelegt
- **Akzeptanzkriterien:**
  - Lizenzentscheidung dokumentiert
  - `LICENSE` im Repo
  - Hinweis im `README.md`

### 2) Community Basisdateien finalisieren - erledigt
- **Typ:** Governance
- **Status:** erledigt
- **Umsetzung:** `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` angelegt
- **Akzeptanzkriterien:**
  - `CONTRIBUTING.md` vorhanden
  - `CODE_OF_CONDUCT.md` vorhanden
  - `SECURITY.md` vorhanden

### 3) BPMN-2.0 Referenzmodelle bereitstellen - erledigt
- **Typ:** Fachmodell
- **Status:** erledigt
- **Umsetzung:** `bpmn/invoice-process.bpmn`, `bpmn/bookkeeping-process.bpmn` angelegt
- **Akzeptanzkriterien:**
  - Mindestens `invoice.bpmn` und `bookkeeping.bpmn`
  - Bezug aus Doku und Python-Engine dokumentiert

### 4) PDF Export für Unternehmensdokumentation automatisieren - erledigt
- **Typ:** DevEx
- **Status:** erledigt
- **Umsetzung:** `.github/workflows/docs-pdf-export.yml` angelegt
- **Akzeptanzkriterien:**
  - Workflow für Markdown -> PDF
  - PDFs als Artefakt
  - Exportdoku in `docs/de/`

## P1 (wichtige Verbesserungen, offen)

### 5) CI Check für Technology Policy
- **Typ:** Compliance Automation
- **Akzeptanzkriterien:**
  - Check blockiert nicht erlaubte Technikpfade
  - Check prüft Cross-IDE Sync Dokumente

### 6) Release Checklist für Prozessversionen
- **Typ:** Release Governance
- **Akzeptanzkriterien:**
  - Checkliste für Tag/Release
  - Verweis auf Audit-/Nachweisartefakte

### 7) Branchensets erweitern
- **Typ:** Fachinhalt
- **Akzeptanzkriterien:**
  - Onboarding für Softwareunternehmen
  - Beispielprozesse für Notariat/Steuerbüro
