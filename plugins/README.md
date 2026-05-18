# NaC Plugins fuer regulierte Branchen

Dieser Ordner enthaelt installierbare repo-lokale Codex-Plugins fuer NaC-
Arbeitsablaeufe in regulierten Branchen. Die erste Suite fokussiert
Anwaltskanzleien, Notariate, Steuer-Arbeitsablaeufe und
Cloud-Nachweisbetrieb.

## Installierbare Plugins

- `nac-regulated-core`: gemeinsame Schutzplanken fuer regulierte Arbeitsablaeufe.
- `nac-idaas`: Begleiter fuer deutsche eID-Pruefung und IAM-Projektionsbereitschaft.
- `nac-cyberjack-rfid`: lokale Karten- und SAK-lite-Pruefung vor dem XNP-Login.
- `nac-bnotk-xnp`: lokale XNP-Authentifizierungspruefung nach Kartenbereitschaft.
- `nac-pkcs7-certbundle`: lokaler PKCS#7/P7B-Zertifikatsbuendel-Nachweis ohne Signatur.
- `nac-handelsregister`: HRA-zuerst-Bereitschaft fuer Online-Registeranmeldungen nach Modusentscheidung.
- `nac-bea-portal`: beA-Arbeitsablauf- und Nachweisbegleiter.
- `nac-elster-eric`: ELSTER- und ERiC-Arbeitsablaufbegleiter.
- `nac-grundbuch-portal`: Grundbuchzugangs- und Nachweisbegleiter.
- `nac-oci-evidence`: OCI-Landing-Zone-Nachweis- und Auditbegleiter.

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

## Marktplatz-Grenze

Oeffentliche GPT-Store-Pakete und arbeitsbereichsinterne App-Installationen sind
verschiedene Veroeffentlichungsziele. Jedes Plugin muss vor oeffentlicher Veroeffentlichung
gegen die jeweils aktuellen OpenAI-Veroeffentlichungsregeln geprueft werden;
Aktionen brauchen weiterhin gueltige Datenschutz- und Nutzungsbedingungen-URLs.
