# M365 Matter-Access Apply Live-Smoke Release Lane

Dieser Release-Lane-Standard trennt den owner-gated
`matter-access-apply-smoke` bewusst vom normalen M365 Runtime Release-Gate. Der
Smoke schreibt echte synthetische SharePoint-Listeneinträge in
`Vertretungsfreigaben` und `AuditJournalLite`, liest sie zurück, löscht sie im
gleichen Lauf und speichert nur redigierte Evidence. Deshalb ist er kein
stillschweigender Default im One-Shot-Runner.

Der `matter-access-apply-smoke` ist eine owner-gated Release Lane: kein stillschweigender Default,
kein automatischer Anhang an Evidence und kein Start ohne vorbereiteten
Freigabetext.

## Zweck

Der Live-Smoke beweist, dass der spätere Apply-Pfad für zeitbegrenzte
Vertretungsfreigaben nicht nur offline geplant ist, sondern im Workspace
Graph-REST-only schreiben, lesen und bereinigen kann.

Er ergänzt, aber ersetzt nicht:

- `matter-access-apply-readiness`
- `matter-access-apply-request-plan`
- `matter-access-apply-policy-smoke`
- das normale `release-gate-run` mit `mvp_release_readiness=READY`

## Auslösebedingung

Der Live-Smoke wird separat ausgeführt, wenn mindestens eine dieser Bedingungen
vorliegt:

- der Apply-Pfad für `grant_request` oder `audit_append` wurde geändert
- das SharePoint-Listenmodell für `Vertretungsfreigaben` oder
  `AuditJournalLite` wurde geändert
- Runtime-Credentials, App-Berechtigungen oder Graph-REST-Grenzen wurden
  geändert
- vor einer fachlichen Abnahme soll ein echter synthetischer Write-Read-Cleanup
  nachgewiesen werden

Ein Agent darf diesen Smoke nicht automatisch aus einem normalen Release-Gate
ableiten. Der Live-Smoke braucht immer explizite Owner-Freigabe.

## Voraussetzungen

- lokaler `main` ist aktuell
- das normale M365 Runtime Release-Gate ist `PASSED`
- `release-readiness` meldet `mvp_release_readiness=READY`
- `matter-access-apply-policy-smoke` meldet `5/5` Negativfälle und
  Fail-Closed vor Graph-Writes
- Ziel-Workspace ist explizit freigegeben, im MVP normalerweise
  `notary_team_01`
- es werden nur synthetische IDs mit den Präfixen `NAC-SMOKE-GRANT-` und
  `NAC-SMOKE-MATTER-` verwendet

## Freigabetext

```text
Freigabe: Matter-Access Apply Live-Smoke im Workspace notary_team_01 owner-approved ausführen, inklusive synthetischer Vertretungsfreigabe, Audit-Event, Readback, Cleanup und redigiertem Evidence-Artefakt.
```

## Befehl

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-smoke \
  --owner-approved \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --format json
```

Das Standardartefakt liegt unter:

```text
out/m365/teams-sharepoint/matter-access-apply-smoke.redacted.json
```

Nach einem erfolgreichen Lauf archiviert der Befehl das redigierte
Live-Smoke-Artefakt zusätzlich automatisch in einem correlation-basierten
Retention-Ordner:

```text
out/m365/teams-sharepoint/matter-access-apply-live-smokes/<correlation-id>/
```

Dort liegen mindestens:

```text
matter-access-apply-smoke.redacted.json
matter-access-apply-live-smoke-retention.redacted.json
matter-access-apply-live-smoke-retention.redacted.md
```

Der Root-Index liegt unter:

```text
out/m365/teams-sharepoint/matter-access-apply-live-smokes/matter-access-apply-live-smoke-retention-index.redacted.json
```

Vorhandene redigierte Artefakte können offline nacharchiviert werden:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-live-smoke-retain \
  --matter-access-apply-live-smoke-artifact out/m365/teams-sharepoint/matter-access-apply-smoke.redacted.json \
  --format json
```

