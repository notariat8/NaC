# BPMN-js Business Layer

Status: usecase BPMN and local save surface added on 2026-05-19

## Decision

NaC should not model the business layer as Python-code-first. The
subject-matter process source becomes BPMN 2.0. `bpmn-js` is the planned visual
editing layer because subject-matter users can see and change processes without
writing XML or Python.

Python remains essential: it validates whether the visually edited model is
allowed, complete, privacy-compliant and connectable to execution.

## Target Experience For Subject-Matter Users

1. A notary office opens a case type or process in the BPMN editor.
2. The editor exposes only allowed building blocks: task, decision, approval,
   evidence and local plugin step.
3. A properties panel shows understandable NaC fields: role, execution
   channel, data class, approval, evidence, plugin and KG reference.
4. After saving, Python validates the BPMN model.
5. Changes go through pull request, diff, quality gate and approval.

## Why Not Put Everything Into bpmn-js

`bpmn-js` is the editor, not the governance layer. It should make processes
editable, but it must not decide by itself whether a process is allowed. That
decision remains with Git, Python validators, privacy rules, review and human
approval.

## Current Repository State

- The NaC model profile lives in [bpmn/nac-moddle.json](../../bpmn/nac-moddle.json).
- The subject-matter description lives in [bpmn/nac-bpmn-profile.md](../../bpmn/nac-bpmn-profile.md).
- Every usecase under [usecases/](../../usecases) has a bpmn-js-ready BPMN
  model. The canonical real-estate purchase contract remains at
  [bpmn/immobilienkaufvertrag.bpmn](../../bpmn/immobilienkaufvertrag.bpmn);
  the other usecase models live under [bpmn/usecases/](../../bpmn/usecases).
- `nac:channel` documents how a step is executed, for example in person,
  by email, by post/fax, digitally signed, through local XNP, or through a
  register/land-register portal.
- Deterministic validation lives in
  [scripts/validate_bpmn_models.py](../../scripts/validate_bpmn_models.py).
- Generation lives in
  [scripts/generate_usecase_bpmn.py](../../scripts/generate_usecase_bpmn.py).
- The workflow contract lives in
  [workflows/contracts/bpmn-js-editor.contract.json](../../workflows/contracts/bpmn-js-editor.contract.json).
- The local browser surface for graphical outputs is documented in
  [docs/en/lokaler-webserver.md](lokaler-webserver.md).

## Subject-Matter Sources

The usecase BPMN models are a reviewable working state. They connect the
usecase-local KGs with two external BNotK anchors:

- BNotK describes XNP integration as a local `localhost` REST interface that
  involves login information, the current official activity and, for login
  functions, an API key configured per installation.
- BNotK describes online company-law proceedings with incoming cases, email
  notification, clerk/file-reference handling, edit/export/create actions and
  videoconference-related steps.

NaC therefore models XNP-adjacent steps as local, evidence-required service
tasks and online GmbH steps with `notary_app`, `video` and
`qualified_e_signature`. This does not replace notarial legal review and does
not store mandate values.

## Relationship To KG

BPMN and KG have different jobs:

| Layer | Question | Source |
| --- | --- | --- |
| BPMN | What happens when? | [bpmn/](../../bpmn) |
| KG | Which information, documents, decisions and evidence are open? | [usecases/](../../usecases) |
| Python | Is the model allowed and checkable? | [scripts/](../../scripts), [src/](../../src) |

A BPMN step can reference a usecase-local knowledge graph through `nac:kgRef`.
This keeps the flow visually editable while detailed subject-matter questions
remain controlled in the KG.

## Next Steps

1. Further restrict the bpmn-js palette and NaC properties panel.
2. Show BPMN diff and validation report in pull requests.
3. Run subject-matter review rounds per usecase against real office practice.
4. Generate safe form and checklist views from BPMN and KG together.
