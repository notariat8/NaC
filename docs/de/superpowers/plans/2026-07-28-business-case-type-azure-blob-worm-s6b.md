# BusinessCaseType Azure Blob WORM S6b Implementierungsplan

Status: `S6B_AZURE_WORM_ADAPTER_READY_OFFLINE`
Live-Status: `BLOCKED_PENDING_S7_APPROVAL`
Führendes Issue: [#693](https://github.com/notariat8/NaC/issues/693)
Spec: [BusinessCaseType Azure Blob WORM S6b Design](../specs/2026-07-28-business-case-type-azure-blob-worm-s6b-design.md)
Domain-Contract: [business-case-type-azure-blob-worm-s6b.contract.json](../../../../../workflows/contracts/business-case-type-azure-blob-worm-s6b.contract.json)
Lock-Contract: [azure-blob-worm-irreversible-lock-s6b.contract.json](../../../../../workflows/contracts/azure-blob-worm-irreversible-lock-s6b.contract.json)

## Plan -> Review -> Fix

1. **Tests first:** Pre-Put-Timestamp-/Retention-/Overflow-Negative,
   Future-S6a-Timestamp, Response-Loss, echte Same-Blob-Concurrency, frischen
   Provider-Readback und 201/412-Version-Discovery festhalten.
2. **AC-S6B-01:** unveränderte `WormJournalPort`-Signaturen und vollständigen
   kanonischen Readback erhalten.
3. **AC-S6B-02:** nur den S6a-`worm-commit`-Schlüssel akzeptieren; HTTP `201`
   an rohe `version_id` aus `x-ms-version-id` binden; bei `412` List Blob Versions und GET mit
   roher `versionid` nutzen. Keine Hash-Selektoren im Transport-Port.
4. **AC-S6B-03:** alle fehlschlagenden Berechnungen vor Put ausführen und im
   Fake `retention_until` ab `created_at` modellieren. Exakte Version muss
   `Locked`, mindestens `3653` Tage, Legal-Hold-Fähigkeit und CMK belegen.
5. **AC-S6B-04:** frische Tenant-, Subscription- und Storage-Resource-Readbacks
   domain-separiert hashen; stale Metadata und Tenant-Transfer redigiert
   blockieren. Quellen sind `subscription().tenantId`, `subscription().id`
   und `resourceId('Microsoft.Storage/storageAccounts', storageAccountName)`.
6. **AC-S6B-05:** dedizierte Bicep-Baseline mit Blob `add/action` plus `read`
   und getrennten Management-Reads für Container, Immutability Policy und
   Encryption Scope erstellen. Kein Blob-`write`, Delete, Owner, Contributor
   oder Broadening bestehender Identitäten.
7. **AC-S6B-06:** Netzwerk, Azure, Credentials, Tenant-Writes, Live-Lock und
   Live-Factory bleiben null; S7 bleibt `BLOCKED_PENDING_S7_APPROVAL`.
8. **AC-S6B-07:** Domain-/Verification-/Lock-Contract, DE/EN-Dokumente,
   Validator und fokussierte Tests angleichen. Der reine Lock-Plan bindet
   Target, Provider-Kontext, Policy, ETag, Request-Hash, Operator/Approver und
   Pre-/Post-Readback, führt aber nichts live aus.
9. **Review:** None-/Ambiguous-/Foreign-Version, malformed `201`/`412`,
   Overflow vor Put, Provider-Transfer, RBAC-Negative, Redaction und
   Target-/ETag-/Request-Hash-Drift unabhängig prüfen.
10. **Fix und Abnahme:** fokussierte Tests, Validator, Spec-Traceability,
    Parität, Links und Diff-Check wiederholen.

## Integrations- und Compile-Schritt

Track B ändert oder revertiert keine zentralen Index-, Architektur-, CLI- oder
Quality-Gate-Dateien. Die vorhandene zentrale Adoption bleibt erhalten. Vor
Merge bleibt die gepinnte Bicep-CI-Kompilierung verpflichtend:

```bash
az bicep build --file deploy/runtime/azure/immutable-evidence/main.bicep --stdout
```

Lokal sind `az bicep`, `bicep` und `npx bicep` nicht verfügbar. Daher wird kein
lokaler Compile-Erfolg behauptet.

## Irreversibler Lock

S6b führt keinen Lock aus. Ein späterer Owner-gated S7-Schritt muss den exakten
Target-/Provider-Kontext und die Policy frisch lesen, `Unlocked`, mindestens
`3653` Tage und ETag prüfen, den kanonischen Request-Hash freigeben und nach
der Operation denselben Kontext mit neuem ETag und `Locked` zurücklesen. Jede
Target-, ETag- oder Request-Hash-Abweichung blockiert.

## Fokussierte Validierung

```bash
python3 -m unittest tests.test_immutable_evidence tests.test_azure_blob_worm tests.test_azure_blob_worm_contract
python3 scripts/validate_business_case_type_azure_blob_worm.py
python3 scripts/validate_spec_traceability.py
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
git diff --check
```
