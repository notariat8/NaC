# Workflow Contracts

This folder is reserved for workflow contracts. A contract describes the
boundary between a notarial usecase, one or more plugins, and deterministic
workflow execution.

Each contract should define:

- input schema
- output schema
- required roles
- required approvals
- required plugin gates
- data class
- evidence record shape

## Implemented Contracts

- [workflows/contracts/kg-editor.contract.json](kg-editor.contract.json): KG
  editor contract for rendering usecase-local
  [knowledge-graph.graph.json](../../usecases/immobilienkaufvertrag/knowledge-graph.graph.json)
  files as safe forms, checklists and patch proposals without exposing `value`
  fields to Fachpersonal.
