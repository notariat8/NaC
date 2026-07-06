# NaC OCI Runtime (Archived)

Status since 2026-07-06: archived legacy path. The M365 MVP uses no OCI
Functions, no OCI API Gateway, no OCI DevOps, no ATP data plane and no
OCI-bound on-prem agent runtime. This document remains only as historical
operating and security reference if OCI is explicitly reactivated later. Active
storage and workspace integration run through Teams, SharePoint Team Site and
Microsoft Graph REST/MCP.

This document defines the first live OCI runtime contract for the NaC web app.
This is not a mandate-data environment. No mandate data, customer secrets, OCI
API keys, or tenant credentials are stored in this repository or in the systemd
unit.

Required apply gate:

`Owner Apply Approval for Apply Block G NaC runtime deployment`

The first runtime command is:

`nac-web --repo-root /opt/nac/current --host 0.0.0.0 --port 8768`

First live endpoints:

- `GET /healthz`
- `GET /admin/onboarding`

## OCI Functions Parallel Runtime

The next runtime stage is an OCI Functions Parallel Runtime behind OCI API
Gateway. It does not replace the VM immediately: the VM remains fallback until
the Functions path is confirmed by a live smoke test.

The first Functions adapter is GET/HEAD-only by default. It calls the same
`NaCLocalWebApp.handle(...)` contract as the local web server. Exactly one POST
exception is allowed for customer onboarding: `POST /onboarding/requests`.
This path accepts only the domain, tenant reference, and responsible email
address. The function package stores no mandate data, secrets, OCI API keys, or
tenant credentials.
After successful creation, the public path returns `303 See Other` with
`Location: /onboarding/requests/<request_id>?audience=customer`. That status
page is publicly readable through GET/HEAD and can be reloaded; the URL contains
no administration email and does not expose admin queue functions.

Required apply gate for the Functions parallel path:

`Owner Apply Approval for Apply Block J NaC OCI Functions parallel runtime`

## No-SSH Functions Release

For the cloud-native runtime, the target path is a No-SSH Functions Release. A
protected, merged GitHub commit is built by OCI DevOps, stored as a container
image in OCIR, and pinned by an OCIR digest. The OCI Function is updated to
that digest and then verified through an API Gateway smoke test.

The release is commit-bound: the OCI DevOps build run must pass the
owner-approved commit as the `NAC_RELEASE_COMMIT` build argument in addition to
`commit-info`. The build spec detaches the checkout to that commit and fails
fast if the commit is unavailable in the OCI mirror or if the active checkout
does not match. `commit-info` alone is audit metadata; it does not pin the build
checkout.

This path needs no Bastion or SSH access to the VM. The VM remains fallback
until the API Gateway path for `/healthz`, `/onboarding/readiness`,
`/onboarding/dns-check`, `/login`, and `/api/tenant/login-intent` is live-tested
and a separate Owner Apply gate approves cutover.

The Function release path remains GET/HEAD-only except for
`POST /onboarding/requests`; the reloadable customer page
`GET /onboarding/requests/<request_id>?audience=customer` is the matching
public read route after the redirect. Login-intent configuration comes only
from server-side environment values; query parameters must not set identity
domain, client, redirect, state, or nonce values.

## ATP Onboarding Request Store

The productive onboarding request store and server-side portal session store
are enabled only through explicit server-side gates:

- `NAC_ONBOARDING_STORE=atp`
- `NAC_SESSION_STORE=atp`
- `NAC_ATP_DSN`
- `NAC_ATP_USER`
- `NAC_ATP_PASSWORD_SECRET_OCID`
- `NAC_ATP_WALLET_OBJECT_STORAGE_NAMESPACE` for mTLS-required ATP
- `NAC_ATP_WALLET_BUCKET_NAME` for mTLS-required ATP
- `NAC_ATP_WALLET_OBJECT_NAME` for mTLS-required ATP
- `NAC_ATP_WALLET_PASSWORD_SECRET_OCID` for mTLS-required ATP

A plaintext password in `NAC_ATP_PASSWORD` does not enable any store. If any
required value is missing, affected routes remain fail-closed. Onboarding
returns `onboarding_request_store_disabled`; protected start pages remain
closed without an active server-side session record. The password value is read
at runtime from OCI Vault through Resource Principal; Git, chat, query
parameters, HTML, and Function config contain only the Secret OCID, never the
secret value.

For mTLS-required ATP, the wallet zip is read from a private Object Storage
bucket and extracted into the ephemeral Function filesystem. The wallet
password remains a separate Vault secret. The wallet contains credential
material, not mandate data. Its contents are not written to Git, chat, Resource
Manager variables, Function config, query parameters or HTML.
`NAC_ATP_WALLET_ZIP_SECRET_OCID` remains only as a compatibility path because a
real ATP wallet does not reliably fit into a single OCI Vault secret after
base64 encoding.

Optional wallet/network paths:

- `NAC_ATP_CONFIG_DIR`
- `NAC_ATP_WALLET_LOCATION`
- `NAC_ATP_WALLET_EXTRACT_DIR`

The ATP apply, table creation, and secret boundary remain a separate
Owner-gated infrastructure track through `notariat8/oci-landing-zone#44`. The
app adapter track is `notariat8/NaC#85`.

The versioned bootstrap artifact for the first tables is
[archive/legacy-oci-atp/deploy/database/atp-onboarding-request-store.sql](../../../archive/legacy-oci-atp/deploy/database/atp-onboarding-request-store.sql).
It creates `onboarding_requests` and `nac_sessions` with the current contract
fields. `nac_sessions` stores only hashed session IDs, tenant/user/usecase/
purpose bindings, and redacted audit metadata. Tokens, claims, credentials, and
mandate data are excluded by contract and schema guardrail. Running it belongs
into the Block M runbook step after the ATP target has been reviewed and before
the final live smoke for `POST /onboarding/requests` and the protected
`GET /workspace` start status.
The smoke test must also verify the `303` redirect and the reloadable GET status
page without `admin_email` in the URL.

## App Release Overlay

An ordinary NaC software release does not require VM replacement after the
initial runtime is stable. The standard path is an App Release Overlay: a
reviewed NaC commit is transferred to the private runtime as a checked archive with a
documented SHA-256, unpacked by [deploy/runtime/nac-web-release.sh](../../../deploy/runtime/nac-web-release.sh)
into `/opt/nac/releases/<commit>`, activated through `/opt/nac/current`, and
verified after a `nac-web` systemd restart.
The health check uses a short configurable wait window
(`NAC_RELEASE_HEALTH_ATTEMPTS`, `NAC_RELEASE_HEALTH_SLEEP_SECONDS`) so a
healthy process has time to bind its port after the restart. If the health
check still fails, the script performs a rollback by pointing
`/opt/nac/current` back to the previous target and restarting `nac-web` again.

Required apply gate for this app release path:

`Owner Apply Approval for Apply Block H NaC app release overlay`

VM replacement remains a fallback or an intentional host change. It is still
required when the base image, operating system, firewall, network path, systemd
contract, or dependencies change and are not already present on the running
runtime.

Access to the private OCI VM uses OCI Bastion diagnostics or another
owner-approved private access path. Do not add public SSH for this runtime.
