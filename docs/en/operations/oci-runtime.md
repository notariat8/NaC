# NaC OCI Runtime

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

Required apply gate for the Functions parallel path:

`Owner Apply Approval for Apply Block J NaC OCI Functions parallel runtime`

## No-SSH Functions Release

For the cloud-native runtime, the target path is a No-SSH Functions Release. A
protected, merged GitHub commit is built by OCI DevOps, stored as a container
image in OCIR, and pinned by an OCIR digest. The OCI Function is updated to
that digest and then verified through an API Gateway smoke test.

This path needs no Bastion or SSH access to the VM. The VM remains fallback
until the API Gateway path for `/healthz`, `/onboarding/readiness`,
`/onboarding/dns-check`, `/login`, and `/api/tenant/login-intent` is live-tested
and a separate Owner Apply gate approves cutover.

The Function release path remains GET/HEAD-only except for
`POST /onboarding/requests`. Login-intent configuration comes only from
server-side environment values; query parameters must not set identity domain,
client, redirect, state, or nonce values.

## ATP Onboarding Request Store

The productive onboarding request store is enabled only through an explicit
server-side gate:

- `NAC_ONBOARDING_STORE=atp`
- `NAC_ATP_DSN`
- `NAC_ATP_USER`
- `NAC_ATP_PASSWORD_SECRET_OCID`

A plaintext password in `NAC_ATP_PASSWORD` does not enable the store. If any
required value is missing, the route remains fail-closed and returns
`onboarding_request_store_disabled`. The password value is read at runtime from
OCI Vault through Resource Principal; Git, chat, query parameters, HTML, and
Function config contain only the Secret OCID, never the secret value.

Optional wallet/network paths:

- `NAC_ATP_CONFIG_DIR`
- `NAC_ATP_WALLET_LOCATION`

The ATP apply, table creation, and secret boundary remain a separate
Owner-gated infrastructure track through `notariat8/oci-landing-zone#44`. The
app adapter track is `notariat8/NaC#85`.

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
