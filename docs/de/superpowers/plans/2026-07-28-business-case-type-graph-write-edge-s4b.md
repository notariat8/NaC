# BusinessCaseType Graph Write Edge S4b Implementierungsplan

**Status:** offline implementiert; Protected-PR-Integration ausstehend
**Spec:** [BusinessCaseType Graph Write Edge S4b Design](../specs/2026-07-28-business-case-type-graph-write-edge-s4b-design.md)
**Leading Issue:** [GitHub #694](https://github.com/notariat8/NaC/issues/694)
**Delivery Mode:** Protected PR
**Risk Gates:** Privacy, Human Approval, External Service
**Thresholds:** Live Graph Calls = 0; Tenant Writes = 0; Credential Reads = 0; Live Factories = 0

## Ziel

Eine eigenständige Offline-S4b-Kante plant und orchestriert fünf exakt
begrenzte BusinessCaseType-Schreiboperationen mit separater Write-Identität,
Deduplizierung, ETag-Concurrency, S5-Hashbindung und injiziertem
Evidence-/Reconciliation-Hook.

## Plan Review Fix

Der erste Plan hätte Create-Idempotenz nur über einen lokalen Hash abgebildet.
Das Review verlangte zusätzlich den GET auf die bereits als eindeutig
definierten SharePoint-Felder `NacCaseId` und `NacTaskId`; Mehrdeutigkeit wird
sticky reconciled. Außerdem schließt ein erfolgreicher Readback nach unklarem
Write die Reconciliation nicht automatisch. Diese Korrekturen sind im
Contract und in Negativtests gebunden. Der Safety-Fixpass ergänzt die vollständige kanonische Execute-Revalidierung, `$top=2` mit `nextLink` als Ambiguität, strikte tatsächliche Readbacks, dauerhaft bestätigte prozessweite Reconciliation und feste redigierte
Transportfehler. Der erneute Fixpass ersetzt `clear` als alleinige Freigabe
durch persistente Intent-Generationen samt Closure-Proof und bindet
PATCH-5xx-Readbacks ausschließlich an `plan.mutation.item_id`. Der finale Safety-Fixpass macht persistiertes `closed` auch bei fehlgeschlagener
nachgelagerter Closure-Bestätigung terminal und bindet jeden Target-Hash
unabhängig von der aktiven Operation an Workspace, Site und beide Listen-IDs.

## Arbeitspakete

- [x] **WP1 – Tests first:** synthetische Fixtures und rote Tests für fünf
  Operationen, Binding-Drift, Legacy-Gate, S5-Hash, Dedupe, ETag, 412 und
  Reconciliation, Paging, 409/412, Plan-Manipulation, Restart-Fail-closed und
  Fehlerredaktion, frische Hook-Instanz über gemeinsamem Store, physisch
  geschlossenes Intent mit verlorener Bestätigung, inaktive Listen-Drift in
  beide Richtungen und fremde PATCH-5xx-Response-ID.
- [x] **WP2 – Domain:** geschlossene `BusinessCaseTypeMutation` mit exakten
  Feldmengen und kanonischer S5-Prüfung.
- [x] **WP3 – Plan:** immutable Workspace-/Site-/Listen-/Rollen-/Zweck-/
  Approval-/Identitätsbindung, Target-Hash über Workspace, Site und beide
  Listen-IDs, kanonischer Plan-Hash, vollständige Execute-Revalidierung und
  exakte Graph-v1.0-Ziele.
- [x] **WP4 – Edge:** Dedupe/Freshness, Intent, einzelner Write, Outcome,
  strikter Readback und dauerhaft bestätigte, prozessweit sticky
  Reconciliation mit persistenter Intent-Generation, terminaler monotoner Closure
  und Closure-Proof über injizierte Ports.
- [x] **WP5 – Contract:** S4b-Domain-/Verification-Contract, Standalone-
  Validator sowie DE/EN-Spec/Plan.
- [x] **WP6 – Review/Fix:** vollständige Scope-Diff, fokussierte Tests,
  Validator, `compileall`, Traceability, Sprachparität und Linkprüfung; alle
  Safety-Findings behoben.
- [ ] **WP7 – Integration:** Hauptagent ergänzt gemeinsame
  Index-/Quality-Gate-/CLI-Flächen und führt Protected-PR-Gates aus.

## Nicht Enthalten

- Live-Factory, HTTP-Client oder Credential-Lader,
- Permission-, Schema- oder Tenant-Write,
- Änderung der BFF-UAMI,
- zentrale CLI-, README-, Index-, GANTT-, Agent-Context- oder S6a-Dateien,
- automatische Reconciliation-Schließung oder produktive S6-Komposition.

## Validierung

1. fokussierte Unit- und Contracttests,
2. S4b-Standalone-Validator und `compileall`,
3. Spec-Traceability, Sprachparität und Doc-Links,
4. Scope- und Whitespace-Diff,
5. unabhängiges Implementierungsreview vor Übergabe.
