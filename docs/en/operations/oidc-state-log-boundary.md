# OIDC State And Log Boundary

Status: 2026-06-09.

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

Before productive token exchange, one of these variants is required:

1. Evidence that every involved log path redacts callback queries or does not
   store them.
2. Move the callback to a suitable POST edge, for example a separately reviewed
   `response_mode=form_post` path.
3. Reviewed secret/key path for state signing before the live route may treat
   real state validation as configured.

Both variants need their own Protected PR. If this changes API Gateway routes,
logging policies, or secret access, the apply also needs explicit owner
approval.
