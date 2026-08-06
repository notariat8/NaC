# Umsetzungsplan: Konservative BFF-Messadapter

- Issue: [#733](https://github.com/notariat8/NaC/issues/733)
- Spec: [Konservative BFF-Messung](../specs/2026-08-03-bff-conservative-measurement-adapters-design.md)
- Vertrag: [m365-bff-performance-acceptance.contract.json](../../../../workflows/contracts/m365-bff-performance-acceptance.contract.json)
- Status: Offline-Implementierung; Live und Provisionierung gesperrt.

Die Planungsgrenze führt vier getrennte Aussagen: `tenant_wide_sharepoint_baseline_claim: NOT_CLAIMED`, `tenant_wide_sharepoint_request_allowance_claim: NOT_CLAIMED`, `tenant_wide_sharepoint_resource_unit_allowance_claim: NOT_CLAIMED` und `monetary_cost_claim: NOT_CLAIMED`.

1. Tenantweite SharePoint-Kapazitätslogik vollständig durch eine unveränderliche endpointgebundene Messpolitik mit `NOT_CLAIMED` ersetzen (`AC-733-01`).
2. Die Allokationen auf `1 + 1 + 90 + 120 + 288 = 500`, Parallelität eins und höchstens sechs Dispatches pro Minute festlegen (`AC-733-02`).
3. Einen read-only Monitor-Adapter mit fester Resource-ID, API, Metrik-, dimensionslosem app-weitem Rollup, Aggregations-, Settlement- und Fenster-Allowlist implementieren (`AC-733-03`).
4. Einen lokalen BFF-Broker-Client und eine serverseitige, UAMI-gebundene Azure-Blob-State-Machine mit Acquire, Assert und Release implementieren; der lokale Runner erhält weder Storage-Token noch Lease-ID (`AC-733-04`).
5. Acquire-/Release-Crashpunkte, Same-ID-Resume und `PASSED` erst nach einem exakten, an `target_binding_sha256` und Lease-Bindung gebundenen `RELEASED`-Receipt testen (`AC-733-06`).
6. Messpolitik, Monitor, Broker-Lease, App-Rolle `Performance.Lease`, Function-Settings, Function-System-Identity, RBAC/ABAC, Infrastrukturplan und -parameter, Commit, Tree und Toolchain in genau einem kombinierten Owner-Gate hashbinden; konkrete Lease- und Broker-Bindung per Readback nachweisen (`AC-733-05`, `AC-733-08`).
7. Ein finales gesetztes Monitorfenster binden, dessen `monitor_window_end_utc` nach dem settlement `measurement_finished_at_utc` abdeckt; `projected_remaining_execution_units_gb_seconds` bei jeder Safety-Beobachtung persistieren und im erfolgreichen terminalen Messnachweis exakt null verlangen (`AC-733-03`, `AC-733-07`).
8. Jedes terminale Ergebnis über einen dauerhaften `pending-finalization`-Datensatz, Same-ID-Release-Reconciliation, exakten Release-Nachweis und ein zuletzt geschriebenes `Completion-Manifest` für crash-sichere JSON-/Markdown-Persistenz finalisieren.
9. CLI-/Composition-Negativtests sichern, dass Offline keine Adapter instanziiert, nur die exakte Monitor-URL als Read-Command zulässig ist, die TOCTOU-Neumessung unmittelbar vor jedem Subprozess erfolgt und alle Gates vor Provider-/BFF-Zugriff liegen.
10. Contract, Contract-Index, Verification Contract, Validator, DE/EN-Dokumentation und CLI synchronisieren.
11. Unit-, Command-Boundary-, Composition-, Crash- und RBAC-Negativtests, Strict-Gate und unabhängige Reviews ausführen; Befunde beheben und den geschützten PR liefern (`AC-733-07`).
12. Vor Provisionierung die bestehenden BFF-/WORM-`Resource-ID`-Werte autoritativ binden und Azure-Namensverfügbarkeit prüfen; danach vollständige effektive RBAC-/ABAC-Vererbung einschließlich Tenant-Root, Management Groups und transitiver Entra-Gruppen als `SAFE`-Evidence nachweisen. Die mit Bicep `0.45.15.27210` kompilierten ARM-/Parameter-Artefakte in CI bytegenau reproduzieren.
13. Nach grünem Merge genau eine hashgebundene Freigabe für Provisionierung, read-only Readback und vollständige Live-Abnahme erzeugen.

Keine Planstufe legt Azure-Ressourcen an oder führt einen Live-Test aus.
