# Process-Ontology SharePoint Schema Apply Runner Dry Run

Diese Decision Note beschreibt den Offline-Dry-Run vor einem späteren
owner-gated SharePoint-Schema-Apply.

## Zweck

`nac kg process-ontology-schema-apply-runner-dry-run --format json` erzeugt aus
Apply-Plan, Apply-Readiness und Execution Contract konkrete geplante Schritte:

- Preflight-Request je Workspace-Apply-Unit
- geplanter späterer Mutationsrequest mit Body-Shape
- geplanter Readback-Request
- Stop-Regel-Plan für fehlgeschlagene Preflights, unerwartete Statuscodes und
  uneindeutige Readbacks

Der Dry-Run macht die spätere Live-Sequenz prüfbar, ohne den Tenant zu ändern.

`nac kg process-ontology-schema-apply-runner-dry-run-artifact --format json`
schreibt daraus zusätzlich redigierte Evidence-Dateien:

- `out/notary-kg/process-ontology-schema-apply-runner-dry-run.redacted.json`
- `out/notary-kg/process-ontology-schema-apply-runner-dry-run.redacted.md`

Das Artefakt enthält die 68 Dry-Run-Schritte als redigierten Index. Site-IDs
werden auf `{site-id}` zurückgeführt, Request-Header werden nicht gespeichert
und geplante Mutationsbodies werden nur als Body-Shape-Key-Liste ausgegeben.

`nac kg process-ontology-schema-apply-artifact-index --format json` schreibt
einen zweiten, ebenfalls redigierten Index über vorhandene Dry-Run-Artefakte.
Der Index ist metadata-only: Er enthält Pfade, Schema-/Statuswerte,
Schrittzahlen, Redaktionsflags und die Markierung
`required_for_live_apply_readiness`, aber keine Requestdetails. Wenn im
Standardordner noch kein Dry-Run-Artefakt liegt, erzeugt der Befehl dieses
Standardartefakt offline nach.

`nac kg process-ontology-schema-apply-live-readiness-gate --format json`
schreibt daraus ein letztes Offline-Gate vor einem späteren echten
SharePoint-Schema-Apply. Das Gate prüft, ob Execution Contract,
Workspace-Readiness, Runner-Dry-Run, redigierter Artefaktindex,
Redaktionsgrenze und Owner-Gate vollständig vorliegen. Der Befehl schreibt
zusätzlich den redigierten Artefaktindex, falls er im gewählten
Artefaktverzeichnis noch nicht vorhanden ist.

`nac kg process-ontology-schema-apply-owner-gated-live-plan --format json`
schreibt den nächsten Offline-Vertrag für die spätere Live-Ausführung. Der
Plan enthält den konkreten Freigabetext, Pflichtflags, verbotene Flags,
Stop-Regeln, Phasenplan und Evidence-Mindestumfang. Er deklariert den
zukünftigen Live-Runner ausdrücklich als noch nicht implementiert und bleibt
selbst `offline_only`.

## Grenzen

Der Dry-Run ist offline-only:

- keine Graph-Requests
- keine SharePoint-Schreiboperationen
- keine Schemaänderungen
- keine Request-Header
- keine Tokens oder Secrets
- keine Roh-Graph-Antworten

Der nächste Schritt kann ein redigiertes Dry-Run-Artefakt sein. Ein echter
Live-Apply bleibt ein separater Owner-Gate. Auch das Live-Readiness-Gate führt
keine Graph-Requests aus, schreibt keine SharePoint-Daten und verändert kein
Schema; es belegt nur, dass die später dafür nötigen Offline-Nachweise
vollständig und redigiert sind. Der Owner-gated Live-Plan führt ebenfalls keine
Graph-Requests aus; er macht nur die spätere Ausführungskante prüfbar.

Die Validatoren
[scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py)
,
[scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact.py)
und
[scripts/validate_process_ontology_sharepoint_schema_apply_artifact_index.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_artifact_index.py)
und
[scripts/validate_process_ontology_sharepoint_schema_apply_live_readiness_gate.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_live_readiness_gate.py)
und
[scripts/validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan.py)
prüfen diese Grenze im strikten Quality Gate.
