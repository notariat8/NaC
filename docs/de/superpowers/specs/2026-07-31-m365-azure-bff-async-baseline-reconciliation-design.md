# M365 Azure-BFF-Reconciliation einer asynchron fertiggestellten Baseline

Status: Offline-Safety-Rework für geschützten PR
Datum: 31. Juli 2026
Scope: Read-only-Klassifikation und getrennte Terminalisierung des in Issue #719 gebundenen unterbrochenen Laufs

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-azure-bff-async-baseline-reconciliation-719
leading_issue: https://github.com/notariat8/NaC/issues/719
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-07-31-m365-azure-bff-async-baseline-reconciliation.md
review_gates:
  - External Service
  - Human Approval
acceptance_ids:
  - AC-719-01
  - AC-719-02
  - AC-719-03
  - AC-719-04
  - AC-719-05
  - AC-719-06
validation_commands:
  - python3 -m unittest tests.test_nac_bff_azure_interruption_baseline tests.test_nac_bff_azure_interruption_reconciliation tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_cli tests.test_m365_azure_bff_live_activation_contract
  - python3 scripts/validate_m365_azure_bff_live_activation.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/quality_gate.py --profile strict
  - git diff --check
```

## Ausgangszustand

Der in Issue #719 gebundene BFF-Lauf wurde während
`ensure_resource_group` durch einen Operator-Timeout extern beendet. Der
persistierte Runner-State enthält weiterhin exakt Schritt 1 als `PASSED`,
Schritt 2 als `RUNNING`, sechs gültig hashverkettete Ledger-Ereignisse und die
drei Journale `target`, `legacy` und `legacy_host` als `HELD`.

Nach dem Prozessende lief das bereits gestartete ARM/Bicep-Deployment
asynchron vollständig weiter. Die Ressourcengruppe steht auf `Succeeded` und
enthält die vollständige erwartete Baseline. Dieser Providerzustand darf den
persistierten Schritt 2 weder nachträglich auf `PASSED` setzen noch einen
Resume erlauben.

## Getrennte Providerklassifikationen

`RESOURCE_GROUP_ONLY` bleibt unverändert die Legacy-Klassifikation aus Issue
[#717](https://github.com/notariat8/NaC/issues/717). Sie akzeptiert
fail-closed nur die erfolgreiche Ressourcengruppe mit exakt leerem
Ressourceninventar. Ihre Terminalisierung bleibt an einen unveränderlichen
Owner-Kommentar in Issue #717 gebunden und führt keine Baseline-Hashfelder.

`BICEP_BASELINE_EXACT` ist die getrennte Klassifikation für Issue
[#719](https://github.com/notariat8/NaC/issues/719). Sie ist keine generische
Erlaubnis für nichtleere Ressourcengruppen. Sie gilt nur, wenn vorbereitete
Inputs vorhanden, vollständig hashgebunden und Providerinventar, ARM-
Deployment sowie Deployment-Operationen exakt aus diesen Inputs ableitbar
sind. Jede andere Klassifikation und jeder Mischzustand werden geschlossen
abgewiesen.

## Vorbereitete Hashbindungen

Die Baseline-Erwartung wird ausschließlich aus den bereits im Laufverzeichnis
vorbereiteten Artefakten gelesen:

- `prepared/prepared-inputs.redacted.json` bindet Aktivierungs-Hash, genehmigten
  Commit und Tree sowie die Digests der vorbereiteten Inputs.
- `prepared/main.json` ist der unveränderte Bicep-/ARM-Template-Snapshot.
- `prepared/main.parameters.json` ist der unveränderte Parameter-Snapshot.

Der genehmigte Commit und Tree werden zusätzlich mit dem vertrauenswürdig aufgelösten lokalen Git-Binary direkt gelesen. Der daraus berechnete Tree-Manifest-Hash und der Blob-Hash von `deploy/runtime/azure/nac-bff/infra/compiled/main.json` müssen exakt mit dem Prepared-Manifest und `prepared/main.json` übereinstimmen. Git-Replace-Refs sind für alle Reads deaktiviert; Listing und Archiv adressieren ausschließlich den genehmigten Tree-Objekthash, und jedes Archiv-Blob wird erneut gegen seine Git-Blob-ID geprüft. Selbstkonsistente vorbereitete Dateien können daher keine falsche Git-Provenienz behaupten. Alle neun gebundenen Bicep-Parameter werden auf exakte Schlüsselmenge und Werte geprüft.

Der SHA-256 des rohen Prepared-Manifests,
`prepared_inputs_manifest_sha256`, der Template-Snapshot-Hash
`bicep_snapshot_sha256` und der Parameter-Snapshot-Hash
`bicep_parameters_snapshot_sha256` müssen den Manifestwerten und den
tatsächlichen Bytes entsprechen. Aus Template-Metadaten, kanonischem
Ressourcengraph, Deploymentname, kanonisch normalisierten Parametern und der
exakten Operationstypverteilung entsteht die kanonische Baseline-Erwartung.
Ihr SHA-256 ist `baseline_expectation_sha256`.

Fehlende, partielle oder syntaktisch ungültige vorbereitete Artefakte liefern
`INTERRUPTION_BASELINE_BINDING_INVALID`. Abweichende Aktivierungs-, Commit-,
Tree-, Manifest-, Template- oder Parameterbindungen liefern
`INTERRUPTION_BASELINE_BINDING_MISMATCH`.

## Exakte Baseline

Das Top-Level-Inventar enthält exakt sieben Ressourcen, keine weniger und
keine zusätzlichen:

1. Storage Account (`Microsoft.Storage/storageAccounts`)
2. Log Analytics Workspace (`Microsoft.OperationalInsights/workspaces`)
3. App Service Plan (`Microsoft.Web/serverfarms`)
4. User Assigned Managed Identity (`Microsoft.ManagedIdentity/userAssignedIdentities`)
5. Application Insights Component (`Microsoft.Insights/components`)
6. Function App (`Microsoft.Web/sites`)
7. Smart Detection Action Group (`Microsoft.Insights/actionGroups`)

Für jede Ressource müssen die erwartete vollständige ARM-ID, der Typ, der
deterministisch abgeleitete Name, die Ressourcengruppe, die Region, die Tags
sowie erwartetes `kind` und SKU übereinstimmen. Die Smart Detection Action Group ist die einzige globale
Ressource und besitzt keine Workload-Tags. Deployment-Outputs müssen exakt die
Function-App-ID und den Hostnamen sowie Ressourcen-, Client- und Principal-ID
der User Assigned Managed Identity binden. Zusätzlich werden die User Assigned
Managed Identity und die Identity-Zuweisung der Function App gezielt read-only
gelesen. Tenant-, Client- und Principal-ID sowie die exakt eine Zuweisung vom
Typ `UserAssigned` müssen mit Inventar und Deployment-Outputs übereinstimmen.

Das ARM-Deployment muss `Succeeded`, `Incremental` und an den vorbereiteten
Template- und Parameter-Hash gebunden sein. Es besitzt exakt zwölf
erfolgreiche Deployment-Operationen mit folgender Typverteilung:

- zwei `Microsoft.Authorization/roleAssignments`
- je eine Operation für `Microsoft.Insights/components`,
  `Microsoft.Insights/components/currentBillingFeatures`,
  `Microsoft.ManagedIdentity/userAssignedIdentities`,
  `Microsoft.OperationalInsights/workspaces`,
  `Microsoft.Storage/storageAccounts`,
  `Microsoft.Storage/storageAccounts/blobServices`,
  `Microsoft.Storage/storageAccounts/blobServices/containers`,
  `Microsoft.Web/serverfarms`, `Microsoft.Web/sites` und
  `Microsoft.Web/sites/config`

Jede Deployment-Operation muss zusätzlich auf die exakte erwartete
Top-Level-, Child- oder Role-Assignment-ARM-ID zeigen. Die Smart Detection
Action Group wird gezielt gelesen; Aktivierungsstatus und sämtliche erwarteten
E-Mail-, SMS-, Webhook-, Azure-App-Push- und Voice-Receiver müssen exakt sein.
Zusätzlich werden alle zwölf Deployment-Zielressourcen gezielt read-only
gelesen. Ein exakt gebundener Azure-Resource-Graph-POST enumeriert ergänzend
alle Ressourcen und Authorization-Ressourcen im Ziel-Scope. Seine Menge muss
exakt der Vereinigung aus Inventar und Deployment-Zielen entsprechen; weder
zusätzliche Child-Ressourcen noch weitere Role Assignments sind zulässig.
Storage-Sicherheitsoptionen, Blob-Retention, Container-Public-Access,
Workspace-/Insights-Authentisierung, Function-App-Konfiguration, Appsettings
und beide Role Assignments müssen dem Bicep-Sollzustand als exakte
Property-Objekte entsprechen; nach außen gelangt nur eine redigierte
Zielhash-/Anzahl-/Ergebnis-Zusammenfassung.

Teilinventar, Zusatzressourcen, falsche Operationenzahl, fehlgeschlagene
Operationen sowie ID-, Ziel-ID-, Kind-, SKU-, Typ-, Namens-, Regions-, Tag-,
Smart-Detection-, Deployment-, Output- oder Managed-Identity-Drift liefern
`PROVIDER_OBSERVATION_INVALID`.

## Doppelte Read-only-Beobachtung

Jeder Snapshot liest nur Azure-Zustand: Account, die drei erwarteten Provider,
Ressourcengruppe und Ressourceninventar sowie bei nichtleerem Inventar das
gebundene Deployment, dessen Operationen sowie die User Assigned Managed
Identity und die Function-App-Identity-Zuweisung. Das Inventar wird innerhalb
jedes Snapshots ein zweites Mal gelesen. Danach wird der vollständige Snapshot
erneut erhoben. Beide kanonischen Beobachtungen müssen bytegleich sein und
denselben `provider_observation_sha256` ergeben; andernfalls gilt
`PROVIDER_OBSERVATION_DRIFT`.

Die Inspection verändert weder lokale Artefakte noch Azure- oder
Tenantzustand. Sie gibt `MIDRUN_RECONCILIATION_REQUIRED`, die redigierten
Beobachtungs- und Bindungshashes sowie den kanonischen Owner-Kommentar aus.
Sie ist keine Terminalisierung und keine Erfolgsklassifikation.

## Separate #719-Terminalisierung

Die alte #632-Live-Freigabe identifiziert ausschließlich den unterbrochenen
Lauf. Für `BICEP_BASELINE_EXACT` verlangt
`--confirm-terminalize-and-release` zusätzlich einen unveränderlichen
Owner-Kommentar aus Issue #719. Gegenüber der Legacy-#717-Bindung enthält
dessen kanonischer Body zusätzlich exakt:

- `provider_classification` mit `BICEP_BASELINE_EXACT`
- `baseline_expectation_sha256`
- `prepared_inputs_manifest_sha256`
- `bicep_snapshot_sha256`
- `bicep_parameters_snapshot_sha256`

Alle bisherigen State-, Ledger-, Lock-, Provider-, Reconciler- und
Owner-Bindungen bleiben ebenfalls Pflicht. Die Aktion bleibt exakt
`TERMINALIZE_AND_RELEASE_LOCK_ONLY`. Vor der ersten lokalen Mutation werden
State, Locks, vorbereitete Inputs, Owner-Kommentar und doppelte
Providerbeobachtung unter exklusivem `flock` erneut geprüft. Unmittelbar vor
der ersten lokalen Mutation wird eine dritte read-only Providerbeobachtung
erhoben und gegen den owner-gebundenen Beobachtungshash verglichen. Ebenso
werden die drei aktuellen Journalbytes gegen die owner-gebundenen Lock-Hashes
geprüft; Recovery akzeptiert ausschließlich den deterministisch aus dem
ursprünglichen `HELD`-Journal ableitbaren `RELEASED`-Hash.

Die einzige zulässige Terminalisierung beendet Schritt 2 als `FAILED` mit
`EXTERNAL_PROCESS_INTERRUPTED_AFTER_WRITE`, setzt den Lauf auf
`FAILED_PARTIAL`, persistiert die Terminal-Evidence, schreibt
`MIDRUN_RELEASE_IN_PROGRESS` und hängt `RELEASED` append-only an alle drei
Lock-Journale an. Es gibt kein Resume, keinen Provider-Write, keinen
automatischen Retry, Rollback oder Delete und keine nachträgliche
Erfolgsklassifikation. Ein gerissener Release darf nur mit derselben
unveränderten #719-Bindung idempotent fortgesetzt werden. Ein partieller
Journal-Append ist nur recoverbar, wenn er ein striktes Bytepräfix des
deterministisch erwarteten `RELEASED`-Records ist. Nach erneuter Runtime-,
State-, Pfad- und Descriptor-Prüfung wird ausschließlich dieser Tail auf den
owner-gebundenen Ausgangszustand zurückgesetzt; unbekannte Tails blockieren.

## Akzeptanzkriterien

- **AC-719-01:** `RESOURCE_GROUP_ONLY` bleibt unverändert fail-closed auf das
  leere Legacy-#717-Inventar und die #717-Terminalisierungsbindung begrenzt.
- **AC-719-02:** `BICEP_BASELINE_EXACT` wird nur aus dem commit-, tree- und
  aktivierungsgebundenen Prepared-Manifest, Template- und Parameter-Snapshot
  sowie der kanonischen Baseline-Erwartung klassifiziert.
- **AC-719-03:** Nur exakt sieben erwartete Top-Level-Ressourcen und zwölf
  erfolgreiche ARM-Deployment-Operationen werden akzeptiert; Teilinventar,
  Zusatzressourcen und ID-, Typ-, Regions-, Tag-, Identity-, Deployment- oder
  Snapshot-Drift blockieren mit stabilen Fehlercodes.
- **AC-719-04:** Inspection führt zwei identische read-only
  Providerbeobachtungen ohne lokale Mutation aus und erzeugt einen
  kanonischen #719-Owner-Kommentar mit allen Baseline-Hashes.
- **AC-719-05:** Die separate Owner-Entscheidung erlaubt ausschließlich
  `TERMINALIZE_AND_RELEASE_LOCK_ONLY` zum Terminalzustand `FAILED_PARTIAL`;
  Resume, Azure-/Tenant-Write, Retry, Rollback, Delete und `PASSED` bleiben
  verboten.
- **AC-719-06:** Fokussierte Tests, Contract-Validator,
  Spec-Traceability-, Sprach-, Link- und Strict-Gates sowie unabhängiger
  Review und Remote-CI bestehen.
