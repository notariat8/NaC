# OIDC State And Log Boundary

Status: 2026-06-16.

## Purpose

The login callback must not count as a login before `state`, token response,
session, and the notariat8 role gate have been checked. `state` is not matter
data, but it is security-relevant callback data. It must not appear in
customer-facing text, reports, debug output, or broadly accessible logs.

## State Contract

NaC defines the `nac.oidc-state/v0.1` contract for signed, expiring state
values:

- Status `valid`: signature and expiry are valid; the tenant hint remains
  context only.
- Status `invalid`: format or signature do not match.
- Status `expired`: signature matches, but the state value has expired.
- Status `not_configured`: there is no reviewed server-side signing-key path
  yet.

Even with `valid`, the workspace stays closed. The next step is token exchange,
and only after that may the notariat8 role and case gate decide access.

If state validation is marked as configured but no validated state result is
available, the callback must fail closed. A configuration marker alone does not
count as successful validation.

## Token Exchange Adapter

NaC provides a server-side token exchange adapter that exchanges the
authorization code only on the server side. The adapter is fail-closed: without
complete metadata, a client secret, and an ID-token verifier, it does not start
an HTTP call. Provider failures, access tokens, refresh tokens, and ID tokens
are not copied into browser-facing results. Successfully verified claims may
only be forwarded as internal input for the notariat8 role gate.

Q2I still does not open a workspace, but it may issue a short-lived, signed
session cookie after valid state, successful token exchange, verified claims,
and a positive notariat8 role gate. The cookie contains no tokens, claims,
nonces, provider details, or callback values. Productive operation additionally
needs the reviewed secret path and server-side ID-token signature verification.

Q2G wires the stateful callback to this adapter, but it still does not open a
workspace. The callback reads the
Vault-backed client-secret path only when `state` is valid, `code`,
redirect URI, token endpoint, and client ID are complete, and a server-side
ID-token verifier is configured. If one of these conditions is missing, the
path stays closed and no productive workspace is opened.

Q2H makes the claim boundary explicit: successfully verified claims may be
forwarded internally to the notariat8 role gate. Browser-facing results only
show whether claims were verified and handed to the role gate. Email
addresses, group lists, tokens, nonces, provider details, and callback values
stay out of customer-facing text, reports, and ordinary logs. Even with a
confirmed role, this slice does not open a workspace; Q2I only adds the signed
session boundary.

Q2J validates the signed session cookie server-side and may open only a
protected notariat8 start/status page. Missing, tampered, expired, or
unconfigured cookies fail closed. The validation result exposes no cookie
value, token, claim, nonce, provider detail, or callback value. The full
workspace and all mandate data remain closed.

## Current OCI Finding

Read-only checked on 2026-06-09:

- The `nac-dev-nac-app` API Gateway deployment has no logging policies on the
  deployment or route level.
- The only active log group in the `nac-dev` compartment is the DevOps service
  log group: `nac-dev-devops-logs`.
- No API Gateway or Functions access-log group was found for the public app
  edge.
- The local NaC web server redacts `/auth/callback` queries in its request
  logs.

This is a point-in-time finding, not a permanent approval. If API Gateway,
Function, proxy, or CDN access logs are enabled, NaC must first prove that
`code` and `state` are not stored as query strings.

## Next Boundary

Before productive token exchange on the live route, one of these variants is
required:

1. Evidence that every involved log path redacts callback queries or does not
   store them.
2. Move the callback to a suitable POST edge, for example a separately reviewed
   `response_mode=form_post` path.
3. Reviewed secret/key path for state signing before the live route may treat
   real state validation as configured.

Both variants need their own Protected PR. If this changes API Gateway routes,
logging policies, or secret access, the apply also needs explicit owner
approval.
