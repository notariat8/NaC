# Q2O Protected Start Status Activation

Status: owner-approved design, protected PR implementation.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: q2o-protected-start-status-activation
leading_issue: https://github.com/notariat8/NaC/issues/166
risk_gate: Identity and Session
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
validation_commands:
  - /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_auth_callback_sets_secure_session_cookie_after_verified_role_gate tests.test_nac_web.NaCLocalWebTests.test_auth_callback_keeps_protected_startstatus_closed_without_session_cookie tests.test_nac_web.NaCLocalWebTests.test_workspace_opens_protected_start_page_with_valid_session_cookie_only tests.test_oci_functions_adapter.OCIFunctionsAdapterTests.test_dispatches_workspace_as_protected_stateful_get_route
  - /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py
```

Owner approval:

> Q2O Ansatz A: after Q2N callback-log evidence is complete, enable only the protected notariat8 start/status page for verified server-side sessions; no full workspace, no mandate data, fail-closed, protected PR, release gate first, no OCI writes without separate Owner Apply Approval.

## Boundary

Q2O activates only the transition to the protected notariat8 start/status page
after successful server-side login. Activation requires a signed session cookie
issued only after valid state, server-side token exchange, verified claims, and a
positive notariat8 role gate.

This slice does not open:

- the full workspace,
- mandate data,
- token, claim, nonce, callback, provider, secret, or cookie values,
- OCI write operations.

If the session cookie is missing or cannot be validated, the start status stays
closed.

## Acceptance

- AC-001: The auth callback shows "Startstatus freigegeben" when the session is bound.
- AC-002: The auth callback offers a `/workspace` link when the session is bound.
- AC-003: Without a bound session, the start status stays closed and `/workspace`
  is not offered.
- AC-004: The pages explicitly state that no mandate data is loaded.
