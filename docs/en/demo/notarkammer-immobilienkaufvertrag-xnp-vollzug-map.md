# Notarkammer Demo: Real Estate Purchase Agreement With XNP/SNP And Closing

Status: 2026-06-22

This flow map makes the real estate purchase agreement the primary
Notarkammer demo flow. It connects BPMN, XNP/SNP test access, XNotar/beN
handoffs, card reader, land register and closing so that the demo becomes
professionally concrete without productive XNP action, without matter data and
without productive land-register or register filing.

The source basis remains the
[XNP source matrix](notarkammer-xnp-quellenmatrix.md). This map turns it into a
demo and discussion path: what can NaC show today, and which XNP/SNP test
access or API boundaries must BNotK or the Notarkammer clarify for an ISV
pilot?

## Demo Goal

The appointment should show:

- NaC understands the real estate purchase agreement as a complete notarial
  process, not as a linear click path.
- XNP, XNotar, beN, card reader, land register and closing appear repeatedly
  as professional gates in the BPMN model.
- Duration bands, `parallelGroup` and `criticalPath` make visible which work
  can run in parallel and which response determines the critical path.
- XNP/SNP test access is the central ISV question: which status, evidence,
  callback or test-data surfaces may later be used officially?

## Primary BPMN Flow

| Phase | BPMN gate | External boundary | Duration band | Parallelism | Critical path | ISV question |
| --- | --- | --- | --- | --- | --- | --- |
| Intake | Create matter and party roles synthetically | No domain-system boundary | `same_day_or_internal` | - | no | Which minimal role and matter metadata may an ISV model without matter data? |
| Preliminary review | Review land-register status and documents professionally | Land register as external access point | `standard_external` | `pre_notarization_due_diligence` | yes | Does a test environment provide redacted land-register/status objects or only manual evidence? |
| Local readiness | Check XNP, XNotar, card reader and signature path | XNP/XNotar/card reader locally | `same_day_or_internal` | `pre_notarization_due_diligence` | no | May a local companion check readiness without reading PINs, tokens, card values or document contents? |
| Draft | Coordinate deed draft, closing notes and financing context | XNP/SNP test access as open boundary | `short_party_turnaround` | `pre_notarization_due_diligence` | yes | Which XNP/SNP test data is allowed for draft status, party status and evidence status? |
| Notarization | Confirm notarial approval, signature and beN context | Card reader, signature, beN | `same_day_or_internal` | - | yes | Which evidence fields may NaC store: time, role, hash, status, approval, error class? |
| Priority notice | Prepare land-register application through XNotar/beN | XNotar and land register | `standard_external` | `post_notarization_completion` | yes | Is there a status callback or only manually confirmed dispatch/response status? |
| Right of first refusal | Monitor municipality/authority response | Municipality/authority | `standard_external` | `post_notarization_completion` | yes | Which deadline and response status may be held in NaC as an evidence field? |
| Tax clearance certificate | Monitor tax response | Tax authority | `extended_external` | `post_notarization_completion` | yes | Are testable status objects available or is this only a manual notarial evidence chain? |
| Deletion documents | Track creditor and deletion documents | Banks/creditors/land register | `standard_external` | `post_notarization_completion` | yes | Which evidence form is allowed without storing document contents or bank data? |
| Purchase-price maturity | Release maturity notice only after gates pass | Notarial decision | `short_party_turnaround` | `ownership_transfer` | yes | Which gate combination can an ISV verify before showing a status as ready for maturity? |
| Transfer of title | Prepare transfer of title and monitor response | XNotar, beN, land register | `extended_external` | `ownership_transfer` | yes | Which XNP/SNP test environment represents transfer of title, status callback and response classes? |
| Closing | Close evidence, deadlines and audit status | No productive domain-system action | `same_day_or_internal` | - | no | Which audit metadata does BNotK/the Notarkammer expect for pilot operation? |

## Critical Path In The Demo

The critical path is not NaC operating time. In the demo it is the last
professionally required external response that blocks closing. For a real
estate purchase agreement this may include:

- priority notice or another land-register response,
- right of first refusal or municipal response,
- tax clearance certificate,
- deletion documents,
- purchase-price and financing release,
- transfer of title.

For the demo, the model window `2-8 weeks` is used as a narrative planning
range. It is not an SLA statement and not legal advice.

## What May Be Visible In The Demo

- Process phase, gate name, duration band, `parallelGroup`, `criticalPath`.
- Redacted evidence class: present, missing, blocked, manually reviewed.
- XNP, XNotar, beN, card reader and land register as external or local
  boundaries.
- ISV question per gate: test environment, status callback, evidence field,
  approval.

## What Must Not Be Visible

- no matter data,
- no productive XNP action,
- no productive XNotar or beN filing,
- no land-register, register, property, tax, bank or personal data,
- no PINs, tokens, card values, credentials or provider operating details.

## Discussion Question For BNotK And The Notarkammer

> We can show the real estate purchase agreement as a BPMN, evidence and
> closing path. For a real ISV pilot, we need approved XNP/SNP test access:
> which test environment, API surfaces, status callbacks, evidence fields,
> roles and certification requirements are intended for this closing path?
