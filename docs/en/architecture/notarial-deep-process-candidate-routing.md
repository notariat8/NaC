# Deep-Process Candidate Routing

This routing derives from the business-case inventory and the ontology
sizing/storage contract which case types should be modeled deeply in BPMN and
ontology projection next.

## Decision

All existing business cases are counted for sizing. Deep modeling is not forced
for every case at once. The routing instead creates lanes:

| Lane | Meaning |
| --- | --- |
| `first_wave_deep_process` | immediate candidate for BPMN outline, ontology projection plan and verification contract |
| `archetype_review` | representative case, compare against first-wave archetypes first |
| `candidate_backlog` | subject-matter candidate, batch by domain |
| `legacy_alias_dedupe` | historical alias, map to canonical slug before deep modeling |
| `thin_catalog_only` | keep only in the thin catalog for now |

The machine-readable evidence comes from
`nac kg deep-process-candidates --format json`.

## Boundaries

The routing is offline-only:

- no Microsoft Graph requests
- no SharePoint writes
- no SharePoint schema change
- no document-content reads
- no matter values in Git or ontology
- no runtime reasoning requirement on the user path

SharePoint remains the operative M365 MVP data store. The ontology remains a
versioned projection contract over the usecase-local knowledge graphs. BPMN
remains a process model and review surface, not a workflow engine.

## Validation

The validator
[scripts/validate_notarial_deep_process_candidate_routing.py](../../../scripts/validate_notarial_deep_process_candidate_routing.py)
checks that high/medium complexity cases are recognized as candidates,
first-wave cases remain bounded and legacy aliases are deduplicated first.
The check runs in the strict quality gate as
`notarial_deep_process_candidate_routing`.
