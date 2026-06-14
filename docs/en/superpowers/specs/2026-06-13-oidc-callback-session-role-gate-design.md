# OIDC Callback, Session And NaC Role Gate

Date: 2026-06-13

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: oidc-callback-session-role-gate
leading_issue: https://github.com/notariat8/NaC/issues/128
risk_gate: Identity and Session
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
validation_commands:
  - env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter
  - env GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

## Context

The live `myjur` test confirmed the OIDC flow up to the return to
`/auth/callback`. Password reset, consent and redirect work. NaC then
intentionally shows only `Anmeldung empfangen`, because the workspace may open
only after server-side state, token, session and role validation.

The current state is therefore not an identity-provider defect. It is the next
product increment: the auth callback must move from a closed intermediate event
to a validated notariat8 session.

## Decision

Approach A is approved: `/auth/callback` belongs to the auth/stateful runtime.
The Public GET Function stays lean and as free of secrets as possible for public
pages and login-intent readiness. Token exchange, client-secret access, session
creation and the NaC role gate run server-side in the protected callback path.

## Goals

- `state` is validated server-side and expired or foreign values fail closed.
- The authorization code is exchanged for tokens only on the server.
- ID tokens are validated for issuer, audience, nonce and signature.
- NaC maps identity-domain groups or claims to its own roles.
- A protected workspace opens only after a positive role gate.
- Callback values, tokens and secrets never appear in browser text, logs,
  GitHub, Git or chat.

## Non-Goals

- No mandate data in this track.
- No generic user-management frontend.
- No migration of the whole Public GET Function to a secret-bearing runtime.
- No OCI write operation without a separate Owner Apply Gate.

## Architecture

The login-intent route remains public and creates the signed redirect context.
The callback is moved into a stateful/auth runtime. That runtime has access to
the necessary Vault references, not to plaintext secrets in Git or Function
configuration.

The callback handles only server-side work:

1. Receive the query and redact log output.
2. Validate `state` and treat `tenant_hint` only as context.
3. Exchange the code at the token endpoint.
4. Validate ID token and nonce.
5. Map groups/claims to NaC roles.
6. Set a session cookie with secure attributes.
7. Redirect to the workspace only when the required role is present.

## Role Model

For the first live test, `nac-tenant-admin` is the role anchor. An IdP login
alone is not sufficient. NaC accepts only a server-side verified role binding,
for example membership in `nac-tenant-admin`, before the workspace opens for
`myjur`.

`tenant_hint` remains non-authoritative. It helps with routing and display, but
does not create authorization.

## Security Rules

- Client secrets live only in OCI Vault or an equivalent secret store.
- Tokens are not persisted until an explicit session-store decision has been
  made.
- Session cookies are `HttpOnly`, `Secure` and `SameSite=Lax`.
- Error pages show no provider details, codes, states, nonces, tokens or secret
  references.
- Role-gate failures are closed: no workspace, no mandate data.

## Acceptance Criteria

- AC-001: The Public GET Function returns a closed `404` for `/auth/callback`
  and exposes neither `code` nor `state` in the response body.
- AC-002: The stateful NaC Function continues to serve `/auth/callback`, so
  token exchange, session creation and the role gate can be added there.
- AC-003: Callback values, tokens and secrets are not disclosed in public or
  stateful responses.

## Tests

The implementation needs tests for:

- valid callback with validated state, token response and matching role,
- invalid or expired state,
- token-exchange failure without secret leak,
- ID token with wrong issuer, wrong audience or wrong nonce,
- missing role despite successful IdP login,
- session cookie only after a positive role gate,
- protection against callback values in HTML and logs.

## Delivery

The code change is delivered through a protected PR. Separate gates follow:

1. Release Approval for the new NaC image.
2. Resource Manager plan without apply for route/Function configuration.
3. Owner Apply Approval for the callback route to the auth/stateful runtime and
   the Vault secret reference.
4. Live test with the synthetic `myjur` test account.
