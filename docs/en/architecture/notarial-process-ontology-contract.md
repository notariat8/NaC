# Notarial Process Ontology Contract

This decision note fixes the product-model contract for the M365/SharePoint MVP.

The machine-readable contract lives in
[workflows/contracts/notarial-process-ontology.contract.json](../../../workflows/contracts/notarial-process-ontology.contract.json)
and is checked with `nac kg process-ontology-contract --format json`.

## Purpose

The contract is the product boundary between the business-case inventory, BPMN
process model, ontology projection, SharePoint storage and agent runtime. It no
longer only asks whether SharePoint works technically; it defines the canonical
product objects NaC knows for notarial workflows:

- business-case types
- matters and status
- participants, roles and role bindings
- process phases, tasks, deadlines, gates and decisions
- document types, document pointers and versions
- evidence pointers and audit events
- time-boxed deputy grants
- BPMN model pointers

## Decisions

- SharePoint remains the operative MVP data store for metadata, tasks,
  document pointers, deputy grants and redacted audit events.
- The ontology is a versioned product-model and projection contract, not a
  runtime store and not a global reasoner on the request path.
- All business cases from the inventory are counted for sizing and the case
  index; deep BPMN/ontology modeling may still remain selective.
- Microsoft 365 stays connected through Microsoft Graph REST v1.0. SDKs,
  legacy SharePoint APIs and Graph beta remain blocked for this boundary.
- `Prozessregister` and `BPMN Models` are optional later SharePoint projections
  and require an owner-gated schema action before live use.

## Boundaries

This slice is offline-only:

- no Microsoft Graph requests
- no SharePoint writes
- no SharePoint schema changes
- no matter values in the repo
- no document full text
- no secrets
- no central knowledge-graph folder
- no productive BPMN modeler or workflow-engine apply

The validator
[scripts/validate_notarial_process_ontology_contract.py](../../../scripts/validate_notarial_process_ontology_contract.py)
checks these boundaries in the strict quality gate as
`notarial_process_ontology_contract`.
