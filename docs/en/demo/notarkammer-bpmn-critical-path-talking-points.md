# Notarkammer Demo: BPMN Critical Path Talking Points

These notes complement the public Notarkammer demo. They provide a short talk
track for the Immobilienkaufvertrag and stay deliberately source-agnostic: the
demo shows only the approved BPMN model, no case-specific client content, no
operator or infrastructure details and no productive domain-system action.

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

## Critical Path

| Beat | Demo Point | Evidence Question |
| --- | --- | --- |
| Draft and preliminary review | check professional inputs, parties, property and register references | Is the next notarial step professionally approved? |
| Notarization | appointment, identity, signing or in-person path | Is the notarization step complete or blocked? |
| Grundbuch | priority notice, release documents, ownership transfer | Which response is needed before the next completion step? |
| Register | where a register reference exists, show the handoff as a separate gate | Is register communication only prepared, or has a response been received? |
| Close | payment prerequisites, tax, evidence, transfer | Which external response blocks closing? |

## Safe Boundary

- Notariat only: keep the talk track on notarial matters, especially the
  Immobilienkaufvertrag and Grundbuch/Register handoff.
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
