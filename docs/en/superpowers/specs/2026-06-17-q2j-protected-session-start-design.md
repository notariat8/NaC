# Q2J Protected Session Start Page

Status: owner-approved design, protected PR implementation.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: q2j-protected-session-start-page
leading_issue: https://github.com/notariat8/NaC/issues/153
risk_gate: Identity and Session
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
validation_commands:
  - /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_session_cookie_validation_allows_protected_start_page_without_opening_workspace tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_session_cookie_validation_fails_closed_for_tampered_or_expired_cookie tests.test_nac_web.NaCLocalWebTests.test_workspace_requires_signed_session_cookie tests.test_nac_web.NaCLocalWebTests.test_workspace_opens_protected_start_page_with_valid_session_cookie_only tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_dispatches_workspace_as_protected_stateful_get_route tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_dispatches_workspace_fail_closed_without_cookie
  - /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py
```

Owner approval:

> Q2J Ansatz A: validate signed server-side session cookie and open a protected notariat8 start/status page only, no mandate data, no full workspace, fail-closed, protected PR, no OCI writes.

## Boundary

Q2J validates the signed `__Host-nac_session` cookie issued after valid state,
server-side token exchange, verified claims, and a positive notariat8 role gate.
A valid cookie may open only `/workspace` as a protected start/status page.

This slice does not:

- load mandate data,
- open the full workspace,
- expose tokens, claims, nonces, callback values, provider details, or cookie
  values,
- perform OCI writes.

Missing, tampered, expired, or unconfigured cookies fail closed.

## Acceptance

- AC-001: Missing session cookie returns a login-required page.
- AC-002: Valid session cookie returns a protected notariat8 start/status page.
- AC-003: The result contains no token, claim, nonce, callback, provider, secret, or raw
  cookie values.
- AC-004: The page states that no mandate data is loaded.
