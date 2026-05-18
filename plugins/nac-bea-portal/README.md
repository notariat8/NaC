# beA-Postfach

Lokaler beA-Arbeitsablaufbegleiter für Bereitschaft, Postfach-/eEB-Aufgabenplanung,
Client-Security-Prüfungen und Nachweiserfassung, ohne PINs, Kartendaten,
Postfachgeheimnisse oder Mandatsinhalte in Git zu speichern.

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

- Postfachinhaber, Nutzerrolle, Karten-/Token-Bereitschaft und Verfügbarkeit von
  beA Client Security bestätigen.

## Day1

- Menschlich freigegebenen Sende-/Empfangs-/eEB-Plan und Nachweischeckliste
  erstellen.

## Day2

- Client-Security-Versionen, fehlgeschlagene Sendungen, eEB-Fristen und
  Exportintegritaet verfolgen.

## Erforderliche Konten und Freigaben

- beA-Postfachzugriff
- beA-Karte oder freigegebene Authentifizierungsmethode
- beA Client Security auf der lokalen Workstation
- Kanzleirichtlinie für eEB und Exporte

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
