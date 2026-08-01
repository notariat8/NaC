# Generic Workbench Foundation

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: generic-workbench-foundation
leading_issue: https://github.com/notariat8/NaC/issues/721
risk_gate: Privacy
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-08-01-generic-workbench-foundation.md
review_gates:
  - Privacy
  - Workflow
  - Policy
acceptance_ids:
  - AC-721-01
  - AC-721-02
  - AC-721-03
  - AC-721-04
  - AC-721-05
  - AC-721-06
  - AC-721-07
  - AC-721-08
validation_commands:
  - python3 scripts/validate_generic_workbench_foundation.py
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_workbench_projection
  - cd spfx/nac-bpmn-viewer && npm run build
  - cd spfx/nac-bpmn-viewer && npm run workbench:capture
  - python3 scripts/nac.py frontend workbench-verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
```

## Ziel

Project-Atlas-artige UX-Prinzipien werden als generische, ruhige
Arbeitsoberfläche umgesetzt, ohne die NaC-Autoritäts-, Rollen- und
Nachweisgrenzen in den Browser zu verschieben. Der Slice ist vollständig
offline und verändert weder Tenant noch Live-BFF-Vertrag.

## Akzeptanzkriterien

- **AC-721-01:** `workbench/core` importiert keine Host-, React-, Graph-, MCP-, BPMN- oder NaC-Runtime.
- **AC-721-02:** Der NaC-Adapter akzeptiert nur exakten Producer, Workspace, Akte und Zweck.
- **AC-721-03:** Der Python-Producer serialisiert kompakt in Einfügereihenfolge; Producer und TypeScript-Runtime begrenzen exakt diese UTF-8-Wire-Bytes identisch auf 128 KiB, zählen Text identisch in höchstens 256 UTF-16-Codeeinheiten, begrenzen Lease und Sammlungen und verwerfen Tokenmuster in allen externen IDs und Anzeigetexten.
- **AC-721-04:** Aufmerksamkeit, Entscheidungen, Nachweise und Capabilities bleiben 1:1 serverseitig; keine Browserableitung aus Aufgaben.
- **AC-721-05:** `assigned` und begründetes, befristetes `deputy` sind erlaubt; `deny` erzeugt keinen Snapshot.
- **AC-721-06:** BPMN bleibt eine nicht-autoritative Modellreferenz und alle mutierenden Capabilities bleiben `deny`.
- **AC-721-07:** Die responsive React-Ansicht zeigt Today, Akte, Decision Center und Assistenz ausschließlich mit synthetischen Daten.
- **AC-721-08:** Import-DAG-, Read-only-, Contract-, BFF-, UI- und Visual-Prüfungen sowie Strict Gate bestehen; die CI übergibt die kompilierten Workbench-Artefakte zur zwingenden Byteprüfung an das Gate.

## Scope

Im Scope liegen Core-Vertrag, Parser, NaC-Scope-Adapter, React-Shell,
synthetische Vorschau, BFF-Projektionskomposition, CLI-/Validator-Kante,
DE/EN-Dokumentation und visuelle Evidence. Bestehende SPFx-Paket-,
App-Catalog-, Entra-, Graph- und BFF-Live-Konfigurationen bleiben unverändert.

## Sicherheitsmodell

Snapshots sind maximal fünf Minuten gültig. Deputy-Ablauf darf den
Snapshot-Ablauf nicht überschreiten. `Today` ist auf die aktuell autorisierte
Akte begrenzt. Jeder Snapshot benötigt eine verifizierte, an den kanonischen
Projektionsinhalt gebundene Redaktionsattestierung. Quellreferenzen sind opake
Identifier; bekannte URL-, E-Mail-, Token- und Secret-Formen werden sowohl am
BFF- als auch am Browser-Rand abgelehnt. Es existieren keine Action-URLs, Callback-Handler,
Browser-Persistenz, Graph-/MCP-Clients oder mutierenden UI-Aktionen.

## Visuelle Evidence

- Desktop: [VIS-721-01](../../../../assets/docs/generic-workbench/VIS-721-01-desktop.png)
- Mobile: [VIS-721-02](../../../../assets/docs/generic-workbench/VIS-721-02-mobile.png)
- Hashmanifest: [VIS-721](../../../../assets/docs/generic-workbench/VIS-721-manifest.json)
