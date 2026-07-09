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

Der Validator
[scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py)
prüft diese Grenze im strikten Quality Gate.
