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

The first Functions adapter is intentionally GET/HEAD-only. It calls the same
`NaCLocalWebApp.handle(...)` contract as the local web server and performs no
POST, apply, or productive write operations. The entry path is intended for
`/healthz`, `/onboarding/readiness`, `/onboarding/dns-check`, and other
read-only customer onboarding pages. The function package stores no mandate data,
secrets, OCI API keys, or tenant credentials.

Required apply gate for the Functions parallel path:

`Owner Apply Approval for Apply Block J NaC OCI Functions parallel runtime`

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
