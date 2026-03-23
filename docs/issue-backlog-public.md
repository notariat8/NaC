# Issue Backlog: Public Release

Diese Liste ist als Vorlage fuer GitHub Issues gedacht.

## P0 (Blocker, erledigt)

### 1) Lizenz fuer Public Nutzung festlegen - erledigt
- **Typ:** Governance
- **Status:** erledigt
- **Umsetzung:** `LICENSE` (GPL-3.0) angelegt
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

### 4) PDF Export fuer Unternehmensdokumentation automatisieren - erledigt
- **Typ:** DevEx
- **Status:** erledigt
- **Umsetzung:** `.github/workflows/docs-pdf-export.yml` angelegt
- **Akzeptanzkriterien:**
  - Workflow fuer Markdown -> PDF
  - PDFs als Artefakt
  - Exportdoku in `docs/`

## P1 (wichtige Verbesserungen, offen)

### 5) CI Check fuer Technology Policy
- **Typ:** Compliance Automation
- **Akzeptanzkriterien:**
  - Check blockiert nicht erlaubte Technikpfade
  - Check prueft Cross-IDE Sync Dokumente

### 6) Release Checklist fuer Prozessversionen
- **Typ:** Release Governance
- **Akzeptanzkriterien:**
  - Checkliste fuer Tag/Release
  - Verweis auf Audit-/Nachweisartefakte

### 7) Branchensets erweitern
- **Typ:** Fachinhalt
- **Akzeptanzkriterien:**
  - Onboarding fuer Softwareunternehmen
  - Beispielprozesse fuer Notariat/Steuerbuero
