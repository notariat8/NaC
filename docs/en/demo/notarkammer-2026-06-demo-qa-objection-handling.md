# Notarkammer Demo 2026-06: Q&A and Objection Handling

Status: Protected PR ready speaker sheet for the live demo. This document
complements the [Live Runbook](notarkammer-2026-06-live-demo-runbook.md), the
[XNP Demo Contract](notarkammer-xnp-demo-contract.md) and the
[source matrix for completion and duration logic](../research/notarkammer-demo-vollzug.md).

Scope: demo Q&A, objection handling and safety boundaries. No runtime change,
no infrastructure action, no productive filing, no provider or operator
details, no secrets and no mandate data. The statements are demo orientation,
not legal advice.

## Short Answers

| Question or Objection | Precise Answer |
| --- | --- |
| What does NaC show live? | NaC shows the notarial workflow as a BPMN model with visible domain-system boundaries, Evidence Gates, response status and critical path. The live view is the public process view, demo model, protected entry or fail-closed workspace, plus the speaker line from the runbook. It does not show real files, deeds, register contents, property data or credentials. |
| What does XNP do in the demo? | XNP is the local domain-system boundary for XNP-adjacent tasks such as readiness, role, official activity context and UVZ/VVZ-adjacent steps. NaC does not claim to control XNP from the cloud. XNP does not deliver land-register data to NaC. |
| Is anything filed productively? | No. The demo shows preparation, the evidence question, Gate status and handoff boundaries. It does not trigger a productive register or land-register filing, start dispatch or automate an external domain-system process. |
| Where does the card reader run? | The card reader runs on the approved local workstation in the user's role and official activity context. NaC models the card-reader path as a local readiness Gate and accepts only redacted Evidence such as status, timestamp, role and check result. PINs, keys, tokens and raw data do not belong in NaC. |
| How are land-register and register responses handled? | Responses remain external domain events. NaC models them as BPMN Gates, follow-up tasks, evidence questions and redacted Evidence. If there is an interim order, missing confirmation or inconsistent response, the next step remains blocked or moves to manual review. |
| What is the critical path? | The critical path is the longest blocking professional response, not the UI. In an Immobilienkaufvertrag this is typically a land-register, financing, municipality, tax or release-document response. In register matters, signature, approval, handoff and register response are the central Gates. Duration values remain planning values, not commitments. |
| What is not productive yet? | Productive filing, productive XNP/XNotar automation, direct land-register data intake, real mandate handling, real credentials and binding cost or legal answers are not productive. The demo is an auditable workflow and Evidence proof point. |
| How is mandate data protected? | The demo uses synthetic or public model information. Mandate data, personal details, deeds, identity documents, property data, register contents, secrets and tokens are not shown and are not copied into Q&A or screenshots. Evidence is redacted and limited to status, hash, timestamp, role and check result. |
| What if login fails? | Do not debug live. Explain the closed workspace as fail-closed security evidence and switch to the public process model plus the runbook fallback. Without explicit demo approval, the login flow is not continued. |
| What if XNP or the card reader is unavailable? | Start no productive XNP action. Mark the local Gate as `manual_review` or `blocked` and explain that NaC does not release the next action without local readiness. Continue the demo with the BPMN model, screenshots or speaker line. |
| What if the website is unavailable? | Do not repair live. Use already loaded tabs, approved screenshots or the local process-model explanation. The message remains: NaC makes workflow, domain-system boundaries, responses and critical path visible. |

## Objection Handling

### "Is this already a full notarial product?"

No. The demo shows a controlled slice: BPMN, Evidence Gates, domain-system
boundaries, fallbacks and safe speaker lines. It does not claim complete
production readiness, direct domain-system automation or a legal assessment of
a concrete matter.

### "Why does NaC not control XNP directly?"

Because the demo respects the local domain-system boundary. XNP, card reader,
signature path and official activity context belong on the approved
workstation. NaC shows when this prerequisite matters professionally and blocks
the next BPMN step when redacted Evidence is missing.

### "How does a response become work again?"

A response is not treated as invisible automation; it becomes an evidence
question: what came back, who checked it, which decision follows and which Gate
is still open or released? For land-register and register matters, incoming
confirmation, interim order, registration, missing attachment or inconsistent
response can each be explained as a separate Gate state.

### "Why is the critical path relevant for the chamber?"

The demo shows which work can be prepared immediately and which external
response actually blocks the next step. That explains notarial work as a
professionally auditable completion path with responsibilities, evidence and
waiting reasons, rather than reducing it to a user interface.

### "Where is the security boundary?"

The boundary stands before mandate data, productive domain-system actions,
credentials, local keys and raw documents. NaC may show demo status and
redacted Evidence; real contents, secrets, card PINs, register data, property
data and operator details stay outside the demo.

## Speaker Stop-Lines

- "We show the workflow and evidence boundary, not a productive filing."
- "XNP stays local; XNP does not deliver land-register data to NaC."
- "Without local readiness or Evidence, the Gate remains blocked."
- "We do not debug live; we switch to the approved fallback."
- "The demo uses no mandate data and is not legal advice."

## Sources and Companion Documents

- [Live Runbook](notarkammer-2026-06-live-demo-runbook.md)
- [Demo Script](notarkammer-2026-06-demo-script.md)
- [Demo Preflight](notarkammer-2026-06-demo-preflight.md)
- [XNP Demo Contract](notarkammer-xnp-demo-contract.md)
- [Source matrix: completion, duration logic and critical path](../research/notarkammer-demo-vollzug.md)
