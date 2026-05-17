# NoC Plugins fuer regulierte Branchen

Dieser Ordner enthaelt installierbare repo-lokale Codex-Plugins fuer NoC-
Workflows in regulierten Branchen. Die erste Suite fokussiert Anwaltskanzleien,
Notariate, Steuer-Workflows und Cloud-Nachweisbetrieb.

## Installierbare Plugins

- `noc-regulated-core`: gemeinsame Schutzplanken fuer regulierte Workflows.
- `noc-idaas`: Begleiter fuer deutsche eID-Pruefung und IAM-Projektions-Readiness.
- `noc-cyberjack-rfid`: lokales Karten- und SAK-lite-Gate vor dem XNP-Login.
- `noc-bnotk-xnp`: lokales XNP-Authentifizierungsgate nach Karten-Readiness.
- `noc-pkcs7-certbundle`: lokaler PKCS#7/P7B-Zertifikatsbuendel-Nachweis ohne Signatur.
- `noc-handelsregister`: HRA-first-Readiness fuer Online-Registeranmeldungen nach Modusentscheidung.
- `noc-bea-portal`: beA-Workflow- und Nachweisbegleiter.
- `noc-elster-eric`: ELSTER- und ERiC-Workflowbegleiter.
- `noc-grundbuch-portal`: Grundbuchzugangs- und Nachweisbegleiter.
- `noc-oci-evidence`: OCI-Landing-Zone-Nachweis- und Auditbegleiter.

## Sicherheitsmodell

- Plugins arbeiten standardmaessig lokal, trockenlaufbasiert, mit Planvorschau
  und ausschliesslich Metadaten-Nachweisen.
- Externe Schreibadapter sind im MVP nicht aktiviert.
- Fehlende Konten oder Freigaben werden in
  [docs/de/plugin-operations/account-and-approval-requests.md](../docs/de/plugin-operations/account-and-approval-requests.md)
  und
  [docs/en/plugin-operations/account-and-approval-requests.md](../docs/en/plugin-operations/account-and-approval-requests.md)
  verfolgt.
- Vor Veroeffentlichung oder Installation mit `python3 scripts/validate_plugins.py`
  validieren.

## Fortschritt

Der Plugin-Fortschritt wird in [plugins/GANTT.md](GANTT.md) gepflegt und in
[roadmap/GANTT.md](../roadmap/GANTT.md) zusammengefuehrt. Jede Plugin-Aenderung
muss beide Dateien aktualisieren, bevor sie push-ready ist.

## Marketplace-Grenze

Oeffentliche GPT-Store-Pakete und workspace-interne App-Installationen sind
verschiedene Release-Ziele. Jedes Plugin muss vor oeffentlicher Veroeffentlichung
gegen die jeweils aktuellen OpenAI-Veroeffentlichungsregeln geprueft werden;
Actions brauchen weiterhin gueltige Datenschutz- und Nutzungsbedingungen-URLs.
