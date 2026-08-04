# M365-BFF-Performance-Abnahme

Status: Issue #735 implementiert Azure-Monitor-Adapter, dedizierte
Azure-Blob-Lease und den zentralen, owner-gated Live-CLI-Befehl offline. Dieses
PR legt keine Azure-Ressource an oder ändert sie, greift nicht live auf Blob
oder Lease zu und sendet keinen Live-Lastrequest.

Die maschinenlesbaren Quellen sind der
[Abnahmevertrag](../../../workflows/contracts/m365-bff-performance-acceptance.contract.json)
und der
[Verification Contract](../../../workflows/verification-contracts/m365-bff-performance-acceptance.verification.json).
Der Modus lautet exakt `endpoint_scoped_conservative_measurement`.

## Aussagegrenze

Diese Lane misst ausschließlich einen synthetischen GET-Endpunkt. Sie erhebt
keine tenantweite SharePoint-Baseline, keine tenantweite Request-Allowance,
keine tenantweite Resource-Unit-Allowance und keine tenantweite monetäre
Baseline. Der Status dieser vier Aussagen ist explizit `NOT_CLAIMED`.

Ergebnisse dürfen weder auf andere Endpunkte noch auf die SharePoint-Kapazität
des Tenants hochgerechnet werden. Azure-Monitor-Werte sind konservativ
verwendete, app-weite Deltas der gebundenen Function App. Sie sind keine
Attribution zum gemessenen Endpunkt und keine SharePoint-Kapazitätsquelle.

## Festes Ziel

| Feld | Exakter Wert |
| --- | --- |
| Schema | `https` |
| Host | `func-nac-bff-test-funktion8.azurewebsites.net` |
| Methode | `GET` |
| Workspace | `notary_team_01` |
| Akte | `NAC-SYN-MATTER-001` |
| Pfad | `/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001/workbench-snapshot` |
| Query | `purpose=view_synthetic_matter_workspace` |
| Wire-Schema | `nac.workbench.snapshot/v1` |

Redirects, alternative Hosts, Klartext-HTTP, Cache-Busting und automatische
Retries sind verboten. Jede Antwort muss HTTP `200`, das exakte Wire-Schema
und höchstens `128 KiB` erfüllen. Body und Body-Hash werden nicht gespeichert.

## Fester Messplan

Ein vollständiger Lauf sendet exakt `500` synthetische GETs. Die
Phasenallokationen lauten `1, 1, 90, 120, 288`; die wiederholten Intervalle
lauten `10, 60, 300` Sekunden.

| Reihenfolge | Phase | GETs | Intervall |
| --- | --- | ---: | ---: |
| 1 | `cold_epoch_baseline` | 1 | sofort |
| 2 | `cold_epoch_candidate` | 1 | nach 1.200 Sekunden Runner-Idle |
| 3 | `interval_10s` | 90 | 10 Sekunden |
| 4 | `interval_60s` | 120 | 60 Sekunden |
| 5 | `interval_300s` | 288 | 300 Sekunden |

Es gilt durchgehend Client-Concurrency `1` und ein inklusives Maximum von
`6` Target-Dispatches pro Minute. Catch-up-Bursts, parallele Phasen und das
Wiederholen abgeschlossener Phasen sind nicht zulässig. Jeder reservierte
Versuch zählt; ein unklarer In-Flight-Ausgang wird nach einem Crash nicht
erneut gesendet.

Die Cold-Start-Klassifikation lautet nur dann `VERIFIED`, wenn die gebundene
Serverinstanz oder Start-Epoch nachweislich gewechselt hat. Sonst lautet sie
`INCONCLUSIVE`. Rohe Instanz- oder Epoch-Werte werden nicht gespeichert und
die Infrastruktur wird für die Messung nicht neu gestartet.

## Azure Monitor

Der offline implementierte Adapter liegt in
`src/nac_bff/azure_performance_monitor.py`. Er plant ausschließlich einen
read-only ARM-GET auf den festen `Microsoft.Insights/metrics`-Pfad der
gebundenen Function App. Zulässig sind exakt:

- API-Version `2023-10-01`
- Namespace `Microsoft.Web/sites`
- `OnDemandFunctionExecutionUnits`
- `OnDemandFunctionExecutionCount`
- `AlwaysReadyFunctionExecutionUnits`
- `AlwaysReadyUnits`
- `AlwaysReadyFunctionExecutionCount`
- Aggregation `Total`, Intervall `PT1M`
- Dimensionfilter `Instance eq '*'`

Jede Metrik wird als Summe aller `Total`-Punkte über alle eindeutigen
`Instance`-Serien ausgewertet. Die Fenster müssen UTC-minutengenau sein,
zwischen `60` und `86.400` Sekunden liegen und beim Lesen seit mindestens
`300` Sekunden abgeschlossen sein. Unbekannte Felder, fehlende Serien,
doppelte Instanzen oder Zeitstempel sowie nicht gesetzte Fenster blockieren.

