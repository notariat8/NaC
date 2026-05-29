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

Access to the private OCI VM uses OCI Bastion diagnostics or another
owner-approved private access path. Do not add public SSH for this runtime.
