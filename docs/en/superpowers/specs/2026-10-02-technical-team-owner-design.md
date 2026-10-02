# Technical Team owner instead of ordinary-user owners

Status: Owner clarification dated 2026-10-02; local implementation authorized.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: technical-team-owner-766
leading_issue: https://github.com/notariat8/NaC/issues/766
risk_gate: Policy
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-10-02-technical-team-owner.md
acceptance_ids:
  - AC-OWNER-01
  - AC-OWNER-02
  - AC-OWNER-03
  - AC-OWNER-04
  - AC-OWNER-05
validation_commands:
  - python -m unittest tests.test_m365_technical_team_owner tests.test_teams_sharepoint_graph_data_plane tests.test_customer_tenant_onboarding
  - python scripts/validate_teams_sharepoint_graph_data_plane.py
  - python scripts/validate_governance_sync.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_spec_traceability.py
  - python scripts/nac.py doctor --profile strict
```

## Objective and boundary

The technical user account exactly bound in the
[Team ownership policy](../../../../policies/m365-team-ownership-policy.json) is the sole Team owner of
Teams created by NaC. Ordinary users sign in individually and are members
only. “Application User” means a technical user here, not OAuth app-only.
Delegated technical administration, application runtime and notarial approval
remain separate.

## Acceptance criteria

- AC-OWNER-01: The offline creation plan includes exactly one explicit
  technical owner and no implicit ownership for the calling ordinary user.
  Ordinary users must not receive the owner role.
- AC-OWNER-02: Technical Team ownership grants neither notarial qualifications,
  NaC/business matter authorization nor a second natural principal. The delegated administrative
  proof through `GET /me` remains required.
- AC-OWNER-03: Before the first write, group owners and Teams owners must match
  the exactly resolved technical user. Missing, additional, wrongly bound or
  duplicate, non-user, malformed or paginated ownership data stops fail-closed;
  continuation pages are never requested. There is no automatic owner
  migration or removal.
- AC-OWNER-04: Historical applied evidence is unchanged. Old ordinary-user
  ownership records do not prove compliance with the new model. Missing
  current evidence remains explicitly unverified.
- AC-OWNER-05: Policy, contract, configuration, code, negative tests, DE/EN
  documentation and Codex/pi rule mirrors are validated together.

This correction performs no Microsoft read, login, token renewal, tenant
mutation, application permission change, deployment or live acceptance.
License/terms review, principal gates, Sites.Selected and matter permissions
remain unchanged. Existing Teams require a separate mutation task.
Microsoft platform-owner capabilities are not claimed to disappear.
Customer approval of role assignments and DPA boundaries remain required.
