# BusinessCaseType Azure Blob WORM S6b Design

Status: `S6B_AZURE_WORM_ADAPTER_READY_OFFLINE`
Live-Status: `BLOCKED_PENDING_S7_APPROVAL`
Führendes Issue: [#693](https://github.com/notariat8/NaC/issues/693)
Domain-Contract: [business-case-type-azure-blob-worm-s6b.contract.json](../../../../../workflows/contracts/business-case-type-azure-blob-worm-s6b.contract.json)
Lock-Contract: [azure-blob-worm-irreversible-lock-s6b.contract.json](../../../../../workflows/contracts/azure-blob-worm-irreversible-lock-s6b.contract.json)
Verification-Contract: [business-case-type-azure-blob-worm-s6b.verification.json](../../../../../workflows/verification-contracts/business-case-type-azure-blob-worm-s6b.verification.json)
Plan: [Implementierungsplan](../plans/2026-07-28-business-case-type-azure-blob-worm-s6b.md)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-azure-blob-worm-s6b
leading_issue: https://github.com/notariat8/NaC/issues/693
risk_gate: External Service
delivery_mode: Protected PR
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S6B-01
  - AC-S6B-02
  - AC-S6B-03
  - AC-S6B-04
  - AC-S6B-05
  - AC-S6B-06
  - AC-S6B-07
validation_commands:
  - python3 -m unittest tests.test_immutable_evidence tests.test_azure_blob_worm tests.test_azure_blob_worm_contract
  - python3 scripts/validate_business_case_type_azure_blob_worm.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - git diff --check
```

## Ziel und Offline-Grenze

`AzureBlobWormJournal` implementiert den unveränderten `WormJournalPort` für
eine autoritative Azure-Blob-Immutable-Evidence-Kopie eines On-Prem-Publishers.
Der Slice enthält nur Portplanung und `FakeAzureBlobWormTransport`: keine
HTTP-, Azure-, Credential-, Permission-, Deployment-, Lock- oder
Live-Factory-Aktion. S7 bleibt blockiert.

## AC-S6B-01: Adapter-Semantik

`commit(records, anchor, *, idempotency_key_sha256)` und
`readback(receipt_ref)` bleiben exakt kompatibel zu S6a. Vollständiger
Readback prüft kanonische Bytes, Chain, Anchor, Metadaten, CMK, Policy und die
exakt gebundene Blob-Version. Öffentliche Fehler sind immer
`AzureBlobWormError("Azure Blob WORM operation rejected")` ohne Cause,
Context, Providertext oder Klartext-Identifier.

## AC-S6B-02: Create und Idempotenz

Der Schlüssel ist ausschließlich der kanonische S6a-Schlüssel
`_publication_operation_key("worm-commit", chain_head_sha256)`. Jeder Put nutzt
`If-None-Match: *`.

Die Offline-REST-Planung bildet Azure realistisch ab:

1. HTTP `201` muss die rohe `x-ms-version-id` liefern; anschließend folgt GET
   mit genau dieser rohen `versionid`.
2. HTTP `412` darf keine Version selbst behaupten. Der Adapter führt List Blob
   Versions aus und liest jede Kandidatin mit ihrer rohen `versionid`.
3. Genau eine vollständig passende Version ist erforderlich. Keine,
   mehrdeutige oder fremde Versionen blockieren.
4. Public readback löst die gehashte Receipt-Bindung lokal auf und übergibt dem
   Transport ausschließlich die rohe `version_id`, niemals einen Hash-Selektor.

Post-Create-Response-Loss und echte Same-Blob-Concurrency erzeugen höchstens
einen Create-Effekt und niemals ein Overwrite.

## AC-S6B-03: Policy- und Retention-Beleg

Alle potenziell fehlschlagenden Event-Timestamp-, Retention-, Overflow- und
Policy-Berechnungen laufen vor Put. Auch ein gültiger zukünftiger
S6a-`occurred_at` bestimmt nicht den Azure-Retentionsbeginn. Der Fake setzt
`created_at` beim Create und berechnet `retention_until` ab diesem Zeitpunkt.
Ungültige oder überlaufende Retention erzeugt null Create-Effekte; Retry bleibt
sicher.

Die exakte committed Version muss belegen:

- `Locked` statt nur eines Container-Defaults;
- mindestens `ceil(years * 365.25)`, für zehn Jahre also `3653` Tage ab
  `created_at`;
- getrennte Legal-Hold-Fähigkeit aus `container-policy-properties` und aktiven
  `legal_hold_active`-Zustand;
- dedizierten Encryption-Scope, `Microsoft.Keyvault` und gehashte CMK-Referenz.

## AC-S6B-04: Provider-Drift und Redaction

Der Transport liest für Commit und Readback frisch den tatsächlichen
Provider-Kontext: Tenant-ID, Subscription-Resource-ID und Storage-Resource-ID.
Nur domain-separierte Hashbindungen gelangen in Objekt, Metadaten und Evidence.
Die Bicep-Baseline emittiert weder Klartext-IDs noch selbstbehauptete Hashes.
Der erwartete `provider_context_binding_sha256` stammt aus einer Owner-approved,
commit- und hashgebundenen Deployment-Attestation; der tatsächliche Wert stammt
aus einem davon unabhängigen frischen Azure-Readback. Erwartungs- und Ist-Wert
dürfen nicht aus demselben Readback abgeleitet werden.

Stale Container-Metadaten, Subscription-/Resource-Drift oder Tenant-Transfer
blockieren fail closed. Keine Klartext-Tenant-, Subscription- oder Resource-ID
erscheint in redigierter Evidence oder öffentlichen Fehlern.

## AC-S6B-05: Dedizierte Bicep-Baseline

Die Baseline nutzt `Microsoft.Storage/...@2023-05-01`, emittiert kein ungültiges
`immutabilityPolicy.properties.state` und behauptet keinen Compile-Erfolg. CMK,
CMK-UAMI und Writer-UAMI sind dediziert; keine bestehende Identität wird
erweitert.

Die Writer Data Role enthält exakt:

- `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action`;
- `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read`.

Eine getrennte Management-Read-Role am Storage-Account-Scope enthält exakt:

- `Microsoft.Storage/storageAccounts/blobServices/containers/read`;
- `Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies/read`;
- `Microsoft.Storage/storageAccounts/encryptionScopes/read`.

Blob-`write`, Delete, Owner und Contributor sind ausgeschlossen.

## AC-S6B-06: Zero Live und S7

Netzwerk-, Azure-, Credential-, Tenant-Write- und Lock-Zähler bleiben null.
Es existiert keine Live-Factory-Verdrahtung. Der Status bleibt
`S6B_AZURE_WORM_ADAPTER_READY_OFFLINE`; ohne separaten Owner-Gate- und
`Locked`-Readback bleibt `BLOCKED_PENDING_S7_APPROVAL` verbindlich.

## AC-S6B-07: Verträge, Tests, Review und Lock-Plan

Domain-, Verification- und separater irreversibler Lock-Contract bilden den
Slice maschinenlesbar ab. Der Lock-Plan ist rein offline und bindet exaktes
Target, Provider-Kontext, Policy, API/Operation, ETag, Request-Hash,
unterschiedliche Operator-/Approver-Referenzen sowie Pre-/Post-Readback.
Target-Drift, stale ETag und Request-Hash-Drift blockieren; es gibt keine
Live-Lock-Kante.

Die zentrale Adoption bleibt Integrationsschritt und wird in Track B nicht
überschrieben. Lokal sind `az bicep`, `bicep` und `npx bicep` nicht verfügbar;
es gibt keinen lokalen Compile-Claim. CI muss die gepinnte Bicep-Kompilierung
vor Merge erfolgreich ausführen.

## Abnahme

```bash
python3 -m unittest tests.test_immutable_evidence tests.test_azure_blob_worm tests.test_azure_blob_worm_contract
python3 scripts/validate_business_case_type_azure_blob_worm.py
python3 scripts/validate_spec_traceability.py
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
git diff --check
```
