# Gesellschafterbeschluss bei GmbH/UG

Status: KG baseline  
KG node: `case.gesellschafterbeschluss_gmbh_ug`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, GmbHG Section 53, HGB Section 12

## Goal

Prepare a notary-office usecase package for GmbH/UG shareholder resolutions,
including articles amendments, capital increases, managing-director
appointments, consent to share transfers and other register-relevant decisions.

## Scope

- Intake for company, register data, resolution type, shareholders, votes,
  representation, majority requirements and articles wording.
- Notarial deed or certification route selection.
- Register filing and notary certificate evidence.

## Out of Scope

- No automated company-law final assessment.
- No real shareholder lists, minutes or articles in Git.
- No register filing without XNP/Handelsregister review.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `company.identity` | Which GmbH/UG and register data are affected? | Notary clerk | Company register data |
| `resolution.type` | Which resolution type and legal basis apply? | Notary | Company data |
| `shareholders.present` | Who participates and who represents whom? | Notary clerk | Personal or company data |
| `majority.requirement` | Which statutory and articles majority rules apply? | Notary | Company data |
| `articles.wording` | Which current text changes and what is the new wording? | Notary | Company data |
| `register.filing` | Which register application and XNP route are needed? | Notary clerk | Technical metadata |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Resolution minutes or deed | Captures decision and votes. | Synthetic or metadata only. |
| Current and amended articles | Supports notary certificate and register filing. | Evidence reference only. |
| Register application | Filing package. | Metadata only. |
| Voting/authority evidence | Supports quorum and majority gate. | Evidence reference only. |

## Decisions

- Notarial deed, certified signature or private resolution only.
- Register filing required or not.
- Majority/unanimity threshold and special consent rules.
- Whether current articles wording is sufficient.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Quorum, votes and majority reviewed | Notary | Deed release |
| Authority and representation reviewed | Notary | Execution |
| Articles wording certified | Notary | Register filing |
| Register package ready | Notary clerk | Submission |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Regulated company workflow guardrails. |
| `noc-bnotk-xnp` | Notary filing route readiness. |
| `noc-handelsregister` | Register package and response handling. |
| `noc-cyberjack-rfid` | Card/signature readiness. |

## Delivery Tasks

1. Create resolution-type taxonomy.
2. Add vote and majority completeness checks.
3. Bind articles wording to notary certificate package.
4. Add register filing state model.
5. Validate with synthetic GmbH/UG fixtures.

## Acceptance Criteria

- Majority and representation review blocks execution.
- Articles wording must be available for amendments.
- Register relevance is explicit.
- No real company minutes or shareholder data are committed.

