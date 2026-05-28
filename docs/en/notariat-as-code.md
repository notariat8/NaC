# Subject Concept: Notariat As Code With NaC

## Guiding Principle

NaC treats notarial case types as versioned, checkable and approval-bound
flows. The subject-matter truth is not a chat transcript or a user interface;
it is a traceable state made of usecase, knowledge graph, BPMN model, policy,
review and approval.

A matter becomes binding only when it:

1. exists as a structured request or usecase state,
2. passes subject-matter validation,
3. has completed the required notary-office approvals,
4. has reached the binding state through the applicable delivery mode, either
   protected PR or explicitly approved owner-direct delivery.

## Positioning

- `Notariat as Code` describes the target model.
- `Enterprise GitOps` describes the operational change flow.
- `NaC` is the concrete implementation in this repository.

NaC is only for notary offices. Non-notarial examples are outside product
scope.

Reference: [organization-as-code-positioning.md](organization-as-code-positioning.md)

## Role Model

- `requester`: starts a matter or change proposal.
- `notariatsfachkraft`: maintains matter data, open information and evidence.
- `notar_fachlich`: makes subject-matter notarial decisions.
- `kostenverantwortung`: reviews cost and fee questions where qualified.
- `reviewer`: reviews policy, privacy, technology or QMS impact.
- `auditor`: checks history, evidence, status and closures.
- `automation`: GitHub Actions and the local Python runtime execute
  deterministic checks.

Details: [role-model.md](role-model.md) and
[policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)

## Canonical Usecases

Product examples live only in the [usecase catalog](../../usecases/README.md).
Typical entry points are:

- [real-estate purchase contract](../../usecases/immobilienkaufvertrag)
- [signature certification](../../usecases/unterschriftsbeglaubigung)
- [online GmbH formation](../../usecases/online-gmbh-gruendung)
- [commercial-register filing](../../usecases/handelsregisteranmeldung)
- [testament / inheritance contract](../../usecases/testament-erbvertrag)

Each usecase has a subject-matter front page, a machine-readable
`knowledge-graph.graph.json`, a review view as `knowledge-graph.md` and a BPMN
model where the process state has been modeled.

## Data Principles

- The LLM may structure inputs, but must not replace notarial decision-making.
- Deterministic Python logic checks status, contracts and artifacts.
- Personal data, register extracts, signature secrets, PINs and real matter
  documents stay outside this public repository.
- Every effective matter needs traceable approvals and evidence.
- Idempotency keys prevent duplicate execution of technical steps.

## Git As Control Layer

- A branch or pull request represents work on a matter, rule or usecase.
- Reviews represent human approval.
- Merge into `main` represents binding adoption; production forks use merges,
  while the active reference repository may use owner-direct delivery when
  explicitly requested.
- Tags and releases represent reviewed states.
- Artifacts represent exported evidence.

## Notarial Core And Usecase Layer

The process world is organized in two layers:

- `notariat_core`: rules, roles, approvals, privacy, versioning, QMS relation
  and shared gates.
- `usecase`: case-type-specific open information, documents, decisions, gates
  and evidence.

Details are in
[service-model/notariat-scope-blueprint.md](service-model/notariat-scope-blueprint.md)
and [service-model/notarial-usecase-starter.md](service-model/notarial-usecase-starter.md).

## Variant Capability Instead Of One Standard Process

Notary offices can maintain local variants in private forks as long as they
remain versioned, approved and auditable:

- which variant applies,
- which location or usecase it applies to,
- from when it applies,
- who approved it.

For mixed operation:

- the version is bound when each matter starts,
- running matters remain on their bound version,
- new releases apply only to newly started matters.

Details: [operations/parallelbetrieb-version-binding.md](operations/parallelbetrieb-version-binding.md)

## Model Boundaries

- NaC does not replace a required specialist system.
- NaC does not replace notarial responsibility or legal review.
- Git is not a file or document safe for real matter content.
- Write-capable specialist-system, portal or register adapters require separate
  approval, privacy review and operating evidence.
