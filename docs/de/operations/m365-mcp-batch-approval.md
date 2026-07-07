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

## Runtime-Release-Gate-Freigabe

Nach Runtime- oder MCP-Änderungen rendert der Agent das komplette Gate offline:

```bash
python3 scripts/nac.py batch-approval m365 --batch-mode release-gate --workspace-id notary_team_01 --correlation-id <correlation-id> --format json
```

Der Renderer führt keine GitHub- oder Graph-Schreibaktion aus. Er gibt die
kopierbare Owner-Freigabe und genau einen führenden Live-Befehl aus:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-run \
  --owner-approved \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --format json
```

Der One-Shot-Runner bleibt owner-gated und deckt intern `runtime-smoke`,
`runtime-metadata`, `mcp-smoke-suite --mcp-suite-cleanup`,
`mcp-smoke-leftover-cleanup --mcp-leftover-dry-run` und
`release-gate-evidence --release-gate-require-runtime-artifacts` ab.
`runtime-smoke` und `runtime-metadata` sind read-only, die MCP Smoke Suite
schreibt und löscht eine synthetische Akte, der Leftover-Dry-Run liest nur die
Trefferanzahl. `release-gate-evidence` läuft am Ende offline und liest nur
lokale redigierte Artefakte. `runtime-smoke` und `runtime-metadata` schreiben
dabei eigene redigierte Runtime-Artefakte, damit der Abschlussbericht
`complete_release_gate_artifacts` melden kann. Die Einzelbefehle bleiben ein
Diagnose-/Fallback-Pfad, wenn ein Runner-Schritt isoliert reproduziert werden
muss.

## Standard-Betriebsnachweis für MCP-/Runtime-Änderungen

Die Smoke Suite ist der Standard-Betriebsnachweis nach einem gemergten
Änderungssatz, wenn dieser eine dieser Flächen berührt:

- `teams-sharepoint-data-mcp`-Vertrag, Tool-Grenzen oder Adapterverhalten,
- `nac_m365_graph`-Runtime-, Graph-Client-, Smoke- oder Cleanup-Module,
- zentrale `nac`-CLI-Bedienkante für M365-MCP-Smokes,
- Runtime-Graph-Konfiguration, Zertifikatspfad oder Sites.Selected-Zugriff,
- Runbook- oder Operator-Änderungen, die den Live-Write-/Read-/Cleanup-Pfad
  betreffen.

Der Nachweis darf nicht automatisch ohne Freigabe laufen. Er bleibt ein
separates Owner-Gate, weil er im Live-Tenant eine synthetische Akte schreibt
und löscht. Nach der Freigabe muss der Agent den Lauf vollständig abschließen:
Write, Read, Cleanup, redigiertes Artefakt, Workspace-Clean-State und
konkretes Ergebnis in der Abschlussmeldung. Bleibt nach dem Lauf ein
synthetischer Rest zurück, ist unmittelbar der owner-gated
`mcp-smoke-leftover-cleanup`-Pfad vorzubereiten.

Bei Nutzung von `release-gate-run` erzeugt der Runner den redigierten
Abschlussbericht bereits im gleichen owner-gated Lauf. Der folgende Offline-
Exporter bleibt nur für Diagnose oder erneuten Export vorhandener Artefakte:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-evidence \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --release-gate-require-runtime-artifacts \
  --format json
```

Der Exporter führt keine Graph-Anfrage aus. Er liest die lokalen redigierten
Artefakte `runtime-smoke.redacted.json`,
`runtime-metadata.redacted.json`, `mcp-smoke-suite.redacted.json` und
`mcp-smoke-leftover-cleanup.redacted.json` und schreibt
`out/m365/teams-sharepoint/release-gate-evidence.redacted.md`. Optionale
Runtime-Artefakte können über `--release-gate-runtime-smoke-artifact` und
`--release-gate-runtime-metadata-artifact` ergänzt werden; fehlen sie, werden
die Runtime-Schritte außerhalb des Release-Gate-Batchs als `NOT_ATTACHED`
dokumentiert. Im Release-Gate-Batch blockiert der Export bei fehlenden
Runtime-Artefakten.

## Abschlussregel

Nach einem freigegebenen Batch ist der Agent erst fertig, wenn alle
freigegebenen Aktionen ausgeführt, Checks grün, lokale Branches bereinigt und
der Zielbranch synchronisiert sind. Wenn noch ein agentisch ausführbarer Schritt
offen ist, arbeitet der Agent weiter. Wenn Owner-Input nötig ist, nennt der
Agent genau den nächsten kopierbaren Freigabetext.
