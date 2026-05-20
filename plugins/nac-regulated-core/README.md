# Regulierung

Gemeinsame lokale Arbeitsablauf-, Sicherheitsgrenzen-, Planvorschau-,
Freigabe- und Nachweisführung für NaC-Plugins in Anwaltskanzleien,
Notariaten und angrenzenden regulierten Betriebsabläufen.

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

- Vorgangsart, Akteursrolle, Reviewer-Rolle und Datengrenze bestätigen.
- Lokalen Workspace und Git-Remote auf sauberen Zustand prüfen.

## Day1

- Planvorschau und Nachweisvorlage vor jeder externen Aktion erzeugen.

## Day2

- Drift, abgelaufene Freigaben, fehlgeschlagene Kontrollen und
  Konto-Rezertifizierung prüfen.

## Erforderliche Konten und Freigaben

- GitHub-Schreibzugriff auf das Repository
- freigegebene Reviewer-Liste
- Entscheidung zum Nachweisspeicher

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
