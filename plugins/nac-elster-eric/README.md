# ELSTER/ERiC

Lokaler ELSTER-/ERiC-Arbeitsablaufbegleiter für Abgabe-Bereitschaft, lokale
Zugangsmittelgrenzen, Nachweisimport und Hersteller-/Onboarding-Prüfungen ohne
zentrale Speicherung von Steuer-Zugangsdaten.

## Status

Installierbares MVP-Plugin-Gerüst. Das Plugin stellt lokale Codex-Skill-
Führung, einen maschinenlesbaren Sicherheitsvertrag und Marktplatz-Metadaten
bereit. Externe Schreibadapter sind in dieser ersten Version bewusst nicht
aktiviert.

## Installationsgrenze

- Läuft als lokales Codex-Plugin aus diesem Repository.
- Hält Geheimnisse, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte außerhalb von Git.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder sensiblen Aktion.
- Verlangt menschliche Freigabe für regulierte Einreichungen, Portalaktionen,
  notarielle Aktionen und Cloud-Anwendungen.

## Day0

- Berechtigung des Steuerakteurs und lokale ELSTER-Credential-Grenze bestätigen.
- Entscheiden, ob ERiC-Hersteller-Onboarding im Scope liegt.

## Day1

- Trockenlauf-Abgabeplan und menschlichen Freigabepunkt erstellen.

## Day2

- ERiC-Version, Zertifikate, Fristen, fehlgeschlagene Übertragungen und
  Nachweisaufbewahrung verfolgen.

## Erforderliche Konten und Freigaben

- ELSTER-Organisations- oder Nutzerzugang
- lokales Zertifikat oder freigegebene Authentifizierungsmethode
- ERiC-Herstellerregistrierung, falls serverseitige Integration verfolgt wird
- Freigabe der steuerlichen Vertretung

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
