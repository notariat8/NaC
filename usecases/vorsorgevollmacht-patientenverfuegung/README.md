# Vorsorgevollmacht und Patientenverfuegung

Status: KG baseline  
KG node: `case.vorsorgevollmacht_patientenverfuegung`  
Primary source anchors: BeurkG, BGB care and patient-directive context

## Goal

Prepare a notary-office usecase package for precautionary powers of attorney,
health-care powers and patient directives. The workflow must capture principal,
agents, scope, effectiveness, health-care instructions, central register route
and copy handling.

## Scope

- Intake for principal identity, capacity, agents, substitutes, financial scope,
  health-care scope, patient directive wishes and effectiveness rules.
- Draft support for power of attorney and patient directive instruments.
- Copy, revocation and register evidence metadata.

## Out of Scope

- No medical advice or automated final wording decisions.
- No real health, care, family or address data in Git.
- No registration or copy distribution without reviewed instruction.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `principal.identity` | Who grants the power and how is capacity reviewed? | Notary | Personal data |
| `agent.identities` | Who should act as agent or substitute? | Principal | Personal data |
| `authority.financial` | Which financial, banking, property or business powers are intended? | Principal | Financial data |
| `authority.health` | Which health, care, residence and communication powers apply? | Principal | Health or sensitive data |
| `patient.directive` | Which treatment situations and wishes should be documented? | Principal | Health or sensitive data |
| `effectiveness.rules` | When can the power be used and how are copies handled? | Notary | Mandate metadata |
| `self_dealing.release` | Should self-dealing or sub-delegation be allowed? | Notary | Mandate metadata |
| `central_register` | Should central register registration be prepared? | Notary clerk | Personal data |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Power of attorney draft | Defines agent scope. | Synthetic or metadata only. |
| Patient directive draft | Captures reviewed health-care wishes. | Synthetic or metadata only. |
| Capacity and instruction reference | Supports notarial review. | Evidence reference only. |
| Copy and register trace | Tracks copies and central register state. | Metadata only. |

## Decisions

- Instrument scope: power only, patient directive only or combined.
- Register route: register, do not register, needs review or unknown.
- Agent model: single, joint, substitute or conditional powers.
- Whether financial/property powers need additional form or review.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Capacity and free-will review | Notary | Execution |
| Health-care and patient-directive wording reviewed | Notary | Draft release |
| Copy and revocation model confirmed | Notary clerk | Closing |
| Register route confirmed | Notary clerk | Post-execution |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Sensitive intake and evidence guardrails. |
| `noc-idaas` | Identity support where permitted. |

## Delivery Tasks

1. Create intake schema for power, health and patient-directive scopes.
2. Add capacity and health-sensitivity warning gates.
3. Add copy, revocation and register state model.
4. Add deterministic missing-information report.
5. Validate with synthetic principal and agent fixtures.

## Acceptance Criteria

- Principal identity and capacity gate are mandatory.
- Health-care scope cannot be completed without review.
- Register decision is explicit.
- No real health or family data is committed.

