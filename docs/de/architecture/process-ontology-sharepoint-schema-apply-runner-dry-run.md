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

## Grenzen

Der Dry-Run ist offline-only:

- keine Graph-Requests
- keine SharePoint-Schreiboperationen
- keine Schemaänderungen
- keine Request-Header
- keine Tokens oder Secrets
- keine Roh-Graph-Antworten

Der nächste Schritt kann ein redigiertes Dry-Run-Artefakt sein. Ein echter
Live-Apply bleibt ein separater Owner-Gate.

Die Validatoren
[scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py)
und
[scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact.py)
prüfen diese Grenze im strikten Quality Gate.
