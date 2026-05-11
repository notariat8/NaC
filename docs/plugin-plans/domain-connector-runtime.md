# Plugin Plan: Domain Connector Runtime

Status: `draft`

## Ziel

Fachsystem-Connectoren sollen OaC-Aenderungen kontrolliert in Zielsysteme reconciled:

- IAM
- GitHub
- Jira oder vergleichbare Ticket-Systeme
- Slack oder Teams fuer Benachrichtigungen
- spaetere Branchen- oder Kundensysteme

## Leitprinzip

Connectoren sind Adapter.
Sie duerfen die fachliche Wahrheit nicht ersetzen.
Die Wahrheit liegt in Git, Schemas, Policies, Reviews und freigegebenen Prozessversionen.

## Vertragsmodell

Jeder Connector braucht:

- Input-Schema fuer Intent.
- Plan-Schema fuer Preview.
- Apply-Protokoll.
- Idempotenzschluessel.
- Audit-Event-Schema.
- Drift-Check.
- Exit- und Ersatzpfad.

## Day0

- Zielsysteme fuer MVP bestaetigen:
  - GitHub
  - IAM
  - Jira
- Test- oder Sandbox-Zugang je Zielsystem bereitstellen.
- Keine echten Kundendaten in Beispielen verwenden.
- Connector-Konfiguration als Dokumentation starten, nicht als Secret-Datei.

## Day1

- Ersten Connector nur im Dry-Run bauen.
- Plan Preview im PR erzeugen.
- Reviewer-Gates fuer sensible Aenderungen erzwingen.
- Apply erst nach Merge oder expliziter Freigabe.
- Audit Evidence schreiben:
  - geplanter Zielzustand
  - ausgefuehrte Operation
  - Zielsystem-Antwort ohne Secrets
  - Zeitstempel
  - Actor

## Day2

- Drift regelmaessig pruefen.
- Connector-Ausfaelle als Issues erfassen.
- Replays idempotent ausfuehren.
- Zielsystem-Berechtigungen rezertifizieren.
- Exit-Pfad fuer jeden Connector testen.

## MVP-Reihenfolge

1. GitHub-Connector fuer Issues, PRs, Labels, Reviews und Releases.
2. IAM-Connector fuer Rollen-/Zugriffsaenderungen im Pilot.
3. Jira-Connector fuer Ticket- und Prozessuebergabe.
4. Benachrichtigungsconnector fuer Slack oder Teams.
5. OCI-Evidence-Connector fuer Eventstream und Audit Journal.
6. Handelsregister-Spike fuer Registerrecherche ohne produktive Automatisierung.
7. XNP-Companion fuer lokale Notariatssoftware-Integration.

## Akzeptanzkriterien

- Jeder Connector erzeugt vor Apply einen menschenlesbaren Plan.
- Jeder Apply ist idempotent.
- Jeder Apply schreibt Audit Evidence.
- Drift wird als Issue oder Plan-Diff sichtbar.
- Secrets bleiben ausserhalb von Git.
