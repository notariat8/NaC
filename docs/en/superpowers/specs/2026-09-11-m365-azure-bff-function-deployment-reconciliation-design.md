# Azure BFF Step-7 Reconciliation

Status: `IMPLEMENTED_OFFLINE`

Date: 11 September 2026
Leading issue: [#739](https://github.com/notariat8/NaC/issues/739)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-azure-bff-function-deployment-reconciliation
leading_issue: https://github.com/notariat8/NaC/issues/739
risk_gate: Human Approval
delivery_mode: Owner Direct
plan: docs/en/superpowers/plans/2026-09-11-m365-azure-bff-function-deployment-reconciliation.md
review_gates:
  - Human Approval
  - Security
acceptance_ids:
  - AC-739-R1
  - AC-739-R2
  - AC-739-R3
  - AC-739-R4
  - AC-739-R5
  - AC-739-R6
validation_commands:
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_cli
  - python3 scripts/validate_m365_azure_bff_live_activation.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Problem

The bound live run for `notary_team_01` terminated at step 7 with
`AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS`. The generic finalization recovery
deliberately cannot resolve this provider state. The `target`, `legacy`, and
`legacy_host` journals therefore remain `HELD`, although read-only ARM data now
shows that the deployment was not applied.

## Decision

A separate central `nac` command handles only this exact shape. Inspection
validates state, evidence, all 18 ledger events, the prepared manifest, Function
ZIP, and every lock journal. It performs two identical Azure snapshots through
fixed GET URLs for exactly `func-nac-bff-test-funktion8`. Only a site timestamp
before the failed step, no newer deployment activity, an empty
`deploymentStatus` list, and an absent OneDeploy status classify as
`FUNCTION_DEPLOYMENT_NOT_APPLIED`.

Inspection performs no mutation. Lock release requires a new immutable owner
comment on Issue #739 binding every artifact, lock, provider, commit, tree, and
toolchain hash. Those bindings are revalidated before every local mutation. The
reconciler crash-safely appends only `RELEASED` to all three journals; the old
state, evidence, ledger, and Azure remain unchanged.

## Acceptance Criteria

- **AC-739-R1:** Only the exact terminal step-7 state with six passed steps, 18 valid ledger events, and the ambiguity code is eligible.
- **AC-739-R2:** Two equal allowlist-bound ARM snapshots prove `FUNCTION_DEPLOYMENT_NOT_APPLIED`; any positive, missing, or drifting signal blocks.
- **AC-739-R3:** Owner-free inspection changes no local file and performs no provider write.
- **AC-739-R4:** Release requires the exact new #739 approval by `ofunk` and every emitted hash binding.
- **AC-739-R5:** Release changes neither historical state nor evidence, ledger, or Azure and append-only releases all three journals.
- **AC-739-R6:** Crashes after a journal append are idempotently recoverable with the same approval; unknown tails or binding drift fail closed.

## Non-Goals

No old-run resume, retroactive `PASSED`, Azure deployment, rollback, deletion,
or extension to other steps or apps.
