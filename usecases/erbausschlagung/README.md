# Erbausschlagung

Status: KG baseline  
KG node: `case.erbausschlagung`  
Primary source anchors: BeurkG, BGB Section 1945

## Goal

Prepare a notary-office usecase package for inheritance renunciation
declarations. The workflow must keep deadline risk, identity, capacity,
minor/guardian flags, court route and delivery evidence visible and reviewable.

## Scope

- Intake for decedent, estate court, renouncer, heirship basis and deadline.
- Publicly certified or recorded declaration package.
- Approval checks for minors, guardianship or representation.
- Delivery trace to estate court.

## Out of Scope

- No automated legal advice on accepting or rejecting an inheritance.
- No real family, estate or court documents in Git.
- No deadline assumption without notarial review.

## Required Information Nodes

| Node | Open question | Owner | Privacy class |
| --- | --- | --- | --- |
| `decedent.identity` | Who died and which estate court is competent? | Applicant | Personal data |
| `renouncer.identity` | Who renounces and is capacity verified? | Notary | Personal data |
| `deadline.status` | When did knowledge start and is the deadline open? | Notary | Sensitive process data |
| `heirship.basis` | Why is the person called as heir? | Applicant | Family data |
| `representation.minors` | Are minors, guardians or approvals involved? | Notary | Sensitive family data |
| `delivery.route` | How will the declaration reach the estate court? | Notary clerk | Mandate metadata |

## Documents and Evidence

| Artifact | Purpose | Storage rule |
| --- | --- | --- |
| Renunciation declaration | Core notarial declaration. | Metadata or synthetic only. |
| Death/court reference | Identifies estate proceeding. | Evidence reference only. |
| Approval evidence | Supports minor/guardian cases. | Evidence reference only. |
| Delivery trace | Shows court delivery. | Metadata only. |

## Decisions

- Deadline risk: low, urgent, expired/unclear or unknown.
- Approval needed: yes, no, already available or blocked.
- Declaration before notary or court route.
- Whether substitute heirs or follow-up declarations are triggered.

## Gates

| Gate | Review owner | Blocks |
| --- | --- | --- |
| Deadline reviewed | Notary | Declaration release |
| Identity and capacity reviewed | Notary | Execution |
| Approval status reviewed | Notary | Court delivery |
| Court delivery completed | Notary clerk | Closing |

## Plugin Dependencies

| Plugin | Purpose |
| --- | --- |
| `noc-regulated-core` | Sensitive estate workflow guardrails. |
| `noc-idaas` | Identity support where permitted. |

## Delivery Tasks

1. Build renunciation intake schema.
2. Add deadline-risk checklist.
3. Add minor/guardian approval branch.
4. Add court delivery state model.
5. Validate with synthetic estate fixtures.

## Acceptance Criteria

- Deadline status must be explicit.
- Minor/guardian flags block closing until reviewed.
- Delivery evidence is captured.
- No real estate or family data is committed.

