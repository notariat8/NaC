# Notarial Ontology Scale Budget

This decision note describes the offline smoke for ontology sizing across all
known notarial business cases.

## Purpose

`nac kg ontology-scale-budget --format json` checks whether the current
SharePoint/ontology boundary still holds when sizing considers the full
business-case inventory, not only two or three cases.

The smoke counts and evaluates:

- all business cases from the thin inventory
- existing BPMN sources and BPMN flow nodes
- estimated ontology projection nodes per case
- estimated ontology projection edges per case
- runtime boundaries for Graph reads and SharePoint lists per user action

## Decision

SharePoint remains the operative MVP data store. The ontology remains a
versioned projection and sizing contract in the repository, not the productive
runtime database.

The smoke allows deep BPMN/ontology modeling only as a selective follow-up. It
does not prevent all business cases from being included in sizing.

## Boundaries

The scale smoke is offline-only:

- no Microsoft Graph requests
- no SharePoint writes
- no SharePoint schema changes
- no document-content reads
- no matter values in Git or ontology
- no secrets
- no central `knowledge-graph/` folder
- no runtime ontology reasoning on the user request path

The validator
[scripts/validate_notarial_ontology_scale_budget.py](../../../scripts/validate_notarial_ontology_scale_budget.py)
checks these boundaries in the strict quality gate.
