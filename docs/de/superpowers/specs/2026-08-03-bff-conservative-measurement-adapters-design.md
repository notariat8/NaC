# Konservative BFF-Messung mit Azure-Monitor und Blob-Lease

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: bff-conservative-measurement-adapters
leading_issue: https://github.com/notariat8/NaC/issues/733
risk_gate: External Service
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-08-03-bff-conservative-measurement-adapters.md
review_gates:
  - Privacy
  - Workflow
  - External Service
  - Human Approval
acceptance_ids:
  - AC-733-01
  - AC-733-02
  - AC-733-03
  - AC-733-04
  - AC-733-05
  - AC-733-06
  - AC-733-07
  - AC-733-08
validation_commands:
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_azure_performance_acceptance tests.test_nac_bff_azure_performance_monitor tests.test_nac_bff_azure_performance_lease tests.test_nac_bff_azure_performance_runtime tests.test_nac_bff_azure_performance_owner_gate tests.test_nac_bff_azure_performance_infrastructure_safety tests.test_nac_bff_azure_live_commands tests.test_nac_bff_performance_coordination_iac
  - python3 scripts/validate_m365_azure_bff_performance_acceptance.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
```

## Ziel

Die Performance-Lane misst ausschließlich das Verhalten des fest gebundenen,
synthetischen BFF-Endpunkts. Sie erhebt weder eine tenantweite
SharePoint-Baseline noch eine Aussage über allgemeine SharePoint-Kapazität.
Kanonisch bleiben `tenant_wide_sharepoint_baseline_claim: NOT_CLAIMED`,
`tenant_wide_sharepoint_request_allowance_claim: NOT_CLAIMED`,
`tenant_wide_sharepoint_resource_unit_allowance_claim: NOT_CLAIMED` und
`monetary_cost_claim: NOT_CLAIMED` voneinander getrennt.
Der erfolgreiche Lauf verwendet exakt 500 Requests, höchstens einen
gleichzeitigen Request und höchstens sechs Dispatches pro Minute. Der erste
Throttle-, Authentifizierungs-, Redirect-, Schema-, Lease- oder
Monitorfehler beendet den Lauf ohne Retry.

## Akzeptanzkriterien

- **AC-733-01:** Modus und Evidence lauten `endpoint_scoped_conservative_measurement`; Baseline, Request-Allowance, Resource-Unit-Allowance und monetäre Kosten lauten jeweils `NOT_CLAIMED`.
- **AC-733-02:** Der deterministische Plan bleibt auf 500 synthetische Reads, Parallelität eins und höchstens sechs Requests pro Minute begrenzt. Er behauptet aus den Ergebnissen keine tenantweite Baseline.
- **AC-733-03:** Der Azure-Monitor-Adapter liest ausschließlich die fünf festgelegten Flex-Consumption-Metriken am gebundenen Function-App-ARM-Resource-ID mit API `2023-10-01`, `Total` und festem Zeitfenster.
- **AC-733-04:** Der Lease-Adapter kennt ausschließlich `acquire`, `assert_held` und `release` für einen vorab angelegten dedizierten Blob. Break, Delete, Change und Renew sind nicht implementiert.
- **AC-733-05:** Monitor-, Messpolitik-, Lease-, Bootstrap- und Infrastruktur-Safety-Policy sowie Bicep-Quellen, kanonisch kompilierte ARM-Artefakte und Infrastrukturparameter sind getrennt hashgebunden. Erst ein vollständiger `SAFE`-Readback ergänzt `infrastructure_safety_evidence_sha256`; ETag und Lease-Bindung entstehen danach im gebundenen Blob-Readback.
- **AC-733-06:** Resume verwendet dieselbe Zielbindung und Lease-ID. Ein fremder, verlorener oder nicht beweisbarer Lease stoppt vor dem nächsten BFF-Dispatch.
- **AC-733-07:** Evidence enthält nur Aggregate und Hashbindungen, keine Token, Lease-ID, URLs, Tenant-/User-IDs oder Response-Inhalte.
- **AC-733-08:** Infrastruktur und Live-Ausführung bleiben bis zu einer einzigen commit-, tree-, toolchain-, policy-, monitor- und lease-gebundenen Owner-Freigabe offline.

## Messgrenze

Die Allokationen lauten exakt 1 Cold-Baseline, 1 Cold-Kandidat, 90 Reads im
endpointgebundenen Sample mit zehn Sekunden Abstand, 120 Reads über zwei
Stunden und 288 Reads im 24-Stunden-Soak. Die Summe ist 500. Alle Phasen sind
offen getaktet, ohne Catch-up, Retry oder automatische Parallelisierung. Die
statische Azure-Reserve beträgt konservativ 30.000 GB-s (`500 * 2 GB * 30 s`)
und wird über die verbleibende Arbeit projiziert. Vor jedem Dispatch schließt
die Berechnung diesen Dispatch ein; Evidence bindet
`projected_remaining_execution_units_gb_seconds`. Im erfolgreichen terminalen
Messnachweis ist dieser Wert exakt null, während die statische
Gesamtlaufprojektion 30.000 GB-s bleibt. Azure-Monitor-Metriken belegen nur
Ausführungszahl und -verbrauch der einen Function App. HTTP-Antworten und
Throttle-Signale belegen nur das Verhalten dieses Endpunkts während dieses
Laufs.

## Monitorgrenze

Der Adapter nutzt die Azure-Monitor-Metrics-REST-API `2023-10-01` über die
versiegelte Azure-CLI-REST-Grenze. Er akzeptiert nur
`OnDemandFunctionExecutionUnits`, `OnDemandFunctionExecutionCount`,
`AlwaysReadyFunctionExecutionUnits`, `AlwaysReadyUnits` und
`AlwaysReadyFunctionExecutionCount`, jeweils mit `Total` und `PT1M`.
`metricnamespace=Microsoft.Web/sites`, `AutoAdjustTimegrain=false` und
`ValidateDimensions=true` sind fest. Ein Dimensionfilter ist verboten; jede
Metrik muss pro Teilfenster exakt eine dimensionslose, app-weite `Total`-Serie
liefern. Der kumulative Lauf beginnt am owner-gebundenen UTC-Minutenanker;
Abschlusswerte werden erst nach mindestens 300 Sekunden Settlement gelesen.
Dimensionswerte, mehrere oder fehlende Serien, doppelte Minuten, abweichende
Timespans oder angepasste Timegrains blockieren. Execution Units
werden durch `1,024,000` in GB-s umgerechnet. Fehlende, negative,
nicht-endliche oder unbekannte Messwerte blockieren. Die Differenz ist eine
konservative App-weite Obergrenze und wird nie ausschließlich dem Test
zugerechnet.

Das finale gesetzte Fenster reicht vom Owner-gebundenen Anker bis
`monitor_window_end_utc` bei oder nach `measurement_finished_at_utc` und wird
erst nach diesem Ende plus settlement delay gelesen. Fensteranfang, -ende,
Beobachtungszeitpunkt und `monitor_settlement_delay_seconds` werden in die
finale Evidence gebunden. Ein gesetztes Fenster, das vor dem terminalen
Messzeitpunkt endet, kann keine Abnahme belegen.

## Lease-Grenze

Ein eigenes Storage-Konto und der Container `nac-bff-performance-leases` sind
von BFF-Deployment-Storage und WORM-Evidence getrennt. Der einzige Blob-Pfad ist
`locks/<target_binding_sha256>.lock`. Der Provisioning-Schritt legt ihn vor dem
Lauf an; die Runtime darf ihn nicht erzeugen oder löschen. Der Data-Plane-Adapter
nutzt Blob REST `2023-11-03`, einen unendlichen Lease (`-1`) und eine
vorgeschlagene UUID. Runner-Identität, Token-Audience
`https://storage.azure.com/.default`, Container-Scope, DataActions
`blobs/add/action`, `blobs/read` und `blobs/write`, Ausschluss von
Delete-/Owner-/Containerrechten sowie
eine ABAC-Bedingung für exakt den Blob-Pfad werden vor Acquire attestiert.
`assert_held` ist ein konditionales `HEAD` mit `If-Match` und
`x-ms-lease-id`; nur `200`, `locked`, `leased`, `infinite` und der gebundene
ETag gelten als Erfolg. Weil Azure RBAC Lease-Break nicht von Blob-Write trennt,
bilden fehlende Break-/Delete-Methoden, exakte Header-Allowlisten, die
versiegelte HTTP-Grenze und die hashgebundene Owner-Freigabe die zusätzliche
Sicherheitsgrenze.

