# Vereinsregisteranmeldung

Status: KG baseline  
KG node: `case.vereinsregisteranmeldung`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, BGB Section 77

## Goal

Prepare a notary-office usecase package for association-register filings, such
as board changes, articles amendments, new registrations, dissolution or
liquidator changes.

## Scope

- Intake for association, register data, filing type, board signers, resolutions,
  articles and court route.
- Public certification of board signatures.
- Attachment and copy package tracking.
- Register-court response evidence.

## Out of Scope

- No association-law final assessment by the LLM.
- No real membership lists, minutes or signatures in Git.
- No court submission without reviewed signing authority.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `association.identity` | Which e.V., register court and number are affected? | Notary clerk | Association register data |
| `filing.type` | Which filing type is needed? | Notary | Association data |
| `board.identity` | Which board members sign and how may they represent? | Notary clerk | Personal data |
| `resolution.evidence` | Which minutes, election or resolution evidence is needed? | Association | Association data |
| `articles.current` | Which articles text applies and was it changed? | Association | Association data |
| `filing.route` | Which court route and copy package applies? | Notary clerk | Technical metadata |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Register application | Certified application package. | Metadata only. |
| Minutes/election/resolution evidence | Supports filing. | Evidence reference only. |
| Articles or amended wording | Supports articles amendment. | Evidence reference only. |
| Court response | Tracks completion or correction. | Metadata only. |

## Decisions

- Paper, electronic or video-certification route.
- Attachment package complete or special review.
- Board representation rule.
- Whether articles amendment needs full wording comparison.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Board signer authority reviewed | Notary | Certification |
| Resolution and articles evidence reviewed | Notary | Application release |
| Register package ready | Notary clerk | Submission |
| Court response reviewed | Notary clerk | Closing |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Guardrails and evidence model. |
| `noc-bnotk-xnp` | Electronic route readiness where used. |
| `noc-idaas` | Identity support where permitted. |

## Delivery Tasks

1. Define filing-type and attachment matrix.
2. Add board authority and signing checks.
3. Add articles comparison placeholder.
4. Add court submission state model.
5. Validate with synthetic e.V. fixtures.

## Acceptance Criteria

- Signer authority blocks certification.
- Filing type determines attachments.
- Court response is tracked.
- No real association member or board data is committed.

