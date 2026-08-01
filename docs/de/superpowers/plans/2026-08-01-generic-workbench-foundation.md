# Umsetzungsplan: Generic Workbench Foundation

Status: `IMPLEMENTED_OFFLINE`

Datum: 1. August 2026

Führendes Issue: [#721](https://github.com/notariat8/NaC/issues/721)

Design: [Generic Workbench Foundation](../specs/2026-08-01-generic-workbench-foundation-design.md)

## Arbeitspakete

1. `core`, `nac` und `react` als gerichtete Importgrenzen im bestehenden SPFx-Paket anlegen.
2. Exakten kurzlebigen Snapshot-Parser mit kompaktem JSON-Serializer, gemeinsamem 128-KiB-Wire-Limit, gemeinsamer 256-UTF-16-Codeeinheiten-Textgrenze sowie ID-, Token-, Referenz- und Lease-Prüfung implementieren.
3. NaC-BFF-Projektionskomposition ohne fachliche Ableitung, mit inhaltsgebundener Redaktionsattestierung und deny-only Capabilities ergänzen.
4. Today-, Matter- und Decision-Center-Ansicht mit synthetischer Vorschau implementieren.
5. Vertrags-, Import-DAG-, Read-only-, UI-, BFF- und Visual-Tests sowie zwingende CI-Prüfung der kompilierten Evidence-Artefakte ergänzen.
6. DE/EN-Dokumentation, Agent-Context-Routing und zentrale `nac frontend workbench-verify`-Kante ergänzen.
7. Unabhängigen Review, Strict Gate, geschützten PR und grüne Remote-CI abschließen.

## Nicht ausgeführt

Kein Tenant-Write, kein App-Catalog-Deploy, keine Graph-/MCP-Browserkante,
keine neue Berechtigung und keine Änderung des bestehenden Live-BFF-Endpunkts.
