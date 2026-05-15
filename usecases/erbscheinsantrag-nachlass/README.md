# Erbscheinsantrag / Nachlassangelegenheiten

Status: KG baseline  
KG node: `case.erbscheinsantrag_nachlass`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, BGB Section 2353, GBO inheritance evidence

## Goal

Prepare a notary-office usecase package for certificate of inheritance
applications, estate declarations, renunciations, oaths and related estate court
processes. The package must separate sensitive family facts from workflow state
and use evidence references instead of raw personal data.

## Scope

- Intake for decedent, jurisdiction, applicants, heirship basis, family
  evidence, dispositions, renunciations and oath statement.
- Application draft and evidence package preparation.
- Estate court submission and response tracking.

## Out of Scope

- No automated final heirship determination.
- No real civil-status certificates, wills or estate facts in Git.
- No hidden storage of family disputes or sensitive declarations.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `decedent.identity` | Who died, when and where, and which evidence confirms this? | Applicant | Personal data |
| `residence.jurisdiction` | Which estate court has jurisdiction? | Notary clerk | Mandate metadata |
| `applicants.identity` | Who applies and in which legal position? | Notary clerk | Personal data |
| `heirship.basis` | Is heirship statutory, testamentary, contractual or European? | Notary | Sensitive family data |
| `family.evidence` | Which civil-status evidence is required? | Applicant | Family data |
| `dispositions.evidence` | Which wills, contracts and opening records exist? | Notary clerk | Sensitive legal data |
| `renunciations.disclaimers` | Are there renunciations, contests or disclaimers? | Notary | Sensitive legal data |
| `oath.statement` | Which facts must be declared under oath and by whom? | Notary | Sensitive process data |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Death evidence reference | Establishes death fact. | Evidence reference only. |
| Civil-status evidence package | Supports statutory succession. | External reviewed evidence store. |
| Disposition and opening record reference | Supports testamentary succession. | Evidence reference only. |
| Erbschein application draft | Human-reviewed application. | Synthetic or metadata only. |
| Court submission trace | Tracks filing and response. | Metadata only. |

## Decisions

- Certificate type: national Erbschein, European certificate, renunciation or
  other estate declaration.
- Oath route: notary, court, not required or unknown.
- Whether statutory or testamentary evidence is sufficient.
- Whether disputes, disclaimers or contests block application readiness.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Heirship and evidence reviewed | Notary | Application release |
| Oath statement readiness | Notary | Appointment |
| Evidence package complete | Notary clerk | Court submission |
| Court response reviewed | Notary clerk | Closing |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Sensitive estate workflow guardrails. |

## Delivery Tasks

1. Define estate-intake schema with strict privacy classes.
2. Add civil-status and disposition evidence checklist.
3. Add oath declaration route logic.
4. Add court submission state model.
5. Validate with synthetic succession fixtures.

## Acceptance Criteria

- Application cannot be marked ready without heirship and evidence review.
- Oath route must be explicit.
- No real decedent, family or estate evidence is committed.
- Court response is tracked as metadata only.

