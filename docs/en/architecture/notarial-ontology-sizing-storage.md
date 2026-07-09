# Notarial Ontology Sizing and Storage Boundary

This decision note fixes the boundary between the business-case inventory,
ontology projection and operative Microsoft 365 storage.

## Decision

NaC uses SharePoint as the operative MVP data store for the M365 MVP. The
ontology is not a runtime store and not a central knowledge-graph folder. It
is a versioned projection and verification contract over the usecase-local
knowledge graphs.

The machine-readable contract lives at
[workflows/contracts/notarial-ontology-sizing-storage.contract.json](../../../workflows/contracts/notarial-ontology-sizing-storage.contract.json)
and is checked with `nac kg ontology-storage-contract --format json` against
the current business-case inventory.

## Why There Is No Central Knowledge Graph

The subject-matter source stays local to each usecase:

- [usecases/](../../../usecases) contains the notarial case types.
- Each case type owns its own `knowledge-graph.graph.json`.
- A central `knowledge-graph/` folder is not allowed.

The business-case inventory counts and classifies all existing cases for
sizing and routing. It does not replace the usecase-local graphs.

## Storage Roles

| Layer | Role |
| --- | --- |
| SharePoint | operative MVP data store for matter metadata, tasks, document pointers, deputy grants and redacted audit events |
| Ontology | versioned catalog and projection contract for types, field mappings, allowed relationships and sizing |
| BPMN | process model and review surface, not workflow engine |
| MCP/Graph | runtime access layer through Microsoft Graph REST v1.0 |

The ontology stores no matter instance values, no document full text, no raw
SharePoint items, no raw Graph responses and no secrets.

## Performance Boundaries

All business cases are counted for sizing. Deep process modeling remains
selective because large ontologies can otherwise grow uncontrollably on the
runtime path.

The contract therefore sets hard boundaries:

- no global OWL/graph reasoning requirement on the user request path
- no bulk mirroring of Office or SharePoint content into agent memory
- no document full text in ontology or Git
- no matter instance values in the repository ontology
- Microsoft Graph REST v1.0 only, no legacy SharePoint APIs and no SDK
  dependency
- architecture review when business-case count or complexity score exceeds
  the configured thresholds

## Validation

The validator
[scripts/validate_notarial_ontology_storage_contract.py](../../../scripts/validate_notarial_ontology_storage_contract.py)
checks:

- contract structure and schema version
- SharePoint as the operative MVP store
- ontology as a versioned projection contract
- Graph REST-only boundary
- sizing against the current business-case inventory
- central KG storage and sensitive payloads remain blocked

The check is part of the strict quality gate as
`notarial_ontology_storage_contract`.
