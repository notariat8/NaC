# Vollmacht fuer Immobilien- oder Gesellschaftsgeschaefte

Status: KG baseline  
KG node: `case.vollmacht_immobilien_gesellschaft`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, BGB Sections 167 and 129, BGB Section 311b, HGB Section 12

## Goal

Prepare a notary-office usecase package for notarized or publicly certified
powers of attorney used in real-estate contracts, company-register filings,
shareholder meetings or share transfers. The workflow must control scope, form,
limitations, original/copy handling and evidence.

## Scope

- Intake for principal, agent, transaction scope, form requirement,
  limitations, self-dealing release, substitution and expiry.
- Form decision: notarial deed, public certification or electronic
  certification.
- Delivery and copy control for originals and certified copies.

## Out of Scope

- No generic blanket power without scope review.
- No real identity documents, signatures or transaction documents in Git.
- No assumption that one form works for all target transactions.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `principal.identity` | Who grants the power and is capacity verified? | Notary | Personal or company data |
| `agent.identity` | Who is authorized and are conflicts present? | Principal | Personal data |
| `transaction.scope` | Which real-estate or company acts are covered? | Notary | Mandate metadata |
| `form.requirement` | Is public certification enough or is a deed required? | Notary | Legal metadata |
| `limitations.expiry` | Which limits, self-dealing, substitution or expiry rules apply? | Notary | Mandate metadata |
| `delivery.evidence` | Who receives originals or certified copies? | Notary clerk | Mandate metadata |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Power of attorney deed/certification | Core instrument. | Synthetic or metadata only. |
| Transaction scope reference | Explains target use. | Evidence reference only. |
| Identity and capacity evidence | Supports review. | Evidence reference only. |
| Copy and delivery trace | Controls originals/certified copies. | Metadata only. |

## Decisions

- Notarial deed, public certification, electronic certification or blocked.
- Scope type: real estate, company register, shareholder resolution, share
  transfer or mixed.
- Whether self-dealing or substitution is allowed.
- Whether original must remain controlled by the notary office.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Principal identity and capacity reviewed | Notary | Execution |
| Form and scope reviewed | Notary | Draft release |
| Limitations and self-dealing reviewed | Notary | Execution |
| Original and copy handling controlled | Notary clerk | Closing |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Guardrails and evidence model. |
| `noc-idaas` | Identity support where permitted. |
| `noc-grundbuch-portal` | Real-estate scope context where needed. |
| `noc-bnotk-xnp` | Electronic/register route readiness. |

## Delivery Tasks

1. Define scope-specific power-of-attorney intake schema.
2. Add form requirement decision model.
3. Add self-dealing/substitution checklist.
4. Add copy/original control state model.
5. Validate with synthetic real-estate and company fixtures.

## Acceptance Criteria

- Form route is explicit before execution.
- Scope cannot remain generic for register or real-estate transactions.
- Original/copy handling is tracked.
- No real identity or transaction data is committed.

