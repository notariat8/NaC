# Positioning: Notariat As Code And Enterprise GitOps

## Goal

This document defines the project terminology:

- `NaC` is the concrete product and operating implementation in this
  repository.
- The overarching architecture model is `Notariat as Code`.
- The operational control principle is `Enterprise GitOps`.

## Terminology

### Notariat As Code

Notarial operations are described declaratively and versioned:

- policies,
- roles and permissions,
- process models,
- control points,
- evidence.

### Enterprise GitOps

Changes to organizational and notarial process logic are controlled through:

- branches,
- pull requests,
- review and approval,
- automated policy and compliance checks.

### NaC

`NaC` is the concrete implementation of Notariat as Code plus Enterprise GitOps
in this repository.

## Why The Separation Matters

- It reduces misunderstandings between tooling and target model.
- It makes the model easier to review for notary-office users, auditors and
  operations owners.
- It supports third-party operation and replaceability without terminology
  conflicts.

## AI-native Positioning

NaC is not "AI-assisted notarial work" where a chatbot merely accelerates
individual steps. NaC is an AI-native operating model for regulated notarial
work: case types, roles, approvals, control points and evidence are structured so
agents can assist without replacing subject-matter truth or notarial
responsibility.

The discipline does not sit in the model alone, but in the NaC harness of
versioned knowledge, guides and sensors. Guides constrain data, roles, tools and
allowed actions. Sensors check schema, policy, privacy, subject-matter
consistency, review state and evidence readiness. Agent knowledge therefore does
not live in the chat history, but in checkable files: policies, roles, skills,
process models, knowledge graphs, contracts, validators and approvals.

The human role therefore does not move toward blind delegation. It moves toward
qualified direction: clarifying the work order, setting boundaries, checking
results, feeding deviations back into the system and owning approvals.

This positioning uses current AI-native operating language as a NaC-specific,
regulated formulation. It is not a delegation of subject-matter or notarial
responsibility to a model.

## Architecture Mapping

- `Intent Layer`: policies, roles, process definitions.
- `Control Layer`: pull requests, reviews, approvals, rulesets.
- `Execution Layer`: runtime, automation, process execution.
- `Evidence Layer`: audit-proof event journal.

## Project Decision

This repository maintains the positioning as an active project decision. The
following terms are the binding terminology for NaC.

Term:

- `Notariat as Code`

Platform name:

- `Enterprise Control Plane`

First product promise:

- "Notarial case types, plugins, workflows, roles, approvals and evidence run
  declaratively, auditable and automated through Git."

The current development status is maintained in
[roadmap/BUILD_NOW.md](../../roadmap/BUILD_NOW.md).

## One-Sentence Pitch

Notariat as Code is an operating model in which notarial case types, plugins,
workflows, policies and operational changes are described declaratively in Git
and moved into verifiable execution through an Enterprise Control Plane.
