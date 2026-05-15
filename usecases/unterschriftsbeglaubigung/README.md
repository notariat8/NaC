# Beglaubigung von Unterschriften

Status: KG baseline  
KG node: `case.unterschriftsbeglaubigung`  
Primary source anchors: BeurkG, HGB Section 12 where register filing applies

## Goal

Prepare a notary-office usecase package for certification of signatures and
hand signs. Typical destinations include register applications, powers of
attorney, approvals, deletion consents, authority declarations and foreign-use
documents.

## Scope

- Intake for signer, document purpose, signature mode, representation, language,
  recipient route, copies and legalization/apostille flags.
- Identity and signature-act evidence.
- Paper, electronic or register filing route metadata.

## Out of Scope

- No certification without identity and notary review.
- No real documents or signatures in Git.
- No foreign-law assessment as automated truth.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `signer.identity` | Who signs and how is identity established? | Notary clerk | Personal data |
| `document.purpose` | What is the document used for and who receives it? | Notary clerk | Mandate metadata |
| `signature.mode` | Is the signature acknowledged or made before the notary? | Notary | Mandate metadata |
| `language.understanding` | Does the signer understand the relevant language? | Notary | Sensitive process data |
| `representation.context` | Does the signer act personally or as representative? | Notary clerk | Personal or company data |
| `copies.routing` | Which copies, electronic certificates and delivery routes are needed? | Notary clerk | Mandate metadata |
| `special.form` | Is apostille, legalization or register-specific form needed? | Notary | Mandate metadata |
| `fee.metadata` | Which value or fee metadata is needed? | Notary clerk | Financial metadata |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Document with signature | Object of certification. | Never store real document in Git. |
| Certification note or electronic witness | Notarial certificate output. | Metadata or synthetic output only. |
| Identity check reference | Shows identity gate passed. | Evidence reference only. |
| Delivery trace | Tracks recipient route. | Metadata only. |

## Decisions

- Certify signature only or include authority evidence.
- Paper, electronic, register filing or foreign-use route.
- Whether translation, interpreter or accessibility support is needed.
- Whether apostille/legalization follow-up is required.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Identity and signature act reviewed | Notary | Certification |
| Representation authority checked where relevant | Notary | Certificate wording |
| Correct form and route selected | Notary clerk | Delivery |
| Foreign-use follow-up clarified | Notary | Closing |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Shared guardrails and evidence model. |
| `noc-idaas` | Identity support where permitted. |
| `noc-bnotk-xnp` | Electronic certificate or register route readiness. |

## Delivery Tasks

1. Create certification intake schema and route taxonomy.
2. Bind identity evidence to the signature act gate.
3. Add form-choice rules for paper, electronic and register routing.
4. Add delivery evidence model.
5. Validate with synthetic signer and document-purpose fixtures.

## Acceptance Criteria

- Signature mode and identity gate are mandatory.
- Language and representation flags cannot be silently ignored.
- Foreign-use and routing decisions are explicit.
- No real signatures or documents are committed.