Der Offline-Index ist lokal filterbar und führt keine Graph-Anfrage aus:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-live-smoke-retention-index \
  --matter-access-apply-live-smoke-correlation-id <correlation-id> \
  --format json
```

Die retenierte Evidence kann vor Abnahme offline als `READY`/`NOT_READY`
bewertet werden. Der Readiness-Befehl liest nur den lokalen redigierten
Retention-Index und führt keine Graph- oder Tenant-Aktion aus:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-live-smoke-retention-readiness \
  --matter-access-apply-live-smoke-correlation-id <correlation-id> \
  --matter-access-apply-live-smoke-write-readiness \
  --format json
```

Bei `--matter-access-apply-live-smoke-write-readiness` entstehen zusätzlich:

```text
matter-access-apply-live-smoke-retention-readiness.redacted.json
matter-access-apply-live-smoke-retention-readiness.redacted.md
```

Ein vorhandenes, owner-gated erzeugtes Artefakt kann danach explizit an die
Release-Gate-Evidence angehängt werden:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-evidence \
  --release-gate-matter-access-apply-smoke-artifact out/m365/teams-sharepoint/matter-access-apply-smoke.redacted.json \
  --format json
```

Ohne diesen Parameter bleibt `matter_access_apply_smoke` in
`release-gate-evidence` absichtlich `NOT_ATTACHED`; vorhandene Default-Dateien
werden nicht automatisch übernommen.

## Akzeptanzkriterien

- `status=PASSED`
- `write_tools=["grant_request", "audit_append"]`
- `write_lists=["Vertretungsfreigaben", "AuditJournalLite"]`
- `executed_graph_requests=true`
- `executed_graph_writes=true`
- `sharepoint_item_writes_executed=true`
- `planned_write_count=2`
- `grant_read_value_count=1`
- `audit_read_value_count=1`
- `cleanup_requested=true`
- `grant_cleanup_read_after_value_count=0`
- `audit_cleanup_read_after_value_count=0`
- `tenant_mutation_allowed=false`
- `team_membership_mutation_allowed=false`
- `sharepoint_item_permission_mutation_allowed=false`
- `stores_tokens_or_secrets=false`
- `stores_matter_payloads=false`
- `raw_graph_path_stored=false`
- `raw_graph_response_stored=false`
- `raw_write_payload_stored=false`
- `reads_sharepoint_file_content=false`
- Retention: `retention_executes_graph_requests=false`
- Retention: `retention_tenant_writes_executed=false`
- Retention: correlation-basierter Ordner und Root-Index vorhanden
- Readiness: `status=READY`
- Readiness: `executes_graph_requests=false`
- Readiness: `tenant_writes_executed=false`

## Fehlerverhalten

Wenn der Smoke nicht `PASSED` ist, gilt die Release Lane als blockiert. Wenn
Cleanup oder Cleanup-Readback fehlschlägt, wird nicht weiter freigegeben. Wenn
der Smoke zwar bestanden hat, die correlation-basierte Retention aber nicht
`PASSED` ist, gibt der Befehl ebenfalls keinen erfolgreichen Abschluss zurück.
Wenn die Retention-Readiness `NOT_READY` meldet, wird keine fachliche Abnahme
behauptet. Der nächste Schritt ist dann ein separater owner-gated
Cleanup-Auftrag mit redigierter Leftover-Evidence bzw. ein
Offline-Retention-Fix; produktive Mandats-IDs dürfen nicht als Fallback-Ziel
verwendet werden.

## Grenzen

Dieser Standard erlaubt keine produktiven Vertretungsfreigaben, keine
Teams-Mitgliedschaftsänderungen, keine SharePoint-Item-Permission-Mutationen,
keine SharePoint-Dateiinhaltsreads, keine Graph-Beta-/SDK-/PnP-Nutzung und kein
Speichern von Tokens, Secrets, Rohantworten, konkreten Graph-Pfaden oder
Mandats-Payloads.
