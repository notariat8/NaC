# Notarkammer Process Editor

Status: contract-first, no productive cloud apply.

The Notarkammer process editor defines the safe boundary between the BPMN
editor, BPMN viewer, Git templates and M365/SharePoint runtime metadata. The
demo target is an Immobilienkaufvertrag that makes XNP/SNP boundaries,
XNotar/XJustiz, land-register boundaries, card-reader readiness, completion,
parallel work, duration band and critical path visible.

## Data And Storage Boundary

- Git remains the source of truth for BPMN templates, contracts, governance
  and review evidence.
- M365/SharePoint lists, document libraries and a later event journal are the
  runtime data plane for tenant, matter, process instance, process events,
  audit metadata and graph projection.
- No mandate data is stored in templates or in the public demo.
- This contract performs no productive XNP access and no live register query.

## Editable Surfaces

The editor may only change demo-safe and review-safe structure:

- BPMN editor structure and step labels.
- Duration band per step, for example minutes, hours, days, weeks or months.
- Parallel groups for work that can be prepared at the same time.
- Critical path hints when an external response or approval blocks completion.
- XNP/SNP, XNotar/XJustiz, land-register and card-reader gates as model
  boundaries.

Every template change goes through review and a protected PR before it reaches
the template catalog.

## Viewer And Demo

The viewer shows process structure, not mandate content. For the Notarkammer
demo, the important point is that NaC can show where the Immobilienkaufvertrag
would communicate with XNP/SNP, which steps can run in parallel and which gates
define the critical path. The later graph projection from runtime events can
render the same process as a status view.
