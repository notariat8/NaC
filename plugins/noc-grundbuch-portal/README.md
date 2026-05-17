# NoC Grundbuchportal-Begleiter

Grundbuchportal-Arbeitsablaufbegleiter fuer Berechtigung, berechtigtes Interesse,
Abrufplanung und Nachweisimport ohne unbefugte Portalautomatisierung oder
unkontrollierte Dokumentenspeicherung.

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

- Berechtigten Nutzer, Landesportal-Scope, Kostenstelle und Grundlage des
  berechtigten Interesses bestaetigen.

## Day1

- Menschlich freigegebenen Abrufplan und Checkliste fuer Nachweisimport erstellen.

## Day2

- Zugriffsrezertifizierung, Laenderdrift, Gebuehren, fehlgeschlagene Abrufe und
  Aufbewahrung pruefen.

## Erforderliche Konten und Freigaben

- landesspezifischer Grundbuchportalzugang
- Bestaetigung der berechtigten Berufsrolle
- Kostenstellenfreigabe
- Aufbewahrungs-/DMS-Entscheidung

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
