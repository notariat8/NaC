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

`nac kg process-ontology-schema-apply-live-readiness-gate --format json
--workspace-id notary_team_01` schreibt daraus ein letztes Offline-Gate vor
einem späteren echten SharePoint-Schema-Apply. Dieser Slice akzeptiert bewusst
nur `notary_team_01`; das Gate bindet genau diesen freigegebenen Workspace. Das
Gate prüft, ob Execution Contract, Workspace-Readiness, Runner-Dry-Run,
redigierter Artefaktindex, Redaktionsgrenze und Owner-Gate vollständig
vorliegen. Der Befehl schreibt zusätzlich den redigierten Artefaktindex, falls
er im gewählten Artefaktverzeichnis noch nicht vorhanden ist.

`nac kg process-ontology-schema-apply-owner-gated-live-plan --format json`
schreibt den nächsten Offline-Vertrag für die spätere Live-Ausführung. Der
Plan enthält den konkreten Freigabetext, Pflichtflags, verbotene Flags,
Stop-Regeln, Phasenplan und Evidence-Mindestumfang. Der Live-Runner-Befehl
existiert, der Plan bleibt aber selbst `offline_only` und führt keine
Graph-Requests aus.

`nac kg process-ontology-schema-apply-owner-gated-runner-contract --format json`
schreibt anschließend den ausführungsnahen Runner-Vertrag. Er bindet den
späteren Befehl `nac kg process-ontology-schema-apply-live` an 68 geplante
Runner-Schritte, Owner-Gate, Pflichtflags, Stop-before-mutation-Regeln und
redigierte Evidence. Der Vertrag markiert den Live-Runner-Befehl als
implementiert, führt aber selbst keine Graph-Requests aus.

`nac kg process-ontology-schema-apply-live --format json --owner-approved
--workspace-id notary_team_01 --owner-approval-reference <approval-reference>
--reason "Freigegebener Schema-Apply für Workspace-Rollout"
--execute-live-schema-apply --live-readiness-gate <gate.json>
--correlation-id <id> --write-redacted-evidence` schreibt den owner-gated
Live-Runner-Envelope. Der Befehl blockt ohne vollständige Pflichtflags oder
ohne bestandenes, für `notary_team_01` gebundenes Live-Readiness-Gate. Mit
vollständigem Gate erzeugt er die redigierte Start-Evidence für den
Graph-REST-Dispatch, führt in diesem Slice aber noch keine Graph-Requests aus
und ändert kein SharePoint-Schema.

`nac kg process-ontology-schema-apply-live-dispatch --owner-approved
--workspace-id notary_team_01 --owner-approval-reference <approval-reference>
--reason "Freigegebener Schema-Apply für Workspace-Rollout"
--execute-live-schema-apply --live-readiness-gate <gate.json>
--correlation-id <id> --write-redacted-evidence` ist der owner-gated
Graph-REST-Dispatcher hinter diesem Envelope. Er nutzt nur Microsoft Graph
v1.0, sequenziert Preflight, Mutation und Readback, stoppt beim ersten Fehler
und schreibt redigierte Evidence. Der Befehl ist der erste Pfad, der echte
SharePoint-Schemaänderungen ausführen kann; deshalb bleibt jede Nutzung
separat owner-approved.

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
Graph-Requests aus; er macht nur die spätere Ausführungskante prüfbar. Der
Runner-Vertrag bleibt ebenfalls offline und ist die letzte Schnittstellenkante
vor der tatsächlichen Runner-Implementierung. Der Live-Runner-Envelope ist die
erste implementierte Befehlsfläche dieser Runner-Kante. Der Graph-REST-
Dispatcher ist als owner-gated Live-Pfad implementiert und wird mit Fake-Client
im Strict Gate geprüft; echte Tenant-Schreibläufe bleiben separate Owner-
Approvals.

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
und
[scripts/validate_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract.py)
und
[scripts/validate_process_ontology_sharepoint_schema_apply_live_runner.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_live_runner.py)
und
[scripts/validate_process_ontology_sharepoint_schema_apply_graph_dispatcher.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_graph_dispatcher.py)
prüfen diese Grenze im strikten Quality Gate.
