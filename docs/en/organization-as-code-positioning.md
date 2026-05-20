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
- It makes the model easier to review for business users, auditors and
  operations owners.
- It supports third-party operation and replaceability without terminology
  conflicts.

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
