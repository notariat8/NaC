# S4b BusinessCaseType Graph Write Edge

Status: offline implementiert in Issue [#694](https://github.com/notariat8/NaC/issues/694); Protected-PR-Abnahme ausstehend

## Ziel

S4b stellt eine begrenzte, fail-closed Graph-Write-Kante für genau fünf Operationen bereit:

- `case_create`
- `case_status_update`
- `task_create`
- `task_update`
- `business_case_type_backfill`

Der ausführliche Entwurf steht in der [S4b-Spec](../superpowers/specs/2026-07-28-business-case-type-graph-write-edge-s4b-design.md), die Umsetzungsschritte im [S4b-Implementierungsplan](../superpowers/plans/2026-07-28-business-case-type-graph-write-edge-s4b.md). Die übergreifende Identifier-Entscheidung bleibt die [BusinessCaseTypeId-ADR](business-case-type-id.md).

## Offline-Bedienkante

```bash
nac m365 teams-sharepoint business-case-type-write-dry-run --operation case_create --format json
```

`--operation` akzeptiert ausschließlich die fünf oben genannten Werte. Der Befehl verwendet synthetische Eingaben, gibt nur redigierte Struktur-, Gate- und Hashinformationen aus und hält diese Zähler bei null:

- Credential Reads,
- Live Factories,
- HTTP-, DNS- und Graph-Aufrufe,
- Tenant- und SharePoint-Writes.

Site-, Listen-, Identitäts- und fachliche Feldwerte werden nicht ausgegeben. Der Dry-Run plant Dedupe oder ETag-Freshness, genau einen Write und den Readback, führt diese Requests aber nicht aus.

## Identitäts- Und Sicherheitsgrenze

Ein späterer produktiver Write-Pfad benötigt eine von der BFF-UAMI getrennte Identität. Der [S4b-Domain-Contract](../../../workflows/contracts/business-case-type-graph-write-edge-s4b.contract.json) begrenzt sie auf `Sites.Selected` mit Site-Grant `write`; die BFF-UAMI bleibt auf `Sites.Selected` mit Site-Grant `read`. Create-Operationen sind über eindeutige Schlüssel dedupliziert, Patch-Operationen verlangen frische ETags, Backfill bindet die kanonischen S5-Hashes und unklare Ergebnisse bleiben in persistenter Reconciliation gesperrt.

## Noch Offen

Offline implementiert sind Domain, Plan, Edge, synthetischer Dry-Run, Tests, Contract, Verification Contract und Validator. Nicht implementiert oder freigegeben sind:

- produktive Factory- und Credential-Komposition,
- Entra-, Permission-, Schema- oder Tenant-Änderungen,
- Live-Graph- oder SharePoint-Writes,
- automatische Reconciliation-Schließung,
- produktive S6-/Evidence-Komposition.

Diese Schritte bleiben separat owner-gated. Der offline implementierte Stand behauptet keine produktive Write-Bereitschaft.

## Verifikation

Der [Verification Contract](../../../workflows/verification-contracts/business-case-type-graph-write-edge-s4b.verification.json) und der [S4b-Validator](../../../scripts/validate_business_case_type_graph_write_edge.py) prüfen Operationen, Bindungen, Redaction und Null-Live-Grenzen. Die zentrale Routing-Fläche steht im [Agent-Context-Index](../../../agent-context/index.json).
