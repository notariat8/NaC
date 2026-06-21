# Notarkammer Demo 2026-06: Demo Gap Audit

Status: 2026-06-21

Purpose: This versioned artifact prioritizes what is showable for the demo in
4 days, what remains an intentional fallback, and which product gaps come
after the demo. It is not marketing copy and it does not claim implementation
that is not evidenced in the repository.

## Priority Legend

- P0: Showable in the Demo in 4 Days if preflight is green.
- P1: Intentional Fallback for the Demo in 4 Days.
- P2: After the Demo as a product gap or integration step.

## Compact Gap List

| Priority | Category | Current State | Demo Statement | Boundary | Next Real Integration Step |
| --- | --- | --- | --- | --- | --- |
| P0 | XNP Access | XNP is documented as a local specialist-system boundary: [notarkammer-xnp-demo-contract.md](notarkammer-xnp-demo-contract.md) covers XNP, XNotar, card reader, beN, UVZ/VVZ and evidence only as local or external boundaries. | Showable: NaC makes it visible in BPMN when XNP/XNotar/card-reader context matters and whether local evidence is missing or present. | No production XNP action, no direct cloud control of XNP, no API keys, no PINs, no login tokens and no mandate data in NaC. | Obtain official XNP test-access and interface definition; then trial a local companion only on the notarial workstation for readiness and redacted evidence. |
| P0 | BPMN Editor/Viewer | BPMN models, profile and validators exist; the critical-path talk track is in [notarkammer-bpmn-critical-path-talking-points.md](notarkammer-bpmn-critical-path-talking-points.md). | Showable: Immobilienkaufvertrag and Handelsregisteranmeldung can be explained as BPMN/process models with critical path, duration band and external gates. | Editor/viewer polish is not proof of productive specialist-system integration; do not show case contents, register data or land-register data. | Harden the viewer/editor path as a stable demo surface and sharpen BPMN gates for XNP, register, land register, signature and evidence in the profile. |
| P0 | Workspace/Auth | Login intent, protected workspace start and fail-closed workspace are tested and planned in the preflight checklist as security evidence. | Showable: Without approved demo session the workspace remains closed; that is the correct security boundary. | No real login during the meeting without owner approval; no mandate data, role secrets, client files or session values in the PR or demo. | Prepare a demo tenant with synthetic roles and an approved OIDC path; then open workspace metadata only until case/document gates are approved. |
| P1 | ATP/Onboarding | Public onboarding, DNS readiness and request status are documented as a demo path; ATP is only the store gate for onboarding requests. | Intentional Fallback: If the store or healthcheck is unavailable, `disabled`, `unavailable` or `not_checked` is explained as setup status. | No OCI writes, no wallet/DSN output, no secret inspection during the meeting, no provisioning beyond dry-run or read-only evidence. | Stabilize the ATP healthcheck with a non-sensitive status projection and prepare the onboarding request store for synthetic demo requests. |
| P0 | Fees/GNotKG | A technical fee draft exists: [src/nac_gnotkg/costs.py](../../../src/nac_gnotkg/costs.py) and [tests/test_gnotkg_costs.py](../../../tests/test_gnotkg_costs.py) verify value fees, minimum fee, table caps and the review boundary. Demo Link: cost review as a specialist gate in the real-estate purchase flow. | Showable: GNotKG can be explained as a review gate that makes value, KV number, table and fee technically traceable. | GNotKG remains not production fee billing, not legal advice, not a final notarial cost review by software and no real business values. | Connect the cost view to the BPMN gate and specialist approval; expand KV cases and use-case mapping after the demo through notary review. |
| P2 | Notariat-only Guardrails | Repository rules, demo preflight and XNP/BPMN documents limit NaC to notarial use cases and synthetic demo data. | After the Demo: Guardrails should become a reusable demo/product check in the quality gate or docs validator. | Notariats-only; no mandate data, no secrets, no production register or land-register action, no non-notarial product paths. | Add a validator for demo artifacts: notarial scope, no mandate data, no OCI writes, no secrets and no false integration claims. |

## Showable In 4 Days

- Showable: notarial process with BPMN, critical path, XNP/XNotar boundary,
  fail-closed Workspace/Auth and the GNotKG review gate as a technical draft.
- Showable: public onboarding and ATP/Onboarding status if the read-only
  preflight is green.
- Showable: fallback narrative if XNP, ATP or login is unavailable: the
  system intentionally stops at the boundary.

## Intentional Fallback

- XNP Access remains a local readiness and evidence boundary in the demo, not
  a live adapter.
- ATP/Onboarding remains a status gate when the store is missing, not live
  debugging.
- Workspace/Auth remains closed without an approved session.
- BPMN Editor/Viewer can be replaced by the public process-model page or a
  prechecked local tab.

## After the Demo

1. Clarify XNP test access, usage terms and local interface definition.
2. Further normalize BPMN gates for XNP, XNotar/XJustiz, land register,
   register, signature and evidence in the profile.
3. Trial Workspace/Auth with a synthetic demo tenant and metadata-only
   workspace.
4. Stabilize ATP/Onboarding as non-sensitive status projection and request
   store.
5. Grow Fees/GNotKG from a technical fee draft into a notary-reviewed gate.
6. Add Notariat-only Guardrails as automated documentation and demo checks.

## Guardrails

- NaC is notariats-only and limited to notarial process types.
- This demo uses no mandate data, no secrets, no PINs, no login tokens and no
  real register or land-register contents.
- This demo performs no OCI writes, no productive provisioning, no release
  action and no production XNP action.
- Every statement must remain identifiable as a model, local readiness
  evidence, fallback or next product gap.
