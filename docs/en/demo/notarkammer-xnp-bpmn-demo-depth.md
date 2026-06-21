# Notarkammer Demo: XNP/BPMN Demo Depth

Status: 2026-06-21

This artifact strengthens the 1h Notarkammer demo track. It explains how NaC
models XNP, XNotar/XJustiz, land register, register, card reader/signature and
external evidence in BPMN. Notary-only: the language stays within notarial
workflows such as real-estate purchase agreements, land-register completion,
commercial-register filing, certification and evidence handling. There is no
raw data, no mandate data and redacted evidence only.

## Demo Core Message

In this demo, NaC is the BPMN, gate and audit frame. XNP remains an external
notarial work environment. XNotar/XJustiz, land register, register, card
reader and signature path remain an external system boundary or local
workstation path. NaC claims no live XNP API access, no productive XNP action
and no direct XNP-to-NaC land-register data delivery.

The demo therefore does not show that NaC replaces domain systems. It shows
that NaC explicitly models professional responsibility, system boundary,
evidence status, duration band, parallelism and critical path.

## BPMN Task Types For The 1h Demo

| BPMN task type | When to show it | Notarial meaning | Allowed evidence |
| --- | --- | --- | --- |
| Service Task | Automatable NaC checkpoint without domain-system operation | NaC checks whether a gate may formally continue, such as evidence present, hash plausible, deadline status set | Status, hash, timestamp, role, check result |
| User Task | Decision or confirmation by a notarial user | The notary office checks draft, representation, release, response or dispatch status | Redacted evidence, approval note, `manual_review` or `blocked` |
| Manual Task | Work performed outside NaC | Local workstation, XNP, XNotar/XJustiz, land-register or register portal, card reader or signature operation is performed outside the SaaS | Attestation without document content, PIN or login value |

The key demo sentence: Service Task explains NaC logic, User Task explains
notarial responsibility, Manual Task explains external or local domain-system
work.

## Modeling Domain-System Boundaries

| Boundary | BPMN modeling | Demo sentence | Do not claim |
| --- | --- | --- | --- |
| Local XNP | Manual Task or User Task with local gate | "XNP stays local; NaC only shows that this step blocks or releases the next BPMN status." | NaC calls XNP live or performs a productive XNP action. |
| XNotar/XJustiz | Manual Task for package, exchange or dispatch path plus User Task for confirmation | "Land-register and register communication remains an external handoff with an evidence question." | NaC performs land-register or register completion automatically. |
| Land register | External gate with duration band and response status | "The land-register response can determine the critical path." | XNP or NaC delivers property or land-register raw values into the demo. |
| Register | External gate with response status | "Register response, interim order or registration are external events." | NaC creates productive register dispatch. |
| Card reader/signature | Manual Task on the local workstation | "Card, reader and PIN entry stay local; NaC sees redacted evidence only." | Card reader or signature card are part of remote automation. |
| External evidence | User Task for professional review, Service Task for formal completeness | "Evidence is a gate question, not raw-data storage." | NaC stores identity-document, deed, register or property raw values. |

## Duration, Parallelism And Critical Path

In the 1h demo, duration values are model windows, not commitments. The
duration band explains how long a gate may shape the story. Parallelism
explains which notary-office preparations can run at the same time. The
critical path explains which external response blocks the next step.

Real-estate purchase agreement example:

- Preliminary review and drafting can run in parallel with document lists,
  role checks and appointment coordination.
- After notarization, land register, financing, municipality, tax and release
  documents run in parallel.
- The model window for external completion responses can be 2-8 weeks.
- The critical path is the last professionally required response, not the
  operating time in NaC.

Commercial-register filing example:

- Attachment review, representation review, signature path and package
  preparation can be prepared in parallel.
- XNotar/XJustiz and register remain modeled as handoff and response.
- Without a signed and professionally approved filing, the register path
  remains fail-closed.

## Presentation Guardrails

- Notary-only language: mention only notarial workflows, roles, gates,
  responses and evidence.
- No raw data: show no person, register, property, identity-document, deed,
  card or PIN content.
- No mandate data: the demo uses synthetic terms, status values and process
  models.
- Redacted evidence only: status, hash, time, role, check result and blocker
  are enough.
- No live XNP API access: open technical details remain "to be clarified in
  XNP test access".
- No production promise: every external domain system remains a boundary,
  handoff or manually confirmed gate.

## 1h Talk Track

1. "We show the notarial process first, not a domain-system login."
2. "BPMN separates Service Task, User Task and Manual Task: NaC gate,
   notarial decision and external domain-system work."
3. "XNP, XNotar/XJustiz, land register, register, card reader and signature
   are deliberately modeled boundaries."
4. "Duration band, parallelism and critical path show why external responses
   matter more than a linear click path."
5. "Without local readiness or redacted evidence, the next step remains
   fail-closed."
