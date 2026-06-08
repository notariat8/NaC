# KG Editor Workstream

Status: MVP implemented on 2026-05-15

The KG editor is the subject-matter editing layer above the usecase-local static
knowledge graphs. The files
[usecases/*/knowledge-graph.graph.json](../../usecases) remain the
machine-readable representation. Notarial staff should not edit those JSON files
directly.

## Product Decision

For notarial case types, the editor does not introduce real mandate data into
Git. `value` fields stay empty and are blocked in the editor view. The editor
instead exposes status, roles, open information, documents, decisions, gates and
evidence metadata.

The smallest useful end-user flow is:

1. ChatGPT or another LLM receives the natural-language instruction.
2. The runtime reads the matching KG through [src/notary_kg/editor.py](../../src/notary_kg/editor.py).
3. Staff see four tabs: Open Information, Documents, Decisions and
   Gates/Evidence.
4. Changes are produced as structured patches according to
   [schemas/kg-editor-patch.schema.json](../../schemas/kg-editor-patch.schema.json).
5. The patch is validated, checked for privacy, shown as a diff and applied only
   after confirmation through a pull request.

## Executable Surface

The current CLI produces a safe editor view for every usecase slug:

```bash
python scripts/nac.py kg editor-view immobilienkaufvertrag
python scripts/nac.py kg --format json editor-view immobilienkaufvertrag
python scripts/nac.py kg cost-view immobilienkaufvertrag
```

This is not the final web editor yet, but it is an implemented contract for a
GitHub-backed sidecar editor or a later ChatGPT App. The workflow contract lives
in [workflows/contracts/kg-editor.contract.json](../../workflows/contracts/kg-editor.contract.json).
The GNotKG cost view has its own contract in
[workflows/contracts/gnotkg-cost-review.contract.json](../../workflows/contracts/gnotkg-cost-review.contract.json):
it produces `xyflow`-ready nodes and edges for business value, value rule,
KV item, table A/B, fee rate, expenses, review gate and draft cost note, but
does not calculate in the browser.
Why the visible editing surface needs a checkable technical core is explained in
[docs/en/ausfuehrungsmodell.md](ausfuehrungsmodell.md).

## Tabs

| Tab | KG source | Interaction model |
| --- | --- | --- |
| Open Information | `required_information` | Checklist with status, role and required context |
| Documents | `documents` | Document status with source and privacy marker |
| Decisions | `decisions` | Dropdown/options model with status |
| Gates/Evidence | `gates`, `evidence` | Review list for approvals and evidence |

Every usecase additionally contains the cost nodes `cost.business_value`,
`decision.gnotkg_cost_path`, `gate.gnotkg_cost_review` and
`evidence.gnotkg_cost_note`. This lets every workflow call the same central
cost module without duplicating cost logic per usecase.

## Guardrails

- No direct JSON editing by subject-matter staff.
- No real person, property, health, family, estate, company or secret data in the
  repository.
- No editor changes to `value` fields.
- No blind overwrites; changes go through patch, validation, diff, confirmation
  and pull request.
- Graph visualization is secondary; operationally, missing information,
  blockers, responsibilities and review gates matter more.

## KG Cleanliness For JSON Files

NaC treats the usecase-local KG not as a self-learning graph database, but as a
versioned subject-matter contract. The most important cleanliness rule is
therefore: alias, label and identity stay separate. An agent may flag similar
labels or possible duplicates, but it must not merge nodes automatically.

- Stable `id` values are the identity of a KG node; labels, questions and
  aliases may change, IDs only through an explicit migration.
- Label or alias normalization is allowed, but it is not proof that two nodes
  are the same subject-matter entity.
- Possible duplicates, similar IDs, orphan edges, unknown `source_refs` or
  missing privacy classes are handled as validator warnings or review
  candidates.
- Merges, replacements and deletions go only through patch, diff, human review
  and pull request. When a real replacement happens, provenance stays traceable
  through `deprecated`, `replaced_by` or a comparable review note.
- For NaC, an uncertain KG match is not a reason for automation; it is a review
  signal.

## Integration Path

MVP 1 is the GitHub-backed KG editor. MVP 2 is a ChatGPT App with an embedded
sidecar editor. MVP 3 is a low-code configuration layer so new usecases can be
rendered as forms, checklists and review gates without new UI code.

For later OpenAI integration, the official
[Apps SDK](https://developers.openai.com/apps-sdk/) and
[GPT Actions](https://platform.openai.com/docs/actions) are recorded as
technical integration paths. The subject-matter truth still remains Git plus
review plus approval.
