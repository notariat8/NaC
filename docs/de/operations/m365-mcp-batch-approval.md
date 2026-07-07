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

Der One-Shot-Runner bleibt owner-gated und deckt intern
`runtime-certificate-expiry-monitor`, `runtime-smoke`, `runtime-metadata`,
`mcp-smoke-suite --mcp-suite-cleanup`,
`mcp-smoke-leftover-cleanup --mcp-leftover-dry-run` und
`release-gate-evidence --release-gate-require-runtime-artifacts` ab.
`runtime-certificate-expiry-monitor` ist offline, `runtime-smoke` und
`runtime-metadata` sind read-only, die MCP Smoke Suite schreibt und löscht eine
synthetische Akte, der Leftover-Dry-Run liest nur die Trefferanzahl.
`release-gate-evidence` läuft am Ende offline und liest nur lokale redigierte
Artefakte. Der Expiry-Monitor, `runtime-smoke` und `runtime-metadata` schreiben
dabei eigene redigierte Runtime-Artefakte, damit der Abschlussbericht
`complete_release_gate_artifacts` melden kann. Der offline
`mcp-inventory-smoke` bleibt ein separater Diagnose- und Evidence-Befehl und
kann mit `--release-gate-inventory-artifact` optional an den Abschlussbericht
gehängt werden; der One-Shot-Runner führt ihn nicht automatisch aus. Die
Einzelbefehle bleiben ein Diagnose-/Fallback-Pfad, wenn ein Runner-Schritt
isoliert reproduziert werden muss.

## Runtime-Zertifikatsrotation-Freigabe

Nach einer `runtime-certificate-readiness`-Warnung rendert der Agent das
komplette Zertifikatsrotationspaket offline:

```bash
python3 scripts/nac.py batch-approval m365 \
  --batch-mode runtime-certificate-rotation \
  --workspace-id notary_team_01 \
  --correlation-id <correlation-id> \
  --format json
```

Der Renderer führt keine GitHub- oder Graph-Schreibaktion aus und liest keine
Zertifikats-, Private-Key- oder Secret-Dateien. Er bündelt die nötigen
Owner-Gates in einem kopierbaren Freigabetext: lokales Runtime-Zertifikat
erzeugen, Public Certificate in Entra hochladen, lokale Runtime-Credential-
Grenze aktualisieren, `release-gate-run` live ausführen, nicht-geheime
Runtime-Evidence per PR refreshen, altes Entra-Credential entfernen, lokales
altes Zertifikatsarchiv löschen und die lokale delegated M365-CLI-Session
abmelden.

## Standard-Betriebsnachweis für MCP-/Runtime-Änderungen

`release-gate-run` ist der Standard-Betriebsnachweis nach einem gemergten
Änderungssatz, wenn dieser eine dieser Flächen berührt:

- `teams-sharepoint-data-mcp`-Vertrag, Tool-Grenzen oder Adapterverhalten,
- `nac_m365_graph`-Runtime-, Graph-Client-, Smoke- oder Cleanup-Module,
- zentrale `nac`-CLI-Bedienkante für M365-MCP-Smokes,
- Runtime-Graph-Konfiguration, Zertifikatspfad oder Sites.Selected-Zugriff,
- Runbook- oder Operator-Änderungen, die den Live-Write-/Read-/Cleanup-Pfad
  betreffen.

Der Nachweis darf nicht automatisch ohne Freigabe laufen. Er bleibt ein
separates Owner-Gate, weil der intern abgedeckte
`mcp-smoke-suite --mcp-suite-cleanup`-Schritt im Live-Tenant eine synthetische
Akte schreibt und löscht. Nach der Freigabe muss der Agent den Lauf
vollständig abschließen: Runtime-Smoke, Runtime-Metadata, Write, Read,
Cleanup, Leftover-Dry-Run, Zertifikatsablauf-Monitor, Runtime-Env-Bootstrap,
Evidence Export,
Workspace-Clean-State und
konkretes Ergebnis in der Abschlussmeldung. Die MCP Smoke Suite bleibt
Diagnose-/Komponentenpfad, wenn nur dieser Schritt isoliert reproduziert werden
muss. Bleibt nach dem Lauf ein synthetischer Rest zurück, ist unmittelbar der
owner-gated `mcp-smoke-leftover-cleanup`-Pfad vorzubereiten.

