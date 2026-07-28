# BusinessCaseType Immutable Evidence S6a Implementierungsplan

**Status:** offline in Umsetzung; Live-Mutationen bleiben blockiert
**Spec:** [BusinessCaseType Immutable Evidence S6a Design](../specs/2026-07-20-business-case-type-immutable-evidence-s6-design.md)
**Leading Issue:** [GitHub #687](https://github.com/notariat8/NaC/issues/687)
**Delivery Mode:** Protected PR
**Risk Gates:** Privacy, Human Approval, External Service
**Thresholds:** Network Calls = 0; Provider Calls = 0; Tenant Calls = 0; Tenant Writes = 0; Credential Reads = 0; Live Mutations = 0; Production-WORM-Claim = false

## Ziel

S6a implementiert einen redigierten, deterministischen Evidence-Kern für
BusinessCaseType-Mutationen ausschließlich mit synthetischen
In-Memory-Adaptern. S6b-Provideradapter und S7-Live-Freigabe bleiben getrennt.

## Acceptance-Mapping

- **AC-S6-01:** Exakte Phasenfolge, lückenlose Sequenz und SHA-256-Kette.
- **AC-S6-02:** Persistiertes Intent, Outcome/Readback, Operations- und
  Delivery-Key sowie persistierte Tenant-/Principal-Key- und geordnete
  Event-Hash-Sequenz-Bindungen.
- **AC-S6-03:** Correlation, Actor, Operator und Approver sind an denselben
  Tenant gebunden; Actor, Operator und Approver nutzen denselben
  Principal-Key-Binding-Hash. Abweichungen schlagen fail-closed fehl.
- **AC-S6-04:** Port-Verträge verlangen deterministische
  kettenkopfgebundene Idempotency-Keys für Anchor/WORM, Write-ahead-Fortschritt
  und crash-sicheren Resume.
- **AC-S6-05:** Mindestens zehn Jahre Retention und Legal-Hold-Metadaten.
- **AC-S6-06:** Principal-key-gebundene Pre-Claim-Autorisierung und
  Event-Hash-Präfix werden atomar in eine vollständige Publication-Sequenz
  konsumiert; Completed-Replay prüft Kettenlänge und Providerbindungen.
- **AC-S6-07:** Exakte Offline-/Live-Status und alle sechs Nullzähler.
- **AC-S6-08:** Negative Gates einschließlich externer
  `ImmutableEvidenceError` werden fail-closed und ohne Providerdetails
  behandelt.

## Arbeitspakete

- [x] **WP1 – Scope:** S3-Katalog und Runtime als Implementierungsquelle
  prüfen; keine Live-Funktionen ergänzen.
- [x] **WP2 – Envelope:** 20 kanonische Slugs, echte CatalogVersion,
  `delivery_key_sha256`, tenantgebundene HMAC-ETags und alle persistierten
  Principal-/Security-Bindings synchronisieren.
- [x] **WP3 – Ports:** finale `ReconciliationStorePort`-Operationen,
  optionale `require`-Bindings, persistierte Pre-Claim-Autorisierung und
  geordneten Event-Hash-Präfix, deren atomaren Claim-Verbrauch in eine
  vollständige Sequenz, Publication-Progress, Vier-Augen-Resume und
  deterministische Anchor-/WORM-Idempotenz dokumentieren.
- [x] **WP4 – Completion:** Completed Result und Progress gegen aktuelle
  Kettenlänge, ACKs, Head sowie Anchor-/Signatur-/WORM-Bindungen prüfen.
- [x] **WP5 – Fehlergrenze:** alle externen Port-Fehler einschließlich
  `ImmutableEvidenceError` auf feste redigierte Meldungen begrenzen.
- [x] **WP6 – Contract/Doku:** Contract, Validator und DE/EN Spec/Plan
  synchronisieren.
- [x] **WP7 – Abschluss:** fokussierte Validator-, Contract-, Parity- und
  Traceability-Checks sowie Diff-Prüfung.

## Nicht Enthalten

- Produktionsadapter oder neue Live-Funktionen,
- Graph-/SharePoint-/Entra-/Azure-Aufrufe,
- Live-Schema-Apply, Backfill, Cutover, Rollback oder Cleanup,
- Behauptung einer revisionssicheren Produktionsablage.

## Validierung

1. S6-Standalone-Validator und fokussierter Contracttest,
2. `nac contracts verify`,
3. Sprachparität und Spec-Traceability,
4. `git diff --check` ausschließlich für die sechs S6-Dateien.
