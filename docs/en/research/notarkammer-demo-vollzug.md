# Notarkammer Demo: Completion Flow, Duration Logic and Critical Path

This note supports the Notarkammer demo. It is not an official statistical
source and contains no client data. Durations are deliberately modeled as
planning values: hours, days, weeks and months. They are not official averages.

## Source Baseline

- German Federal Chamber of Notaries, purchase-price maturity:
  https://www.notar.de/themen/immobilien/kaufpreisfaelligkeit
- German Federal Chamber of Notaries, transfer of ownership:
  https://www.notar.de/themen/immobilien/eigentumsuebergang
- German Federal Chamber of Notaries, notarial costs:
  https://www.notar.de/themen/notarkosten
- German Federal Chamber of Notaries, fee calculator:
  https://www.notar.de/themen/notarkosten/gebuehrenrechner

## Real Estate Purchase Agreement Reasoning

Completion is not linear. After notarization, several work streams can run in
parallel, but not every stream has the same effect on the next legal action.
The critical path is created where an incoming confirmation is required before
the next step may proceed.

The purchase price usually becomes due only after specific prerequisites are
met. According to the German Federal Chamber of Notaries, these include
required approvals, the priority notice in the land register, documents for
releasing non-assumed encumbrances and clarification of municipal pre-emption
rights. The notarial office informs the parties once these prerequisites are
met.

Transfer of ownership is downstream. According to the same source, the
application for ownership transfer is submitted after full payment of the
purchase price. The tax clearance certificate may also be required.

## Demo Modeling

| Phase | Planning value | Parallel work possible | Critical path |
| --- | --- | --- | --- |
| Intake and preliminary review | hours to days | limited | yes, if documents are missing |
| Drafting and alignment | days | partly | yes, if approvals are missing |
| Notarization | hours | no | yes |
| Priority notice, approvals, releases, pre-emption | days to weeks | yes | yes, if maturity prerequisite |
| Purchase-price payment and economic transfer | days to weeks | partly | yes |
| Tax and land-register feedback, ownership transfer | weeks to months | yes | yes, if feedback is missing |

The BPMN usecase view therefore exposes these external gates separately:
`Task_VormerkungBeantragen`, `Task_LoeschungsunterlagenNachhalten`,
`Task_VorkaufsrechtKlaeren`, `Task_UnbedenklichkeitNachhalten` and
`Task_EigentumsumschreibungEinreichen`. All five steps use mandate-data-free
model metadata and describe only the handoff/evidence boundary. XNP is not a
land-register data source for NaC; land-register communication is described as
an `xnotar_xjustiz`/land-register portal boundary.

## Demo Message

The visualization should not claim how long a specific case will take. It
should show:

- which work can start immediately,
- which steps wait for external feedback,
- which feedback blocks the critical path,
- where duration classes are editable planning values,
- why a linear four-step view simplifies completion too much.
- that critical-path and duration-class metadata does not trigger runtime,
  OCI, release, apply or cloud actions.

## Fee Logic

Notarial costs are legally regulated and are not negotiated freely. For the
demo, the relevant point is modularity: a fee-calculation component should not
be rebuilt for every use case, but maintained once as a central GNotKG module
inside matter handling.

The public demo should only show that this module is planned. It should not
show a binding cost calculation or real transaction values.
