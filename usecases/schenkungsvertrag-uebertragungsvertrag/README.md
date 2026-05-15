# Schenkungsvertrag / Uebertragungsvertrag

Status: KG baseline  
KG node: `case.schenkungsvertrag_uebertragung`  
Primary source anchors: BeurkG, BGB Sections 518 and 311b, GBO

## Goal

Prepare a notary-office usecase package for gift and transfer agreements,
especially family real-estate transfers and anticipated succession. The package
must capture asset, parties, reserved rights, reversion, obligations, approvals,
tax flags and land-register execution metadata.

## Scope

- Intake for transferor, transferee, transferred asset, consideration,
  reserved rights, reversion rights, approvals and tax/family flags.
- Draft support for gift, mixed gift or transfer with obligations.
- Land-register, tax notification and follow-up evidence references.

## Out of Scope

- No tax advice as automated truth.
- No real family, asset, value or property data in Git.
- No filing before ownership and reserved rights are reviewed.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `transferor.identity` | Who transfers and are identity, capacity and ownership verified? | Notary clerk | Personal data |
| `transferee.identity` | Who receives and what family or tax relation is relevant? | Notary clerk | Personal or family data |
| `asset.identity` | Which property, share, business interest or asset is transferred? | Notary clerk | Property or financial data |
| `reserved.rights` | Are usufruct, residential, care or usage rights reserved? | Notary | Family or financial data |
| `reversion.rights` | Which retransfer events, revocation grounds or notices apply? | Notary | Sensitive legal data |
| `consideration.obligations` | Is the transfer gratuitous, mixed or obligation-based? | Notary | Financial data |
| `consents.approvals` | Which spouse, court, bank or public approvals are needed? | Notary clerk | Mandate metadata |
| `tax.family.flags` | Which gift tax, succession or mandatory-share flags apply? | Notary | Sensitive family-financial data |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Transfer agreement draft | Human-reviewed deed. | Synthetic or metadata only. |
| Land-register excerpt | Ownership and rights review for real estate. | Evidence reference only. |
| Approval and consent evidence | Tracks spouse, court, administrator, bank or public approvals. | External reviewed evidence store. |
| Tax and filing trace | Tracks notifications and execution. | Metadata only. |

## Decisions

- Transfer type: gift, mixed gift or transfer with obligations.
- Reserved rights: none, usufruct, residential right, reversion, mixed.
- Whether care, maintenance or equalization obligations are included.
- Whether family/tax flags require specialist review.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Asset and ownership review | Notary | Draft release |
| Reserved rights and reversion review | Notary | Execution |
| Family, tax and succession flags reviewed | Notary | Closing decision |
| Filing and tax notification package ready | Notary clerk | Post-execution |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Regulated workflow and evidence model. |
| `noc-grundbuch-portal` | Land-register readiness for real-estate transfers. |

## Delivery Tasks

1. Define transfer-intake schema with asset-type branches.
2. Add reserved-rights and reversion decision model.
3. Add approval and consent checklist.
4. Add land-register and tax-notification evidence model.
5. Validate with synthetic family-transfer fixtures.

## Acceptance Criteria

- Ownership and asset review block draft release until complete.
- Reserved rights are explicit and evidenced.
- Tax and family flags cannot be silently ignored.
- No real asset values or family details are committed.

