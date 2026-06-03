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

## App Release Overlay

An ordinary NaC software release does not require VM replacement after the
initial runtime is stable. The standard path is an App Release Overlay: a
reviewed NaC commit is transferred to the private runtime as a checked archive with a
documented SHA-256, unpacked by [deploy/runtime/nac-web-release.sh](../../../deploy/runtime/nac-web-release.sh)
into `/opt/nac/releases/<commit>`, activated through `/opt/nac/current`, and
verified after a `nac-web` systemd restart.
If the health check fails, the script performs a rollback by pointing
`/opt/nac/current` back to the previous target and restarting `nac-web` again.

Required apply gate for this app release path:

`Owner Apply Approval for Apply Block H NaC app release overlay`

VM replacement remains a fallback or an intentional host change. It is still
required when the base image, operating system, firewall, network path, systemd
contract, or dependencies change and are not already present on the running
runtime.

Access to the private OCI VM uses OCI Bastion diagnostics or another
owner-approved private access path. Do not add public SSH for this runtime.
