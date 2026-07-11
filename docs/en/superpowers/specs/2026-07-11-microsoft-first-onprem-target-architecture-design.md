# Microsoft-First, On-Prem AI Target Architecture

Status: planning decision; implementation follows in protected PR slices.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: microsoft-first-onprem-target-architecture
leading_issue: https://github.com/notariat8/NaC/issues/613
risk_gate: Architecture and Privacy
delivery_mode: Protected PR
acceptance_ids:
  - AC-613-01
  - AC-613-02
  - AC-613-03
  - AC-613-04
  - AC-613-05
  - AC-613-06
validation_commands:
  - python3 scripts/validate_microsoft_first_onprem_target_architecture.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/validate_gantt_progress.py
  - python3 scripts/nac.py doctor --profile strict
```

Plan:
[2026-07-11-microsoft-first-onprem-target-architecture.md](../plans/2026-07-11-microsoft-first-onprem-target-architecture.md)

## Problem

The M365 MVP decision is final, but UI, agentic runtime, durable workflow
execution, M365 adapter, persistence, local workstation and audit must not
collapse into a SharePoint-centered monolith. The supplied PDF provides a
useful baseline while leaving some technology options broader than NaC permits.

## Goal

The binding boundary is:

- Microsoft-first for Teams, SPFx, SharePoint, Entra and Graph REST v1.0/MCP.
- On-prem-first for Python/FastAPI, AI/models, deterministic workflow control
  plane, PostgreSQL, outbox/broker and WORM. Temporal and baseline modes are
  exclusive execution modes: Temporal History owns state/timers/retries in
  Temporal mode, while PostgreSQL additionally owns state/timers/leases/retries
  in baseline mode; WORM remains separate in both.
- NVIDIA NeMo Agent Toolkit as the only agentic toolkit.
- SharePoint as document/projection storage, not durable technical workflow truth.
- WSL sidecars as non-authoritative workstation adapters.
- Temporal only as a timeboxed, outcome-open durable-workflow candidate.

## Acceptance

- **AC-613-01:** Every relevant PDF recommendation is classified as Adopt,
  Adapt or Reject.
- **AC-613-02:** UI, BFF/access, workflow, personal agent, M365 adapter,
  persistence and audit are separated.
- **AC-613-03:** Graph-v1.0-/MCP-only, NeMo-only-agentic and on-prem AI are
  machine-readable guardrails.
- **AC-613-04:** SharePoint, PostgreSQL, workflow history, WORM, local cache and
  agent memory have unambiguous roles; authoritative technical execution truth
  is assigned exactly once for the selected mode.
- **AC-613-05:** 90/180/365-day roadmap, critical path, repository ownership,
  costs and open owner decisions are documented.
- **AC-613-06:** DE/EN mirrors, contract, validator, spec traceability,
  documentation links and Gantt validation pass.

## Boundaries

This slice changes no runtime, tenant configuration, Entra app, credentials,
deployment or live data. It does not finally select Temporal, a WORM provider
or an M365 license package.

