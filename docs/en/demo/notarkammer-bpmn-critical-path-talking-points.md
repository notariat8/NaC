# Notarkammer Demo: BPMN Critical Path Talking Points

These notes complement the public Notarkammer demo. They provide a short talk
track for the Immobilienkaufvertrag and the Handelsregisteranmeldung and stay
deliberately source-agnostic: the demo shows only the approved BPMN model, no
case-specific client content, no operator or infrastructure details and no
productive domain-system action. All durations are planning values for the
demo narrative, not legal advice or processing commitments.

## Talk Track

- "The Immobilienkaufvertrag is a Notariat usecase with several professional
  feedback loops. BPMN makes visible which steps can be prepared in parallel
  and which step blocks the critical path."
- "The critical path is not the prettiest user interface; it is the set of
  professional gates: preliminary review, notarization, land register,
  financing, municipality, tax and final ownership transfer."
- "For Grundbuch and Register, NaC shows a handoff boundary. The model names
  when an XNotar/XJustiz package, exchange folder, portal or local
  Kartenleser/signing path becomes relevant."
- "NaC does not replace those domain systems. It preserves the evidence
  question: who prepared, reviewed, approved or documented each handoff or
  return?"
- "The Handelsregisteranmeldung shows the same point on a shorter path:
  draft, resolution or representation basis, signature, filing and register
  response are distinct gates. Some preparation takes minutes or hours; the
  blocking response can determine days or weeks."

## Process 1: Immobilienkaufvertrag

| Beat | Demo Point | Planning Value | Parallel Preparation | Blocking Event | Critical-Path Note |
| --- | --- | --- | --- | --- | --- |
| Intake and preliminary review | structure parties, property reference, drafting request and checklist | 15-30 minutes | identity/role check, document list, financing request | missing property or party information | No reliable draft without complete preliminary review. |
| Draft and alignment | prepare contract draft, exhibits, cost and completion notes | 2-6 hours | draft review, questions, appointment alignment | open change request or missing approval | Draft approval is the gate before notarization. |
| Notarization | perform appointment, identity, signing or in-person path | 60-120 minutes | prepare completion file and dispatch packages | rescheduled appointment or identity/representation issue | Completion gates start only after notarization. |
| Parallel completion | trigger priority notice, release documents, financing, municipality and tax | 1-3 working days of preparation | land-register package, financing documents, pre-emption request, tax notice | missing bank, municipality, tax or land-register response | The longest external response drives the demo narrative. |
| Ownership transfer | track payment prerequisites, clearance, releases and transfer | 2-8 weeks as model window | prepare status evidence and reminders | response from land register, financier, municipality or tax is missing | Critical path sits with the last required response. |
| Closing evidence | explain closing status, evidence and safe filing | 15-30 minutes | closing communication, control note | inconsistent or missing evidence | Close only when all gates are professionally green. |

## Process 2: Handelsregisteranmeldung

| Beat | Demo Point | Planning Value | Parallel Preparation | Blocking Event | Critical-Path Note |
| --- | --- | --- | --- | --- | --- |
| Clarify trigger and register reference | model filing type, entity, representation and resolution basis | 10-25 minutes | check register excerpt, participant roles, document list | unclear representation or missing resolution | No filing without a reliable basis. |
| Draft the filing | prepare filing text, exhibits and powers of attorney | 45-120 minutes | exhibit review, register data check, appointment window | missing exhibit or inconsistent register status | Draft must be professionally coherent before signing. |
| Certification or notarization reference | complete identity, representation and signing path | 30-60 minutes | dispatch package and internal checklist | identity, signing or representation issue | This gate blocks every register communication. |
| Prepare XNotar/XJustiz package | explain exchange package and register-portal handoff | 15-45 minutes | technical readiness, exhibit naming, approval note | missing file, wrong assignment or missing approval | NaC shows preparation and approval; the handoff stays outside the demo. |
| Monitor register response | model receipt, interim order or registration as response | 2 days to 3 weeks as model window | follow-up reminder, status note, draft response | interim order or missing register response | Register response is the critical path after filing. |
| Close and evidence | explain registration evidence, party information and filing | 15-30 minutes | closing communication and control note | registration evidence missing | Close only after professional response. |

## Parallel Preparation

- In both processes, document lists, role checks, appointment alignment, draft
  review and package preparation can run in parallel as long as no gate depends
  on professional approval.
- In the Immobilienkaufvertrag, several streams run side by side after
  notarization: land register, financing, municipality, tax and release
  documents.
- In the Handelsregisteranmeldung, exhibit review, representation review,
  signing path and package preparation run side by side until notarial approval
  allows the register handoff.
- The demo should explain duration as planning values, not as an SLA: minutes
  for intake and closing, hours for drafting and review, days for package and
  question windows, weeks for external responses.

## Blocking Events

- missing or inconsistent documents
- unresolved representation, identity or signing question
- draft not approved
- missing land-register, register, municipality, tax or financing response
- interim order, follow-up question or correction need
- missing closing evidence

## Critical Path And Evidence Question

| Beat | Demo Point | Evidence Question |
| --- | --- | --- |
| Draft and preliminary review | check professional inputs, parties, property and register references | Is the next notarial step professionally approved? |
| Notarization | appointment, identity, signing or in-person path | Is the notarization step complete or blocked? |
| Grundbuch | priority notice, release documents, ownership transfer | Which response is needed before the next completion step? |
| Register | show the Handelsregisteranmeldung as a separate gate | Is register communication only prepared, or has a response been received? |
| Close | payment prerequisites, tax, evidence, transfer | Which external response blocks closing? |

## Safe Boundary

- Notariat only: keep the talk track on notarial matters, especially the
  Immobilienkaufvertrag, Handelsregisteranmeldung and Grundbuch/Register
  handoff.
- No case-specific client content: the demo uses only public process
  references and model terms.
- Source-agnostic: do not name internal operator, tenant or
  infrastructure details.
- No production promise: XNP, Kartenleser, XNotar/XJustiz, Grundbuch and
  Register are explained as boundaries, packages, portals, local readiness and
  human-approved gates.

## Do Not Say

- "NaC automatically completes land-register or register execution."
- "XNP delivers land-register data into NaC."
- "The card reader is part of remote automation."
- "This is already a complete notarial product."
- "We show real deeds, real register content or real property data."

## Handoff

The strongest close for this section is:

"BPMN makes more than the sequence visible; it shows critical responsibility:
what can be prepared in the Notariat, which external response blocks the next
step, and which handoff deliberately remains outside the demo?"
