# Handelsregisteranmeldung

Status: KG baseline  
KG node: `case.handelsregisteranmeldung`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, HGB Section 12, GmbHG

## Goal

Prepare a notary-office usecase package for commercial-register applications:
managing director changes, seat relocation, company name changes, capital
measures, object changes, procuration, branch data and similar register events.

## Scope

- Intake for entity, register number, event type, signers, authority evidence,
  effective date, required attachments and XNP route.
- Public certification and electronic filing readiness.
- Machine-readable package checks and register response evidence.

## Out of Scope

- No automatic filing without notarial approval.
- No real register packages, IDs or company documents in Git.
- No hidden substitution of missing corporate resolutions.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `entity.identity` | Which entity, register court and register number are affected? | Notary clerk | Company register data |
| `event.type` | Which register event is being filed? | Notary | Company data |
| `signers.identity` | Who must sign and how is authority proven? | Notary clerk | Personal or company data |
| `corporate.resolution` | Which resolution or legal basis authorizes the filing? | Notary | Company data |
| `attachments.required` | Which electronic attachments are required? | Notary clerk | Company data |
| `effective.date` | Is the change effective, conditional or register-effective only? | Notary | Mandate metadata |
| `xnp.route` | Which notary card, XNP workspace and EGVP/beN route applies? | Notary clerk | Technical metadata |
| `fees.costs` | Which value or fee metadata is needed? | Notary clerk | Financial metadata |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Register application | Publicly certified filing instrument. | Metadata only in Git. |
| Corporate evidence | Resolution, appointment, articles or authority proof. | Evidence reference only. |
| Electronic attachments | Machine-readable filing package. | Hash/reference only after review. |
| Register response | Confirms submission, correction or completion. | Trace metadata only. |

## Decisions

- Standard event route or special legal review.
- Signature method: in-office, video route, existing certified power or blocked.
- Whether attachments are complete and machine-readable.
- Whether correction or resubmission is needed after register response.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Public certification requirements met | Notary | Filing |
| Authority and signer identity reviewed | Notary | Signature |
| Electronic package format checked | Notary clerk | Submission |
| Register response reviewed | Notary clerk | Closing |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Guardrails and evidence model. |
| `noc-bnotk-xnp` | XNP and notary signature route. |
| `noc-handelsregister` | Register filing readiness and response handling. |
| `noc-cyberjack-rfid` | Card and reader readiness for notary signature. |

## Delivery Tasks

1. Build event-type taxonomy and required-attachment matrix.
2. Bind signer identity and authority evidence to public certification gate.
3. Add XNP and register-package dry-run.
4. Add response-state model for submitted, corrected, completed or blocked.
5. Validate with synthetic HRB/HRA fixtures.

## Acceptance Criteria

- Event type determines required attachments.
- Signer authority must be reviewed before public certification.
- XNP route must be ready before submission.
- Register response is captured as evidence metadata.

