# Umsetzungsplan: Workbench Live-Read-Bindung

Status: `PLANNED`

Datum: 1. August 2026

Führendes Issue: [#725](https://github.com/notariat8/NaC/issues/725)

Design: [Workbench Live-Read-Bindung](../specs/2026-08-01-workbench-live-read-binding-design.md)

## Arbeitspakete

1. Dedizierten Live-Binding-Vertrag und Verification Contract mit normativer Hash-/Wire-Fixture, AC-Testmatrix, Synthetic-Allowlist sowie Deny-/Cache-Semantik definieren.
2. Rich-Access-Entscheidung ergänzen und Assigned-/Deputy-/Deny-Verhalten ohne Änderung des bestehenden v0.2-DTO testen.
3. Workbench-Orchestrator und rekursiven Redaktionsprüfer mit exakter Wire-Serialisierung, Pre-Graph-Allowlist und fail-closed Fehlerabbildung implementieren.
4. FastAPI-Route und Azure-Composition additiv anbinden; alte Route unverändert halten und `no-store` für alle Antwortpfade testen.
5. Strikten SPFx-Workbench-Client und Refresh-Host mit sofortiger Datenverwerfung, monotone Generation und Race-/Unmount-Tests implementieren.
6. Workbench als primäre Ansicht und BPMN-Cockpit als Detailansicht im bestehenden Webpart integrieren.
7. Validatoren, DE/EN-Dokumentation und Agent-Context-Routing aktualisieren.
8. Fokussierte Tests, Build, Desktop-/Mobile-Evidence, unabhängigen Implementierungsreview und Strict Gate ausführen.
9. Vollständige `main...head`-Diff prüfen, geschützten PR erstellen und Remote-CI bis grün bearbeiten.
10. Deployment-Readiness gegen vorhandene App-Catalog-/Teams-/BFF-Automation prüfen; kein Live-Deploy aus ungeprüftem Branch.

## Parallelisierung

Nach Festschreibung des gemeinsamen Vertrags werden Server und SPFx-Host in getrennten Dateibereichen
implementiert. Contract-/Security-Review und visuelle Prüfung laufen parallel zu
den fokussierten Testschleifen. Subagents erhalten ausschließlich isolierten,
pfadbezogenen Kontext.
