# M365 Site Permission Boundary

Status: offline safety rework for a protected PR
Date: 19 July 2026
Scope: separation of SharePoint schema provisioning, site-permission administration, and runtime access

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-site-permission-boundary-671
leading_issue: https://github.com/notariat8/NaC/issues/671
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-07-19-m365-site-permission-boundary.md
review_gates:
  - External Service
  - Human Approval
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
  - AC-005
  - AC-006
validation_commands:
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_azure_activation_provisioner_bootstrap tests.test_nac_bff_azure_activation_owner_gate tests.test_nac_bff_azure_activation tests.test_m365_azure_bff_live_activation_contract tests.test_teams_sharepoint_graph_data_plane tests.test_nac_bff_graph_activation
  - PYTHONPATH=src python3 scripts/validate_m365_azure_bff_live_activation.py
  - PYTHONPATH=src python3 scripts/validate_teams_sharepoint_graph_data_plane.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```


## Acceptance

- AC-001: The provisioning app contract additionally requires `Sites.FullControl.All` for site-permission administration.
- AC-002: The runtime app and BFF UAMI remain restricted to exactly `Sites.Selected` and site role `read`.
- AC-003: The state validator and read-only pre-write inventory require the exact existing provisioning client ID plus the exact six-role allowlist and block a missing or replacement app, duplicate or broader roles, or effectively unusable permissions before the first provider write.
- AC-004: DE/EN architecture and runbook document the existing app, app-ID-bound CLI command, and separate owner gate.
- AC-005: Focused negative tests, contract validators, and the strict gate must pass.
- AC-006: This slice changes neither Entra nor tenant state, consent, credentials, or live runtime.

## Decision

The owner-gated `NaC M365 Provisioning` app retains
`Sites.Manage.All` for lists and columns and additionally requires
`Sites.FullControl.All` in the target contract exclusively for `GET`
and `POST` on `/sites/{siteId}/permissions`. This permission is
tenant-wide and must not move into a runtime identity.

The BFF UAMI remains restricted to exactly the Microsoft Graph application
role `Sites.Selected` and target-site grant `read`. This offline
rework does not rewrite the general NaC runtime app or historical tenant
snapshots.

## Fail-Closed Boundary

Before creating the live factory, the hash-bound local provisioner state must
contain exactly the six allowlisted Graph application roles. It includes exactly
one `Sites.FullControl.All` assignment and accepts only `created` or
`existing` status values. Missing FullControl returns
`PROVISIONER_SITE_PERMISSION_GRAPH_ROLE_MISSING`; a duplicate, missing, or
additional role returns `PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH`. Both stop
without provider access or tenant write.

## Excluded

This PR assigns no Entra permission, grants no admin consent, changes no
credential, performs no live retry, and changes no historical applied-state
artifact.
