# NoC beA-Portal-Begleiter

Lokaler beA-Arbeitsablaufbegleiter fuer Bereitschaft, Postfach-/eEB-Aufgabenplanung,
Client-Security-Pruefungen und Nachweiserfassung, ohne PINs, Kartendaten,
Postfachgeheimnisse oder Mandatsinhalte in Git zu speichern.

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

- Postfachinhaber, Nutzerrolle, Karten-/Token-Bereitschaft und Verfuegbarkeit von
  beA Client Security bestaetigen.

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
- Kanzleirichtlinie fuer eEB und Exporte

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
