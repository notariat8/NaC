# Process-Ontology SharePoint Schema Apply Execution Contract

Diese Decision Note beschreibt die letzte Offline-Kante vor einem späteren
owner-gated SharePoint-Schema-Apply.

## Zweck

`nac kg process-ontology-schema-apply-execution-contract --format json` nimmt
den vorhandenen Apply-Plan und die Apply-Readiness und erzeugt daraus einen
ausführungsnahen Vertrag:

- beide Notar-Workspaces werden abgedeckt
- alle Workspace-Apply-Units bleiben sichtbar
- acht Ausführungsphasen ordnen Preflight, optionale Listen, Spalten,
  Choice-Erweiterungen, Readback und Evidence
- Graph REST v1 bleibt die einzige Datenebene
- `Sites.Manage.All` und Application-Owner-Pfad bleiben Pflicht
- ein späterer Live-Runner müsste zusätzlich `--owner-approved`,
  `--execute-live-schema-apply` und `--write-redacted-evidence` verlangen

## Grenzen

Der Contract selbst führt nichts aus:

- keine Graph-Requests
- keine SharePoint-Schreiboperationen
- keine Schemaänderungen
- keine Tokens, Auth-Header oder Secrets
- keine Roh-Graph-Antworten in Evidence
- keine automatischen Rollbacks

Jede spätere Live-Ausführung muss bei unklarer Idempotency, fehlenden IDs,
unerwarteten Statuscodes oder fehlender Permission fail-closed stoppen.

## Anschluss

Der nächste technische Anschluss wäre ein Dry-Run-Runner, der aus diesem
Contract konkrete geplante Requests und Evidence-Dateien erzeugt, weiterhin
ohne Live-Write. Erst danach ist ein separater Owner-Gate für echte
SharePoint-Schemaänderungen sinnvoll.

Der Validator
[scripts/validate_process_ontology_sharepoint_schema_apply_execution_contract.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_execution_contract.py)
prüft diese Grenze im strikten Quality Gate.
