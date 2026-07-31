# Umsetzungsplan für die asynchrone Azure-BFF-Baseline-Reconciliation

Führendes Issue: [#719](https://github.com/notariat8/NaC/issues/719)
Spec: [M365 Azure-BFF-Reconciliation einer asynchron fertiggestellten Baseline](../specs/2026-07-31-m365-azure-bff-async-baseline-reconciliation-design.md)
Akzeptanz: `AC-719-01` bis `AC-719-06`

1. Issue #719, DE-/EN-Specs, DE-/EN-Pläne, CLI-Dokumentation und
   `AC-719-01` bis `AC-719-06` miteinander binden.
2. Den bestehenden `RESOURCE_GROUP_ONLY`-Pfad unverändert als fail-closed
   Legacy-#717-Klassifikation für exakt leeres Ressourceninventar erhalten.
3. Prepared-Manifest, Bicep-/ARM-Template und Parameter-Snapshot sicher lesen
   und ihre Aktivierungs-, Commit-, Tree- und Byte-Hashes gegeneinander
   prüfen, den genehmigten Git-Tree direkt inspizieren und Tree-Manifest sowie
   Bicep-Blob gegen die vorbereiteten Bytes verifizieren, Replace-Refs
   deaktivieren und jedes Archiv-Blob gegen seine Git-Blob-ID prüfen; daraus die kanonische
   Baseline-Erwartung und ihren SHA-256 ableiten.
4. `BICEP_BASELINE_EXACT` ausschließlich bei exakt sieben erwarteten
   Top-Level-Ressourcen mit vollständiger ID-, Typ-, Kind-, SKU-, Namens-,
   Regions-, Tag-, Smart-Detection-, Output- und Managed-Identity-Bindung
   zulassen.
5. Deploymentname, `Succeeded`, `Incremental`, Template- und Parameterhash
   sowie exakt zwölf erfolgreiche ARM-Deployment-Operationen mit der
   erwarteten Typverteilung und exakten Ziel-ARM-IDs prüfen; alle zwölf
   Zielressourcen zusätzlich read-only auf ihre als exakte Objekte gebundenen
   Bicep-Properties prüfen und über einen exakt gebundenen Azure-Resource-Graph-
   POST die vollständige Ressourcen- und Authorization-Ressourcenmenge im
   Ziel-Scope gegen Inventar plus Deployment-Ziele abgleichen.
6. Teilinventar, Zusatzressourcen, ungültige vorbereitete Inputs und jede
   Ressourcen-, Identity-, Deployment-, Operations- oder Snapshot-Drift mit
   stabilen fail-closed Fehlercodes abweisen.
7. Jeden vollständigen Provider-Snapshot read-only zweimal erheben, das
   Inventar zusätzlich innerhalb jedes Snapshots doppelt lesen und nur
   bytegleiche kanonische Beobachtungen akzeptieren.
8. Die Inspection ohne lokale Mutation und ohne Azure-/Tenant-Write auf
   `MIDRUN_RECONCILIATION_REQUIRED`, redigierte Hashes und den kanonischen
   #719-Owner-Kommentar begrenzen.
9. Die #719-Terminalisierung an
   `BICEP_BASELINE_EXACT`, `baseline_expectation_sha256`,
   `prepared_inputs_manifest_sha256`, `bicep_snapshot_sha256` und
   `bicep_parameters_snapshot_sha256` sowie alle bisherigen State-, Ledger-,
   Lock-, Provider- und Reconciler-Hashes binden.
10. Nur `TERMINALIZE_AND_RELEASE_LOCK_ONLY` zulassen, Schritt 2 als
    `EXTERNAL_PROCESS_INTERRUPTED_AFTER_WRITE` beenden, den Lauf auf
    `FAILED_PARTIAL` setzen und alle drei Lock-Journale append-only freigeben.
11. Resume, Provider-Write, Retry, Rollback, Delete und nachträgliches
    `PASSED` ausdrücklich ausschließen; gerissene lokale Terminalisierung nur
    mit identischer immutable #719-Bindung fortsetzen; unmittelbar vor der
   ersten lokalen Mutation die vollständige Providerbeobachtung erneut lesen
   und gegen den owner-gebundenen Hash prüfen; die drei Journalbytes vor jeder
   Mutation und in Recovery gegen ursprüngliche bzw. deterministisch
   abgeleitete Release-Hashes verifizieren; partielle Journal-Appends nur als
   striktes Präfix des erwarteten Release-Records nach vollständiger Runtime-,
   State-, Pfad- und Descriptor-Revalidierung reparieren; Commit, Tree und
   Laufzeitdateien zusätzlich mit deaktivierten Replace-Refs an die genehmigten
   Git-Blob-Digests binden.
12. Fokussierte Tests, Contract-Validator, Spec-Traceability-, Sprach-, Link-
    und Strict-Gates ausführen, die vollständige `base...head`-Diff
    unabhängig prüfen, P1/P2-Befunde beheben und per Protected PR liefern.
