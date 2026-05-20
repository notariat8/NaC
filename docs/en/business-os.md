# Subject Concept: Notariat As Code With NaC

## Guiding Principle

Git is treated as a versioned operating system for business processes. The
subject-matter truth is not the user interface, but the traceable state change.
A matter becomes effective only when it:

1. exists as a structured request,
2. passes subject-matter validation,
3. has completed the required approvals,
4. has been merged into the binding main state.

## Positioning

- `Notariat as Code` describes the overarching target model.
- `Enterprise GitOps` describes the operational change flow.
- `NaC` is the concrete operating implementation in this repository.

Reference: [docs/en/organization-as-code-positioning.md](organization-as-code-positioning.md)

## Role Model

- `requester`: starts a matter through a prompt.
- `operator`: maintains templates, schemas and rule sets.
- `reviewer`: performs subject-matter review for sensitive matters.
- `approver`: decides on payment, outgoing invoices or tax filing.
- `auditor`: checks history, evidence, status and closures.
- `automation`: GitHub Actions and the Python engine execute deterministic
  steps.

Extension for operational use:

- Every role may create tickets (`everyone_can_open_ticket=true`).
- Self-resolution is allowed only within the approved competence.
- Subject-critical steps go through review or approval depending on impact and
  compliance.
- Domain-specific cases can require qualifications, for example RVG billing.

Details: [docs/en/role-model.md](role-model.md) and
[policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)

## Process Domains

### Formation

Formation is handled as a sequence of controlled checkpoints:

- define legal form,
- create formation documents,
- prepare register and tax filing,
- set up bank account, roles and powers of attorney,
- create ongoing compliance deadlines.

Typical states:

- `draft`
- `validated`
- `needs_review`
- `approved`
- `executed`
- `archived`

### Invoicing

Invoices are modeled as versioned matter objects. The engine assigns or
validates number ranges, checks required fields and creates exportable
artifacts.

Typical states:

- `draft`
- `approved`
- `issued`
- `paid`
- `cancelled`

### Bookkeeping

Bookkeeping is treated as a repeatable transformation process: input events
such as invoice, payment or receipt become an idempotent accounting entry. Git
records evidence, approval and history; Python executes the account-assignment
logic.

Typical states:

- `draft`
- `validated`
- `posted`
- `closed`

### Tax

Tax cases aggregate periodic data, document decisions and lead to prepared
filings. Depending on the legal environment, the actual filing can happen in an
external specialist system. Git remains the controlling evidence layer.

Typical states:

- `draft`
- `prepared`
- `approved`
- `submitted`
- `archived`

## Data Principles

- The LLM may structure inputs, but must not claim subject-matter validity.
- Deterministic Python logic decides on state transitions.
- Personal data should be minimized or referenced.
- Every effective business transaction receives a stable `request_id`.
- Idempotency keys prevent duplicate execution.

## Git As Control Layer

- A branch or pull request represents work on a matter.
- Reviews represent subject-matter approvals.
- Merge into `main` represents binding adoption.
- Tags represent closures such as `close/2026-03`.
- Releases or artifacts represent exported evidence.

## Generic vs Domain-Specific

The process world is organized in two layers:

- `generic`: usable by all organizations,
- `domain`: additional subject logic for each organization type.

Example structure:

- generic: roles, approvals, invoicing, bookkeeping, tax, deadlines,
- domain law firm: mandate, deadline control, file logic,
- domain notary office: deed process, completion steps, register
  communication,
- domain tax office: client cycles, declaration flow, inquiry management,
- domain software company: release, incident, SLA and license evidence,
- domain carpentry: measurement, workshop flow, installation and warranty.

The combination of generic plus domain forms the operational process map of
the respective organization.

## Variant Capability Instead Of One Standard Process

Different organizations need different variants. Variants are therefore
explicitly versioned:

- which variant applies,
- which unit it applies to,
- from when it applies,
- who approved it.

This keeps differences allowed, but transparent and auditable.

For mixed operation, additionally:

- the version is bound when each matter starts,
- running matters remain on their bound version,
- new releases apply only to newly started matters.

Details: [docs/en/operations/parallelbetrieb-version-binding.md](operations/parallelbetrieb-version-binding.md)

## Change Request And Inheritance

Recommended model:

1. Reference process, for example association or pattern organization.
2. Organization fork with local adjustment.
3. Change request with rationale and evidence.
4. Review and approval.
5. Versioned adoption into the local standard.
6. Optional return into the reference process.

This model enables shared learning without losing local control.

## Model Boundaries

- Git is not a high-volume transaction system.
- Git is not a replacement for legally required portals or interfaces.
- Secrets and especially sensitive documents do not belong in the repository in
  unencrypted form.
- Legal approvals require clearly defined responsibilities outside the LLM.
