# Notarkammer Demo: XNP/SNP Evidence Matrix For The Real Estate Purchase Agreement

Status: 2026-06-22

This document is a demo/modeling artifact for the real estate purchase
agreement. It describes which BPMN gates are repeatedly connected in the demo
with XNP/SNP, XNotar, card reader, signature, register, land register and
closing. It claims no productive XNP action and uses no matter data, no secrets
and no API credentials.

## Matrix

| BPMN gate | external environment | expected evidence | parallelism | critical-path relevance | demo statement |
| --- | --- | --- | --- | --- | --- |
| Create synthetic matter | NaC demo without domain-system boundary | audit metadata: demo ID, role class, timestamp, no personal reference | not parallel; start point | not critical | The real estate purchase agreement starts as a synthetic model case with no matter data. |
| Review land-register status and register context | land register, register, manual evidence | response evidence or placeholder: status present, missing, blocking | parallel in `pre_notarization_due_diligence` with draft and readiness | critical if land-register or register status blocks closing | NaC shows the evidence gap and claims no productive retrieval. |
| Check XNP/SNP, XNotar and card-reader readiness | local XNP/SNP environment, XNotar, card reader | readiness evidence: component reachable, signature path modeled, no PINs or card values | parallel in `pre_notarization_due_diligence` | usually not critical; critical only if signature readiness is missing before notarization | The demo shows system boundaries, no productive XNP action. |
| Coordinate draft and party status | XNP/SNP test access as open ISV question | audit metadata: draft status, approval status, evidence class | parallel in `pre_notarization_due_diligence` | critical if approval or a document is missing | XNP/SNP remains a test-access question, not a productive integration. |
| Confirm notarization and signature context | card reader, signature, beN, XNotar | readiness evidence and signature evidence: role, time, hash/status class, error class | sequence point after preliminary review | critical | The demo explains expected evidence without showing card values, secrets or deed contents. |
| Prepare priority notice | XNotar/beN, land register | dispatch evidence and response evidence: application prepared, dispatch status, land-register response class | parallel in `post_notarization_completion` | critical when the response is blocking | Closing depends on external response, not NaC operating time. |
| Monitor right of first refusal and authority response | municipality, register/authority context | response evidence: deadline, response class, blocking or complete | parallel in `post_notarization_completion` | critical when deadline or response blocks closing | Parallel work and the critical path become visible as BPMN evidence. |
| Track tax clearance and deletion documents | tax authority, banks, land register | response evidence: tax status, deletion status, missing or complete | parallel in `post_notarization_completion` | critical while evidence remains blocking | The demo separates evidence status from real tax, bank or land-register data. |
| Check purchase-price maturity | notarial decision, financing context | audit metadata: gate combination fulfilled, blocking, manually reviewed | transition to `ownership_transfer` | critical | NaC models the approval logic as an evidence matrix, not legal advice. |
| Transfer title and close | XNotar/beN, land register, closing | dispatch evidence, response evidence, closing audit | parallel in `ownership_transfer`, close after final response | critical until close; then not critical | The critical path ends at the final blocking closing evidence. |

## Demo Boundaries

- no productive XNP action,
- no productive XNotar, beN, register or land-register filing,
- no matter data, land-register data, register data, tax data, bank data or
  personal data,
- no secrets, no API credentials, no PINs, tokens or card values,
- demo/modeling artifact only for BPMN, evidence, parallelism and critical
  path.

