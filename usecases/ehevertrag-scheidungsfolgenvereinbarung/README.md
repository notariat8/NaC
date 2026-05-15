# Ehevertrag / Scheidungsfolgenvereinbarung

Status: KG baseline  
KG node: `case.ehevertrag_scheidungsfolgen`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)
Primary source anchors: BeurkG, BGB Section 1410, Versorgungsausgleich context

## Goal

Prepare a notary-office usecase package for marriage contracts and divorce
consequence agreements. The workflow must capture spouses, context, property
regime, asset categories, maintenance, pension equalization, child/family flags,
asset transfers and fairness-review evidence.

## Scope

- Intake for spouses, marriage or divorce context, property regime, asset and
  debt categories, maintenance, pension equalization and transfers.
- Draft support for pre-marriage, in-marriage and divorce-consequence variants.
- Fairness, imbalance and simultaneous-presence review gates.

## Out of Scope

- No automated family-law fairness decision as final truth.
- No real asset schedules, child data, health data or private addresses in Git.
- No court filing or register follow-up without reviewed connector.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `spouses.identity` | Who are the spouses or intended spouses? | Notary clerk | Personal data |
| `marriage.context` | Is this pre-marriage, during marriage, separation or divorce? | Notary | Family data |
| `property.regime` | Should statutory property regime be modified or replaced? | Notary | Financial data |
| `asset.disclosure` | Which asset categories, debts, businesses or pensions are relevant? | Spouses | Financial data |
| `maintenance.rules` | Which maintenance provisions or waivers are intended? | Notary | Sensitive family-financial data |
| `pension.equalization` | Should pension equalization be modified? | Notary | Financial data |
| `child.family.flags` | Are child-care, dependency, pregnancy or imbalance flags relevant? | Notary | Sensitive family data |
| `asset.transfer` | Are real estate, shares, accounts or debt transfers included? | Notary clerk | Financial or property data |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Agreement draft | Human-reviewed deed. | Synthetic or metadata only. |
| Asset schedule reference | Supports fairness review without storing details. | Evidence reference only. |
| Fairness review notes | Documents review gate and warnings. | Evidence reference only. |
| Execution and follow-up trace | Tracks signature, copies and register steps. | Metadata only. |

## Decisions

- Instrument type: pre-marriage, marriage contract or divorce consequences.
- Fairness and imbalance risk: low, medium, high, blocked or unknown.
- Whether pension equalization, maintenance or property transfers require
  specialist review.
- Whether real-estate or company-share transfer creates additional usecase
  dependencies.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Identity and personal status checked | Notary clerk | Appointment |
| Simultaneous presence route checked | Notary clerk | Execution |
| Fairness and imbalance review completed | Notary | Draft release |
| Asset transfer side effects reviewed | Notary | Closing and follow-up |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Sensitive family workflow guardrails. |
| `noc-idaas` | Identity support where permitted. |
| `noc-grundbuch-portal` | Land-register review if real estate transfer is included. |

## Delivery Tasks

1. Define intake schema for spouse, property and family-law context.
2. Add fairness and imbalance red-flag checklist.
3. Add optional asset-transfer branch into property/register workflows.
4. Add evidence model for asset schedules and review notes.
5. Validate with synthetic spouse and asset-category fixtures.

## Acceptance Criteria

- Fairness review blocks draft release where risk is unknown or high.
- Asset categories are referenced, not stored with real values.
- Simultaneous-presence route is explicit.
- Side effects into real-estate or company-share transfers are visible.

