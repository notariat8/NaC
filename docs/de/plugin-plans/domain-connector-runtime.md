# Plugin Plan: Domain Connector Runtime

Status: `draft`

## Ziel

Fachsystem-Connectoren sollen NaC-Änderungen kontrolliert in Zielsysteme reconciled:

- IAM
- GitHub
- Jira oder vergleichbare Ticket-Systeme
- Slack oder Teams für Benachrichtigungen
- spätere Branchen- oder Kundensysteme

## Leitprinzip

Connectoren sind Adapter.
Sie dürfen die fachliche Wahrheit nicht ersetzen.
Die Wahrheit liegt in Git, Schemas, Policies, Reviews und freigegebenen Prozessversionen.

## Vertragsmodell

Jeder Connector braucht:

- Input-Schema für Intent.
- Plan-Schema für Preview.
- Apply-Protokoll.
- Idempotenzschlüssel.
- Audit-Event-Schema.
- Drift-Check.
- Exit- und Ersatzpfad.

## Day0

- Zielsysteme für MVP bestätigen:
  - GitHub
  - IAM
  - Jira
- Test- oder Sandbox-Zugang je Zielsystem bereitstellen.
- Keine echten Kundendaten in Beispielen verwenden.
- Connector-Konfiguration als Dokumentation starten, nicht als Secret-Datei.

## Day1

- Ersten Connector nur im Dry-Run bauen.
- Plan Preview im PR erzeugen.
- Reviewer-Gates für sensible Änderungen erzwingen.
- Apply erst nach Merge oder expliziter Freigabe.
- Audit Evidence schreiben:
  - geplanter Zielzustand
  - ausgeführte Operation
  - Zielsystem-Antwort ohne Secrets
  - Zeitstempel
  - Actor

## Day2

- Drift regelmäßig prüfen.
- Connector-Ausfälle als Issues erfassen.
- Replays idempotent ausführen.
- Zielsystem-Berechtigungen rezertifizieren.
- Exit-Pfad für jeden Connector testen.

## MVP-Reihenfolge

1. GitHub-Connector für Issues, PRs, Labels, Reviews und Releases.
2. IAM-Connector für Rollen-/Zugriffsänderungen im Pilot.
3. Jira-Connector für Ticket- und Prozessübergabe.
4. Benachrichtigungsconnector für Slack oder Teams.
5. OCI-Evidence-Connector für Eventstream und Audit Journal.
6. Handelsregister-Spike für Registerrecherche ohne produktive Automatisierung.
7. XNP-Companion für lokale Notariatssoftware-Integration.

## Akzeptanzkriterien

- Jeder Connector erzeugt vor Apply einen menschenlesbaren Plan.
- Jeder Apply ist idempotent.
- Jeder Apply schreibt Audit Evidence.
- Drift wird als Issue oder Plan-Diff sichtbar.
- Secrets bleiben außerhalb von Git.
