# Teilungserklaerung nach WEG

Status: KG baseline  
KG node: `case.teilungserklaerung_weg`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, WEG Section 8, GBO

## Goal

Prepare a notary-office usecase package for division of a property into
apartment ownership or partial ownership. The package must connect owner
authority, unit structure, co-ownership shares, plans, certificates, community
rules, encumbrance handling and land-register implementation.

## Scope

- Intake for base property, owner, planned units, co-ownership shares and
  special-use rights.
- Review of plans, numbering, separation certificate and community rules.
- Handling of existing land-register encumbrances across future units.
- Filing trace for new apartment or partial-ownership registers.

## Out of Scope

- No technical plan verification by the LLM.
- No real plans, certificate files or owner data in Git.
- No automated land-register filing without reviewed connector.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `property.identity` | Which base land-register object will be divided? | Notary clerk | Property register data |
| `owner.identity` | Who owns and is authorized to divide? | Notary | Personal or company data |
| `unit.structure` | Which units, rooms and special-use areas are planned? | Client | Property metadata |
| `ownership.shares` | Which co-ownership fractions are assigned? | Client | Property metadata |
| `plans.certificates` | Are plans and separation certificate available and consistent? | Client | Property metadata |
| `encumbrance.handling` | How do existing rights affect the future unit registers? | Notary | Property register data |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Declaration of division | Core notarial declaration and community rules. | Synthetic or metadata only. |
| Plans and separation certificate | Supports land-register implementation. | Evidence reference only. |
| Land-register excerpt | Confirms property and encumbrances. | Evidence reference only. |
| Unit-register application trace | Tracks implementation. | Metadata only. |

## Decisions

- Residential, partial ownership or mixed division.
- Special-use rights included or not.
- Existing encumbrances stay global, are allocated or require consents.
- Whether corrections to plans/certificates are blocking.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Owner and base property reviewed | Notary | Draft release |
| Plans and certificate reviewed | Notary clerk | Filing |
| Encumbrance implementation reviewed | Notary | Land-register application |
| Unit-register package ready | Notary clerk | Submission |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Regulated workflow and evidence model. |
| `noc-grundbuch-portal` | Base property and encumbrance review. |
| `noc-bnotk-xnp` | Land-register filing route readiness. |

## Delivery Tasks

1. Define unit and co-ownership-share intake schema.
2. Add plan/certificate checklist.
3. Add encumbrance allocation review.
4. Add unit-register filing state model.
5. Validate with synthetic multi-unit fixtures.

## Acceptance Criteria

- Plans and certificate references are mandatory before filing.
- Encumbrances cannot be ignored.
- Unit structure and share totals must be internally complete.
- No real plans or owner data are committed.

