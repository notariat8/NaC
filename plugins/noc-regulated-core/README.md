# NoC Schutzplanken fuer Regulierung

Gemeinsame lokale Arbeitsablauf-, Sicherheitsgrenzen-, Planvorschau-,
Freigabe- und Nachweisfuehrung fuer NoC-Plugins in Anwaltskanzleien,
Notariaten und angrenzenden regulierten Betriebsablaeufen.

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

- Vorgangsart, Akteursrolle, Reviewer-Rolle und Datengrenze bestaetigen.
- Lokalen Workspace und Git-Remote auf sauberen Zustand pruefen.

## Day1

- Planvorschau und Nachweisvorlage vor jeder externen Aktion erzeugen.

## Day2

- Drift, abgelaufene Freigaben, fehlgeschlagene Kontrollen und
  Konto-Rezertifizierung pruefen.

## Erforderliche Konten und Freigaben

- GitHub-Schreibzugriff auf das Repository
- freigegebene Reviewer-Liste
- Entscheidung zum Nachweisspeicher

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
