# Testament

Status: starter

## Goal

Prepare a notary-office usecase package for testament intake, preparation,
execution tracking, and evidence metadata.

## Boundaries

- The LLM is an intake and drafting assistant, not the legal authority.
- Capacity, identity, interpretation, and execution require human notarial
  review.
- No real personal data or sensitive estate information is stored in Git.

## Initial Dependencies

| Layer | Dependency | Purpose |
| --- | --- | --- |
| Plugin | `noc-regulated-core` | Shared regulated workflow guardrails. |
| Workflow | `workflows/contracts/` | Intake, approval, and evidence contract. |
| Workflow | `workflows/python/` | Deterministic checks and plan preview. |

## Delivery Plan

1. Define intake contract for person, family situation, assets as categories,
   wishes, capacity flags, and approvals.
2. Define review gates for sensitive legal interpretation and execution.
3. Create evidence metadata for intake, review, appointment, execution, and
   retention.
