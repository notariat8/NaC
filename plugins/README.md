# NaC Plugins für regulierte Branchen

Dieser Ordner enthält installierbare repo-lokale Codex-Plugins für NaC-
Arbeitsabläufe in regulierten Branchen. Die erste Suite fokussiert
Anwaltskanzleien, Notariate, Steuer-Arbeitsabläufe und
Cloud-Nachweisbetrieb.

## Installierbare Plugins

- `nac-regulated-core`: gemeinsame Schutzplanken für regulierte Arbeitsabläufe.
- `nac-idaas`: Begleiter für deutsche eID-Prüfung und IAM-Projektionsbereitschaft.
- `nac-cyberjack-rfid`: lokale Karten- und SAK-lite-Prüfung vor dem XNP-Login.
- `nac-bnotk-xnp`: lokale XNP-Authentifizierungsprüfung nach Kartenbereitschaft.
- `nac-pkcs7-certbundle`: lokaler PKCS#7/P7B-Zertifikatsbündel-Nachweis ohne Signatur.
- `nac-handelsregister`: HRA-zuerst-Bereitschaft für Online-Registeranmeldungen nach Modusentscheidung.
- `nac-bea-portal`: beA-Arbeitsablauf- und Nachweisbegleiter.
- `nac-elster-eric`: ELSTER- und ERiC-Arbeitsablaufbegleiter.
- `nac-grundbuch-portal`: Grundbuchzugangs- und Nachweisbegleiter.
- `nac-oci-evidence`: OCI-Landing-Zone-Nachweis- und Auditbegleiter.

## Sicherheitsmodell

- Plugins arbeiten standardmäßig lokal, trockenlaufbasiert, mit Planvorschau
  und ausschließlich Metadaten-Nachweisen.
- Externe Schreibadapter sind im MVP nicht aktiviert.
- Fehlende Konten oder Freigaben werden in
  [docs/de/plugin-operations/account-and-approval-requests.md](../docs/de/plugin-operations/account-and-approval-requests.md)
  und
  [docs/en/plugin-operations/account-and-approval-requests.md](../docs/en/plugin-operations/account-and-approval-requests.md)
  verfolgt.
- Vor Veröffentlichung oder Installation mit `python3 scripts/validate_plugins.py`
  validieren.

## Fortschritt

Der Plugin-Fortschritt wird in [plugins/GANTT.md](GANTT.md) gepflegt und in
[roadmap/GANTT.md](../roadmap/GANTT.md) zusammengeführt. Plugin-Änderungen
aktualisieren diese Gantts nur, wenn Scope, Status, Meilenstein oder
Pilotbereitschaft betroffen sind; kleine Bugfixes, Textkorrekturen oder
Validator-/Test-Fixes ohne Roadmap-Wirkung erzeugen keine künstliche
Gantt-Änderung.

## Marktplatz-Grenze

Öffentliche GPT-Store-Pakete und arbeitsbereichsinterne App-Installationen sind
verschiedene Veröffentlichungsziele. Jedes Plugin muss vor öffentlicher Veröffentlichung
gegen die jeweils aktuellen OpenAI-Veröffentlichungsregeln geprüft werden;
Aktionen brauchen weiterhin gültige Datenschutz- und Nutzungsbedingungen-URLs.
