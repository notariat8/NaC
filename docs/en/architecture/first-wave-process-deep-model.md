# First-Wave Process Deep Model

This decision note describes the first deeper, but still mandate-data-free,
process model contract for the four first-wave cases.

## Purpose

`nac kg first-wave-process-deep-model --format json` compresses the existing
offline artifacts into a usable process-model shape:

- eight canonical process phases per first-wave case
- canonical role bindings including deputy roles
- existing BPMN sources as non-executing process model bindings
- usecase-local KG nodes for required information, document types, decisions,
  gates and evidence
- SharePoint projection plan for the MVP lists and libraries
- known SharePoint, BPMN and ontology gaps as an owner-gated gap-closure plan

The next subject-matter step is therefore no longer only an outline. It is a
concrete, verifiable contract for later process instances.

## Boundaries

The contract remains offline-only:

- no Microsoft Graph requests
- no SharePoint writes
- no SharePoint schema changes
- no mutation of existing BPMN files
- no document contents
- no matter values
- no secrets
- no central knowledge-graph folder

SharePoint remains the operative MVP store. The ontology remains a product
model, sizing and projection contract, not a runtime database and not a
reasoning path for user actions.

## Follow-Up

The useful follow-up is a `first_wave_process_instance_seed_plan`: the deep
model can drive synthetic process-instance templates. A real SharePoint write
or BPMN model mutation still requires an explicit owner gate afterwards.

The validator
[scripts/validate_first_wave_process_deep_model.py](../../../scripts/validate_first_wave_process_deep_model.py)
checks these boundaries in the strict quality gate.
