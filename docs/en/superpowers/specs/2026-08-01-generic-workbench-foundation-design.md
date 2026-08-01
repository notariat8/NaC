# Generic Workbench Foundation

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: generic-workbench-foundation
leading_issue: https://github.com/notariat8/NaC/issues/721
risk_gate: Privacy
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-08-01-generic-workbench-foundation.md
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

## Goal

Project Atlas-like UX principles become a generic, quiet workspace without
moving NaC authority, role or evidence boundaries into the browser. The slice
is entirely offline and changes neither tenant nor live BFF contract.

## Acceptance Criteria

- **AC-721-01:** `workbench/core` imports no host, React, Graph, MCP, BPMN or NaC runtime.
- **AC-721-02:** The NaC adapter accepts only the exact producer, workspace, matter and purpose.
- **AC-721-03:** The Python producer serializes compact insertion-order JSON; producer and TypeScript runtime enforce the same 128 KiB limit on those exact UTF-8 wire bytes, count text identically in at most 256 UTF-16 code units, bound lease and collections, and reject token shapes in every external ID and display text.
- **AC-721-04:** Attention, decisions, evidence and capabilities remain server-authored 1:1; no browser derivation from tasks.
- **AC-721-05:** `assigned` and reason-bound time-limited `deputy` are allowed; `deny` produces no snapshot.
- **AC-721-06:** BPMN remains a non-authoritative model reference and every mutating capability remains `deny`.
- **AC-721-07:** The responsive React view shows Today, Matter, Decision Center and Assistance using synthetic data only.
- **AC-721-08:** Import DAG, read-only, contract, BFF, UI and visual checks plus the strict gate pass; CI transfers compiled Workbench artifacts into the gate for mandatory byte verification.

## Scope

Scope includes the core contract, parser, NaC scope adapter, React shell,
synthetic preview, BFF projection composition, CLI/validator edge, DE/EN
documentation and visual evidence. Existing SPFx packaging, App Catalog,
Entra, Graph and live BFF configuration remain unchanged.

## Security Model

Snapshots are valid for at most five minutes. Deputy expiry cannot exceed
snapshot expiry. `Today` is limited to the currently authorized matter. Every
snapshot requires a verified redaction attestation bound to the canonical
projected content. Source references are opaque identifiers; known URL, email,
token and secret shapes are rejected at both the BFF and browser boundaries. No
action URLs, callback handlers, browser persistence, Graph/MCP clients or
mutating UI actions exist.

## Visual Evidence

- Desktop: [VIS-721-01](../../../../assets/docs/generic-workbench/VIS-721-01-desktop.png)
- Mobile: [VIS-721-02](../../../../assets/docs/generic-workbench/VIS-721-02-mobile.png)
- Hash manifest: [VIS-721](../../../../assets/docs/generic-workbench/VIS-721-manifest.json)
