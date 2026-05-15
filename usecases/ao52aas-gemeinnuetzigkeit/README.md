# AO52 Nonprofit Software Company

Status: active intake

Source repository checked on 2026-05-14: `ofunk/AO52aaS`

The source repository contained only `docs/gemeinnuetzigkeit/` documents. Those
documents are now migrated here as the canonical usecase package for forming or
restructuring a nonprofit software organization with AO52 relevance.

## Goal

Prepare a notary-office usecase package for a nonprofit or hybrid software
company. The usecase covers purpose definition, revenue classification,
structure choice, statute preparation, nonprofit pre-check, formation workflow,
and evidence metadata.

## Boundaries

- This usecase does not replace tax advice, legal advice, notarial review, or
  Finanzamt pre-clearance.
- The LLM is an intake and structuring interface, not the legal or tax truth.
- No real personal data, business secrets, tax IDs, certificates, or bank data
  may be stored in Git.
- Formation, statute wording, nonprofit qualification, and registration steps
  require human expert review.

## Initial Dependencies

| Layer | Dependency | Purpose |
| --- | --- | --- |
| Plugin | `noc-regulated-core` | Shared regulated workflow guardrails. |
| Plugin | `noc-bnotk-xnp` | Notary workstation readiness when required. |
| Plugin | `noc-handelsregister` | Register filing readiness for gGmbH/gUG or hybrid entities. |
| Plugin | `noc-elster-eric` | Tax registration and nonprofit-adjacent tax workflow planning. |
| Workflow | `workflows/contracts/` | Intake, approval, data-class, and evidence contract. |
| Workflow | `workflows/python/` | Deterministic checks for completeness, gates, and plan preview. |

## Delivery Plan

1. Define intake contract for purpose, target groups, product, revenue streams,
   legal form, stakeholders, funding, and review owners.
2. Bind AO52 purpose and statute pre-checks to a human tax/legal review gate.
3. Create a formation plan preview for pure nonprofit, nonprofit with economic
   business operation, and hybrid structure.
4. Bind register-readiness and tax-readiness plugin outputs.
5. Define evidence metadata for purpose decision, structure decision, statute
   review, notarial formation, tax pre-check, and Day2 compliance review.

## Migrated Source Documents

- `docs/gemeinnuetzigkeit/README.md`
- `docs/gemeinnuetzigkeit/01-zweckbild.md`
- `docs/gemeinnuetzigkeit/02-finanzierungsmodell.md`
- `docs/gemeinnuetzigkeit/03-strukturmodell.md`
- `docs/gemeinnuetzigkeit/04-vorabpruefung-checkliste.md`
