# NoC ELSTER-ERiC-Begleiter

Lokaler ELSTER-/ERiC-Arbeitsablaufbegleiter fuer Abgabe-Bereitschaft, lokale
Zugangsmittelgrenzen, Nachweisimport und Hersteller-/Onboarding-Pruefungen ohne
zentrale Speicherung von Steuer-Zugangsdaten.

## Status

Installierbares MVP-Plugin-Geruest. Das Plugin stellt lokale Codex-Skill-
Fuehrung, einen maschinenlesbaren Sicherheitsvertrag und Marktplatz-Metadaten
bereit. Externe Schreibadapter sind in dieser ersten Version bewusst nicht
aktiviert.

## Installationsgrenze

- Laeuft als lokales Codex-Plugin aus diesem Repository.
- Haelt Geheimnisse, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte ausserhalb von Git.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder sensiblen Aktion.
- Verlangt menschliche Freigabe fuer regulierte Einreichungen, Portalaktionen,
  notarielle Aktionen und Cloud-Anwendungen.

## Day0

- Berechtigung des Steuerakteurs und lokale ELSTER-Credential-Grenze bestaetigen.
- Entscheiden, ob ERiC-Hersteller-Onboarding im Scope liegt.

## Day1

- Trockenlauf-Abgabeplan und menschlichen Freigabepunkt erstellen.

## Day2

- ERiC-Version, Zertifikate, Fristen, fehlgeschlagene Uebertragungen und
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