Bei Nutzung von `release-gate-run` erzeugt der Runner den redigierten
Abschlussbericht bereits im gleichen owner-gated Lauf und kopiert die
vorhandenen redigierten Artefakte zusätzlich in
`out/m365/teams-sharepoint/release-gates/<correlation-id>/`. Dort liegt auch
`release-gate-retention-index.redacted.json`, damit mehrere Gate-Läufe
auditierbar nebeneinander bleiben, während `out/m365/teams-sharepoint/` weiter
den letzten `latest`-Stand enthält. Nach dem Retention-Schritt aktualisiert der
Runner den Abschlussbericht, das Evidence-JSON und den Artifact-Index mit dem
Retention-Pfad und kopiert diese aktualisierten Artefakte erneut in den
Laufordner. Der folgende Offline-Exporter bleibt nur für Diagnose oder erneuten
Export vorhandener Artefakte:

Der lokale Audit-Überblick läuft offline über:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-retention-list \
  --format json
```

Der Befehl liest nur lokale Retention-Index- und Evidence-JSON-Dateien unter
`out/m365/teams-sharepoint/release-gates/` und gibt Correlation-ID, Status,
Timestamp, Workspace, Artefaktzähler und lokale Evidence-Pfade aus. Er führt
keine Graph-Anfrage, keinen Tenant-Write und keine Löschung aus.

Der lokale Vergleich zweier archivierter Läufe läuft ebenfalls offline:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-retention-compare \
  --release-gate-compare-left <left-correlation-id> \
  --release-gate-compare-right <right-correlation-id> \
  --format json
```

`--release-gate-compare-left` und `--release-gate-compare-right` akzeptieren
Correlation-IDs, Laufordner oder direkte
`release-gate-retention-index.redacted.json`-Pfade. Der Vergleich meldet
Status-, Timestamp-, Artefakt-, fehlende-Anhänge- und Evidence-Pfad-
Unterschiede, liest aber keine SharePoint-Dateiinhalte und führt keine
Graph-Anfrage, keinen Tenant-Write und keine Löschung aus.

Ein versionierbarer Vergleichsnachweis wird offline mit demselben Input
geschrieben:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-retention-compare-artifact \
  --release-gate-compare-left <left-correlation-id> \
  --release-gate-compare-right <right-correlation-id> \
  --format json
```

Ohne explizite Pfade schreibt der Befehl
`release-gate-retention-compare.redacted.md` und
`release-gate-retention-compare.redacted.json` unter
`out/m365/teams-sharepoint/release-gate-comparisons/<left>__<right>/`.
`--release-gate-compare-output` und `--release-gate-compare-json-output`
setzen eigene Zielpfade. Der Export bleibt redigiert und offline.

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-evidence \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --release-gate-require-runtime-artifacts \
  --format json
```

Der Exporter führt keine Graph-Anfrage aus. Er liest die lokalen redigierten
Artefakte `runtime-certificate-expiry-monitor.redacted.json`,
`runtime-env-bootstrap.redacted.json`,
`runtime-smoke.redacted.json`,
`runtime-metadata.redacted.json`, `mcp-smoke-suite.redacted.json` und
`mcp-smoke-leftover-cleanup.redacted.json` und schreibt
`out/m365/teams-sharepoint/release-gate-evidence.redacted.md`. Optionale
Runtime-Artefakte können über
`--release-gate-runtime-certificate-expiry-artifact`,
`--release-gate-runtime-env-bootstrap-artifact`,
`--release-gate-runtime-smoke-artifact` und
`--release-gate-runtime-metadata-artifact` ergänzt werden; fehlen sie, werden
die Runtime-Schritte außerhalb des Release-Gate-Batchs als `NOT_ATTACHED`
dokumentiert. Im Release-Gate-Batch blockiert der Export bei fehlenden
Runtime-Artefakten.

Vor den Live-Schritten nutzt `release-gate-run` intern den Offline-
`runtime-env-bootstrap`: aus dem nicht-geheimen Runtime-Smoke-State werden
Tenant- und Runtime-Client-ID nur als Subprozess-Environment aufgelöst; lokale
Zertifikats- und Private-Key-Pfade werden nur an die Live-Subprozesse
übergeben. Der Runner schreibt
`out/m365/teams-sharepoint/runtime-env-bootstrap.redacted.json` und hängt es an
`release-gate-evidence` sowie den Artifact-Index an. Das Artefakt enthält
keine Tenant-ID, Client-ID, Zertifikatsthumbprints, Zertifikatskörper,
Private-Key-Daten, Tokens oder Secret-Werte.

## Abschlussregel

Nach einem freigegebenen Batch ist der Agent erst fertig, wenn alle
freigegebenen Aktionen ausgeführt, Checks grün, lokale Branches bereinigt und
der Zielbranch synchronisiert sind. Wenn noch ein agentisch ausführbarer Schritt
offen ist, arbeitet der Agent weiter. Wenn Owner-Input nötig ist, nennt der
Agent genau den nächsten kopierbaren Freigabetext.
