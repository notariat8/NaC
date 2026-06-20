# Notarkammer Demo: Domain Evidence For Real-Estate Execution

Status: working state for demo readiness
Date: June 20, 2026
Scope: real-estate purchase agreement and public, mandate-data-free demo context

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: notarkammer-demo-domain-evidence
leading_issue: thread:2026-06-20-notarkammer-demo-readiness
risk_gate: Notarkammer Demo Readiness
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
validation_commands:
  - /home/ubuntu/.venvs/nac/bin/python scripts/validate_language_parity.py
  - /home/ubuntu/.venvs/nac/bin/python scripts/validate_spec_traceability.py
  - /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

## Purpose

This evidence supports the Notarkammer demo with domain context. It describes
typical execution problems, dependencies, parallel work, the critical path and
duration classes. Duration values are planning parameters, not official
averages, unless a citable official statistical source is added later.

## Legal And Domain Anchors

- Real-estate purchase contracts require notarization; domain anchor:
  BGB section 311b.
- Ownership changes in land require agreement and registration; domain anchor:
  BGB section 873.
- The priority notice secures the claim to a change in rem; domain anchor:
  BGB section 883.
- Conveyance is the agreement on transfer of ownership; domain anchor:
  BGB section 925.
- Land-register applications, priority, interim orders, consent and conveyance
  evidence are relevant through the GBO, especially sections 13, 17, 18, 19
  and 20.
- Real-estate transfer tax notification and tax clearance are execution gates;
  domain anchors: GrEStG sections 18 and 22.
- Municipal pre-emption rights and negative certificates can shape execution;
  domain anchors: BauGB sections 24 and 28.
- Notarization, identity certainty, advice and deed procedure run under the
  BeurkG; domain anchor: BeurkG section 17.

## Typical Execution Blockers

- Party identity, authority, power of attorney, company evidence or inheritance
  evidence is unclear.
- Consumer-related draft and review duties are not documented cleanly.
- Land-register status does not match the matter intake.
- Priority notice, rank or pending applications block the next stage.
- Non-assumed encumbrances require release documents, trust conditions or
  payoff amounts.
- Financing or land charge preparation is late or rank conditions are unmet.
- Municipality, authority or another body does not return approval or negative
  certificate in time.
- Real-estate transfer tax is not assessed, unpaid or the tax clearance
  certificate is missing.
- Purchase-price payment or payment evidence is missing.

## Parallel Work

After notarization, several workstreams can start in parallel:

- notification to the tax office,
- request to municipality or authority,
- application for priority notice,
- coordination of release documents,
- financing land charge and bank conditions,
- follow-up on approvals.

These workstreams converge at purchase-price maturity. In the demo, the
maturity notice may only appear possible after all relevant maturity
prerequisites are true.

## Critical Path

The critical path depends on the case. For the demo, this path is plausible:

1. Draft readiness and any consumer review period.
2. Notarization.
3. Post-notarization dispatch and applications.
4. Entry of the priority notice.
5. Approvals, negative certificate and release documents.
6. Financing or land-charge readiness if financed.
7. Maturity notice.
8. Purchase-price payment.
9. Tax clearance certificate.
10. Ownership transfer registration.

The longest external response often dominates the total duration. It can be
the land registry, municipality, tax office, bank or a creditor to be released.

## Demo-Safe Duration Classes

These classes are intentionally planning values:

| Class | Time range | Use |
| --- | --- | --- |
| `same_day_or_internal` | 0-1 business day | internal review, dispatch, status update |
| `short_party_turnaround` | 1-5 business days | missing information, bank forms, simple evidence |
| `standard_external` | 1-3 weeks | usual external response in the demo |
| `extended_external` | 3-8 weeks | land registry, authority, bank or creditor with longer processing |
| `statutory_or_exceptional` | up to 2 months or more | statutory windows, special approvals, complex cases |

## Recommended Real-Estate Process Skeleton

1. Receive inquiry and parties.
2. Check identity, authority and register or inheritance evidence.
3. Capture land or condominium data.
4. Check current land-register status.
5. Check ownership, encumbrances and pending applications.
6. Clarify financing, land charge and bank conditions.
7. Clarify non-assumed encumbrances and release needs.
8. Check public-law approvals and pre-emption rights.
9. Clarify purchase price, maturity, possession, benefits and burdens.
10. Check GNotKG business value and cost path.
11. Create deed draft.
12. Check and document consumer period if applicable.
13. Send draft.
14. Document questions and party approvals.
15. Prepare notarization.
16. Perform notarization.
17. Create certified copies and copies.
18. Notify tax office.
19. Contact municipality or authority.
20. Apply for priority notice.
21. Coordinate release documents and payoff amounts.
22. Prepare and file land charge if financed.
23. Follow up on approvals and negative certificates.
24. Check priority notice and rank.
25. Check maturity prerequisites.
26. Send maturity notice.
27. Capture purchase-price payment or payment evidence.
28. Document transfer of possession, benefits and burdens.
29. Follow up on tax clearance certificate.
30. Apply for ownership transfer.
31. Check land-register completion.
32. Check GNotKG billing.
33. Document closing evidence and matter close.

## Demo Modeling Rule

Every step may carry duration, parallel-group and critical-path metadata only.
Real mandate values, persons, land identifiers, file numbers, accounts, amounts
or portal credentials remain outside the repository.

## Acceptance Criteria

- AC-001: The evidence names legal anchors for notarization, priority notice,
  land-register execution, real-estate transfer tax and pre-emption rights
  without mandate data.
- AC-002: Duration classes are explicitly described as planning parameters and
  not as official averages.
- AC-003: The process structure shows parallel work and critical path without
  real person, land, account, file or portal values.
