# IDaaS Plugin Integration

## Purpose

This plan migrates `ofunk/IDaaS` into the NoC plugin `noc-idaas`.
The plugin is a local companion for German eID verification, minimal claim
sets, consent and audit evidence, and IAM projection planning.

## Day0

- Clarify the verification purpose.
- Determine tenant, customer application, target IAM, and review owner.
- Minimize the claim set.
- Document privacy basis, DPA need, retention, and audit requirements.
- Classify the channel as public GPT Store, GPT with Actions, workspace app, or
  local Codex plugin.

## Day1

- Produce a plan preview for the eID flow and optional IAM projection.
- Check AusweisApp, redirect, webhook or polling, consent, and evidence
  assumptions.
- Dry-run OpenAPI and event contracts.
- Request human approval before processing real personal data or writing target
  systems.

## Day2

- Review expired assertions, revocations, and failed projections.
- Surface retention drift and purpose-binding deviations.
- Recertify connectors, mapping profiles, and reviewer ownership.

## Safety Boundaries

- No real eID raw data, identity-document dumps, tokens, certificates, or
  credentials in the repository.
- No IAM write without reviewed connector and approval.
- No personal-data processing without a documented basis.
- Evidence is metadata-only by default.