Die statische Projektion des vollständigen Laufs beträgt exakt `30,000 GB-s`.
Vor jedem Dispatch wird das verbleibende Budget proportional zu den noch
offenen GETs berechnet. Das app-weite beobachtete Delta plus die Projektion der
verbleibenden GETs darf den inklusiven Cap von `120,000 GB-s` nicht
überschreiten. Alle Always-Ready-Metriken müssen exakt null sein. Der gleiche
Cap gilt nach dem finalen Settling; ein Überschreiten oder eine nicht
verfügbare Beobachtung bricht fail-closed ab.

## Exklusive Lease

Der dedizierte, offline implementierte Adapter liegt in
`src/nac_bff/azure_performance_lease.py`. Lease-Storage, BFF-Storage und
WORM-Evidence-Storage müssen getrennt sein. Der Adapter darf nur diese
Operationen anbieten:

1. `acquire(-1)` mit einer vorab persistent gespeicherten UUID
2. `assert_held`
3. `release`

Die persistente State Machine lautet exakt `ACQUIRE_INTENT`,
`ACQUIRE_IN_FLIGHT`, `HELD`, `RELEASE_INTENT`, `RELEASED`. Vor jedem
Target-Dispatch muss dieselbe Lease-ID auf demselben gebundenen Blob als
gehalten bestätigt werden. Resume setzt dieselbe Lease-ID, dieselbe
Zielbindung und dieselbe Lease-Bindung voraus.

Eine verlorene oder fremde Lease sowie Binding-Drift blockieren ohne Dispatch.
Automatisches Reacquire, Lease-Break, Blob-Delete und Blob-Create sind
verboten. Ein Ergebnis darf ausschließlich im dauerhaft geschriebenen Zustand
`RELEASED` den Status `PASSED` erhalten. `HELD`, ein unklarer Release-Ausgang
oder ein lediglich gesendeter Release reichen nicht aus.

## Owner-Gate und Evidence

Genau eine unveränderliche Owner-Freigabe bindet gemeinsam die entsperrte
WORM-Baseline-Bereitstellung, die Bereitstellung der dedizierten
Koordinationsinfrastruktur, die Runtime-Ausführung und die redigierte Evidence.
Teilfreigaben, stufenspezifische Freigaben und vom Caller gelieferte Hashes
werden vor dem ersten Write abgelehnt. Die Freigabe bindet diese Felder:

- `approved_commit_sha`
- `approved_tree_sha`
- `toolchain_attestations_sha256`
- `activation_evidence_sha256`
- `contract_sha256`
- `phase_plan_sha256`
- `measurement_policy_sha256`
- `monitor_binding_sha256`
- `lease_binding_sha256`
- `target_binding_sha256`
- `worm_baseline_source_sha256`
- `worm_baseline_parameters_sha256`
- `coordination_source_sha256`
- `coordination_parameters_sha256`
- `runtime_composition_sha256`
- `evidence_policy_sha256`
- `infrastructure_binding_sha256`

Jede Abweichung blockiert vor dem ersten Write. Monitor-, Lease-, Target-,
Source-, Parameter-, Runtime-, Evidence- und Infrastrukturbindung sind
voneinander getrennt und müssen gemeinsam zum unveränderlichen Kommentar
passen.

Evidence enthält nur redigierte Aggregate, die neun Gate-Bindungen, die
app-weiten Monitor-Deltas, das verbleibende Projektionsbudget,
Phasenaggregate, Abort-Code und den finalen Lease-Zustand. Die Aussage
`tenant-wide SharePoint baseline: NOT_CLAIMED` und
`tenant-wide monetary baseline: NOT_CLAIMED` bleiben darin ausdrücklich
erhalten. Einzelrequests, rohe Antworten, URLs, Header, Bodies, Tokens,
Tenant-/Benutzer-/Instanz-/Epoch-Werte und die rohe Lease-ID sind verboten.

## Gebundenes Live-Paket

Der bestehende Planbefehl bleibt offline und sendet null Requests:

```text
nac m365 teams-sharepoint bff-performance-acceptance-plan
```

Der zentral komponierte Live-Befehl ist offline implementiert:

```text
nac m365 teams-sharepoint bff-performance-acceptance
```

Nach Verifikation derselben unveränderlichen Owner-Freigabe ist die feste
Reihenfolge: entsperrte WORM-Baseline bereitstellen und zurücklesen,
Koordinationsinfrastruktur bereitstellen und inklusive RBAC zurücklesen,
Koordinations-Blob bootstrappen, Lease beziehen, exakt `500` synthetische GETs
ausführen, Azure Monitor finalisieren, Lease freigeben und redigierte Evidence
schreiben. Jede Stufe ist Voraussetzung der nächsten; Teildeployment oder
Binding-Drift blockiert fail-closed.

Die WORM-Baseline wird ausschließlich entsperrt bereitgestellt. Ein
irreversibler WORM-Policy-Lock ist nicht Teil dieser Lane und bleibt separat
owner-gated. In diesem PR sind Azure-Ressourcenerstellungen oder -änderungen,
Live-Blob-/Lease-Operationen, synthetische Target-Dispatches und irreversible
WORM-Locks jeweils exakt `0`.
