# M365-MCP-Batch-Freigabe

Dieses Runbook bündelt wiederkehrende Freigaben für die aktive
M365-MVP-Spur. Ziel ist, dass Agenten mehrere unabhängige PRs und
Smoke-Vorbereitungen vollständig vorbereiten, statt nach jedem kleinen Schritt
auf Owner-Input zu warten.

Die aktive MVP-Spur bleibt Entra ID, Microsoft Teams, Microsoft-365-Gruppe,
SharePoint-Team-Site und Microsoft Graph REST beziehungsweise MCP. Alte
SharePoint-APIs, SharePoint-SDKs und der archivierte OCI-Pfad gehören nicht zu
diesem Runbook.

## Ohne Owner-Gate

Der Agent arbeitet diese Schritte eigenständig ab:

- GitHub-Issue mit Scope, Akzeptanzkriterien, Risiko und Validierung anlegen.
- Feature-Branch vom aktuellen `main` schneiden.
- Code, Tests, CLI-Oberfläche, MCP-Verträge und Doku vorbereiten.
- Lokale Validatoren und repoübliche Quality Gates ausführen.
- PR öffnen, Checks beobachten und Check-Fehler beheben.
- Read-only Metadaten lesen, solange keine Secrets, Tokens oder echten
  Mandatsdaten ausgegeben werden.
- Einen Batch-Status mit allen vorbereiteten PRs, Check-Ergebnissen und
  konkretem Freigabetext erstellen.

Ein Agent beendet den Arbeitsblock nicht mit einem offenen technischen
Folgeschritt, wenn dieser ohne Owner-Gate ausführbar ist.

## Owner-Gates

Diese Schritte bleiben ausdrücklich Owner-gated:

- PRs nach `main` mergen.
- Branches nach einem Merge auf GitHub löschen, wenn dies Teil eines
  freigegebenen Batchs ist.
- Live-Schreibaktionen im M365-Tenant ausführen, auch wenn nur synthetische
  Testakten verwendet werden.
- Live-Löschaktionen im M365-Tenant ausführen.
- Entra-App-Berechtigungen, Consent, Zertifikate, Secrets oder Credential-Flows
  ändern.
- Teams-, Gruppen-, Site-, Listen-, Spalten-, Rollen-, Mitgliedschafts- oder
  Berechtigungsänderungen im Live-Tenant durchführen.
- Echte Mandatsdaten, personenbezogene Daten oder vertrauliche Dokumente
  verarbeiten.

## Batch-Paket

Ein Batch-Paket enthält pro PR mindestens:

| Feld | Inhalt |
| --- | --- |
| PR | Nummer, Titel und Branch |
| Scope | fachlicher und technischer Umfang |
| Checks | lokale Validatoren und GitHub-Checks |
| Live-Tenant | `keine Live-Aktion`, `read-only` oder konkrete Schreib-/Löschaktion |
| Risiko | relevante Daten-, Rechte-, Tenant- oder Betriebsgrenze |
| Freigabetext | kopierbare Owner-Freigabe |

Der Agent darf mehrere PRs parallel vorbereiten. Er sammelt die Freigaben erst,
wenn die PRs reviewfähig sind oder ein echter Owner-Gate erreicht ist.

## Merge-Freigabe

Für einen reinen Merge-Batch reicht ein konkreter Satz:

```text
Freigabe: PRs #383, #385 mergen und Branches nach Merge aufräumen.
```

Nach dieser Freigabe führt der Agent die freigegebenen Merges, Remote-Checks,
lokale Synchronisierung und Branch-Bereinigung vollständig aus. Er stoppt nur
bei Merge-Konflikt, fehlgeschlagenem Check, Rechtefehler oder unerwartetem
Scope.

## Live-Smoke-Freigabe

Live-Smokes werden getrennt vom Merge-Batch freigegeben, weil sie den
M365-Tenant schreiben oder löschen können. Für synthetische Testakten lautet der
Standardtext:

```text
Freigabe: M365 MCP Smoke Suite live mit synthetischer Testakte im Workspace notary_team_01 ausführen, positive write-read und Cleanup im gleichen Lauf.
```

Der technische Lauf nutzt die zentrale `nac`-CLI:

```bash
python3 scripts/nac.py m365 teams-sharepoint mcp-smoke-suite \
  --owner-approved \
  --mcp-suite-cleanup \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --format json
```

Der Lauf darf nur synthetische IDs mit dem Präfix `NAC-SMOKE-WRITE-READ-`
erzeugen oder bereinigen. Evidence wird redigiert abgelegt; Tokens, Secrets,
Rohdaten echter Akten und vollständige personenbezogene Inhalte werden nicht
protokolliert.

## Abschlussregel

Nach einem freigegebenen Batch ist der Agent erst fertig, wenn alle
freigegebenen Aktionen ausgeführt, Checks grün, lokale Branches bereinigt und
der Zielbranch synchronisiert sind. Wenn noch ein agentisch ausführbarer Schritt
offen ist, arbeitet der Agent weiter. Wenn Owner-Input nötig ist, nennt der
Agent genau den nächsten kopierbaren Freigabetext.
