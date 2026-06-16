# Q2H Claim Boundary And Role-Gate Contract

Status: approved for Issue #147.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: q2h-claim-boundary-role-gate-contract
leading_issue: https://github.com/notariat8/NaC/issues/147
risk_gate: Identity and Session
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
validation_commands:
  - /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_auth_callback_result_marks_verified_claims_forwarded_to_role_gate_without_exposure tests.test_nac_web.NaCLocalWebTests.test_auth_callback_shows_role_gate_confirmed_without_opening_workspace
  - /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py
```

## Goal

Q2H makes the internal boundary between server-side verified OIDC claims and
the notariat8 role gate explicit. The callback may forward verified claims only
internally to the role gate. Browser-facing results must not contain claims,
tokens, nonces, provider details, secret references, or callback values.

## Scope

- `nac.oidc-claim-boundary/v0.1` as a redacted contract slice.
- The role-gate decision stays fail-closed for missing, incomplete, or
  unverified claims.
- The callback page may show that the role check was confirmed.
- No session cookie, no workspace opening, and no mandate data in this slice.

## Explicitly Out Of Scope

- No OCI write action.
- No live test with real user credentials.
- No productive session activation.
- No opening of a protected workspace.

## Acceptance

- AC-001: The auth callback contract contains a redacted
  `nac.oidc-claim-boundary/v0.1` section.
- AC-002: Verified claims are marked as internally forwarded to the role gate
  without exposing claim or token values in public results.
- AC-003: The role gate stays closed when claims are missing, incomplete, or
  unverified.
- AC-004: The callback page may show a confirmed role check, but it does not
  open a workspace or set a session cookie.