## Crash und Resume

Vor dem einzigen Acquire werden `ACQUIRE_INTENT` und `ACQUIRE_IN_FLIGHT`
dauerhaft gespeichert. Erst ein erfolgreiches `assert_held` erzeugt `HELD`.
Ein Crash nach Remote-Acquire wird ausschließlich mit derselben UUID per
`assert_held` aufgelöst; jeder andere Ausgang blockiert ohne zweiten Acquire.
Vor jedem Target-Dispatch muss der Lease gehalten sein. Nach terminaler Messung
folgen `RELEASE_INTENT`, Release und Readback. Ein unklarer Release wird mit
derselben Lease-ID per HEAD klassifiziert; ist er noch gehalten, ist genau ein
zustandsgebundener Release-Reconcile zulässig. Erst dauerhaft gespeichertes
`RELEASED` erlaubt finale `PASSED`-Evidence. Break, Reacquire und Lease-ID-Wechsel
bleiben verboten und benötigen einen eigenen Recovery-Vertrag.
Der Release-Receipt muss exact `RELEASED` sowie die passende
`target_binding_sha256` und Lease-Bindung tragen. Ein Lifecycle-State-Hash ohne
diese exakten Werte ist kein Release-Nachweis.

## Owner-Bindung

Der kanonische Preimage enthält exakt Action, Commit, Tree, Toolchain-Hash,
Contract-Hash, Aktivierungs-Hash, Target-, Phasenplan-, Mess-, Monitor-, Lease-
und Bootstrap-Policy-Hash, Infrastrukturquellen-, Parameter- und Binding-Hash,
Correlation-ID und Owner-Login. Die Parameter binden insbesondere die drei
getrennten Storage-Konten, Provisioner-Objekt-ID, Client-IP, Zielbindung sowie
Tenant, Subscription, Resource Group, `Incremental`-Modus, Region und
kanonische Tags. Die Freigabe erlaubt genau die dadurch gebundene
Custom-Role-Definition und
-Zuweisung; andere Rechte- oder Credential-Änderungen bleiben verboten.

