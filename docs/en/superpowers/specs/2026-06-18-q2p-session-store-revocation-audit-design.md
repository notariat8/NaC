# Q2P Session Store, Revocation, and Audit

Status: owner-approved design, protected PR implementation.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: q2p-session-store-revocation-audit
leading_issue: https://github.com/notariat8/NaC/issues/165
risk_gate: Identity and Session
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
validation_commands:
  - /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_contract_declares_dry_run_only_boundary tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_session_cookie_validation_requires_active_server_session_record_when_store_is_supplied tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_session_cookie_validation_fails_closed_when_server_session_is_missing_revoked_or_expired
  - /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py
```

**Goal:** Before any future full workspace or matter access, notariat8 must have a server-side session control. The browser cookie remains short-lived and contains no tokens, claims, provider details, or callback values.

## Design

Q2P extends the existing OIDC session boundary with an optional server-side session-store contract. The existing cookie validation remains compatible for the protected start status. Once a session store is supplied to validation, a correctly signed cookie is no longer sufficient on its own: an active store record is required.

A store record may contain only safe session metadata: session ID, issued time, expiry time, optional revocation time, and an audit reference. Tokens, claims, provider details, callback values, and matter data are excluded. Missing, revoked, expired, or unsafe store records fail closed.

The audit boundary records only status, reason, check time, and an optional audit reference. It does not expose the session ID, cookie value, tokens, claims, or email addresses.

## Security Rules

- The browser cookie remains a signed, short-lived pointer.
- The server-side session store is required before full workspace or matter access is activated.
- Store-side revocation closes the session immediately.
- Audit events are redacted and contain no sensitive values.
- Q2P does not load matter data.

## Acceptance

- AC-001: When a session store is supplied, a signed cookie is accepted only with an active store record.
- AC-002: Missing, revoked, and expired store records fail closed.
- AC-003: Store and audit results expose no session ID, cookies, tokens, claims, roles, or email addresses.
- AC-004: The existing protected start status remains backward compatible without a store adapter.