Die tatsächlichen BFF- und WORM-Storage-Resource-IDs sind Bestandteil des
Owner-Preimages. Vor Deployment bestätigt ein ARM-Readback diese IDs und eine
Namensverfügbarkeitsprüfung die Abwesenheit des Koordinationskontos. Nach
Deployment müssen effektive direkte, transitive gruppenbasierte und geerbte
RBAC-/ABAC-Zuweisungen vom Tenant-Root über die Management-Group-Kette bis zum
Container gegen Provisioner, Rolle, DataActions, Bedingung und Zielpfad geprüft
werden. Die kanonischen ARM-Artefakte müssen mit Bicep `0.45.15.27210` in CI
bytegenau reproduzierbar sein. Der starke Blob-ETag und die daraus abgeleitete Lease-Bindung
werden danach dauerhaft an State und Evidence gebunden, bevor ein Monitor-,
Lease- oder BFF-Aufruf erfolgt.
Das Offline-Gate liefert nur Owner-Bindungen. Der Runtime-Preflight validiert
den vollständigen Satz erst nach Ergänzung des Safety-Evidence-Hashs.
Ein lokaler, nicht blockierender Prozess-Fence umfasst einen State-Pfad vom
Preflight bis zur finalen Evidence und blockiert konkurrierende Ausführungen vor
dem Netzwerkzugriff.

Die TOCTOU-Abwehr misst die quellengebundenen Freigabeeingaben unmittelbar vor
dem ersten externen Command neu, prüft die Zielbindung unmittelbar vor jedem
Target-Dispatch und misst die versiegelte Azure-CLI-Toolchain unmittelbar vor
jedem Subprozess neu. Die Command-Grenze erlaubt nur argv-basiertes
`az rest --method get` mit der exakten, vom Adapter erzeugten kanonischen
Monitor-URL; Drift bei Methode, Body, Query-Reihenfolge oder Zusatzparametern
blockiert.

Vor dem Lease-Release wird das terminale Messergebnis vor dem finalen
Monitor-Read dauerhaft gespeichert. Ein fehlgeschlagener finaler Read erhält
die gehaltene Lease und wiederholt beim Resume nur diesen Read. Danach werden
Monitor-Attestation und Execution-Cap gegen Settled-Window-Abdeckung und null
projizierte Restarbeit validiert und vor dem Release in
`pending-finalization` gespeichert. Crash-Recovery darf den Release nur mit
derselben Lease-ID und Zielbindung reconciliieren; Acquire und Target-Dispatch
werden nicht wiederholt. Die terminale Finalisierung verlangt den exakten
`RELEASED`-Receipt und mindestens 500 finale On-Demand-Ausführungen, schreibt
redigiertes JSON und Markdown atomar und danach ein Completion-Manifest als
alleinigen Commit-Punkt. Der Pending-Datensatz wird erst nach dem Manifest
gelöscht. Fertige finale
Evidence wird idempotent, validiert und ohne Netzwerkzugriff zurückgegeben.
