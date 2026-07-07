# Microsoft 365 CLI Admin Accelerator

Status: owner-gated admin runbook
Last content update: 2026-07-06

## Purpose

This runbook allows CLI for Microsoft 365 as an operator shell for tenant setup,
Entra app bootstrap and Graph smoke tests. It is not a production dependency of
the NaC runtime and does not replace the Python-based Graph REST provisioner.

The product rule remains unchanged: data operations for the Teams SharePoint
data plane run only through Microsoft Graph REST v1.0 or through MCP servers
that also use Microsoft Graph REST v1.0 internally.

## Installation

```bash
npm install -g @pnp/cli-microsoft365
m365 version
```

Alternatively, the CLI can run in a container. For reproducible provisioning
runs, the used version is recorded in the run log.

## Login

For interactive admin work, device code is the default because it does not place
a password or secret value in shell history, chat or the repository.

Important: The CLI can create Entra app registrations. To do that, it first
needs a valid authentication against the tenant. There are two different app
layers:

| Layer | Purpose | How it is created |
| --- | --- | --- |
| CLI Entra app | The CLI uses it to sign in to the tenant. | Either through `m365 setup` or through an existing app registration. |
| NaC bootstrap/runtime app | NaC later uses it for provisioning or runtime access. | After successful CLI login through `m365 entra app add` or Graph REST. |

The CLI is therefore useful precisely for reproducible app registrations, Graph
smokes and tenant configuration. It just does not remove the need for an initial
admin authentication anchor.

### Bootstrap Route A: CLI App Through `m365 setup`

`m365 setup` can configure a new app registration for the CLI. According to the
CLI documentation, this path uses Azure CLI login, then creates the app
registration and stores the information in the CLI configuration.

Links:

- [CLI for Microsoft 365 setup](https://pnp.github.io/cli-microsoft365/cmd/setup/)
- [Azure CLI authentication](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli?view=azure-cli-latest)

Visible commands:

```bash
az login --tenant "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
m365 setup
```

This route is only partially available in the current Codex environment because
`az` is not installed here and host package installation is blocked. On an admin
workstation or in Azure Cloud Shell, it is the cleanest bootstrap path.

### Bootstrap Route B: Use Existing CLI App

```bash
m365 setup
m365 login --appId "<cli-entra-app-id>" --tenant "<tenant-id>" --authType deviceCode
m365 status
```

The login must be completed by a tenant admin in the browser. The CLI prints a
Microsoft device login URL and a one-time code for that step.
`<cli-entra-app-id>` is the Entra app used by the CLI itself for interactive
admin work. It is not the same as the later NaC runtime app.

### After Login: Create NaC App Through CLI

After successful CLI login, the CLI can create the actual NaC app
registrations:

```bash
m365 entra app add --name "NaC Graph Bootstrap" --certificateFile "<public-certificate.cer>" --apisApplication "https://graph.microsoft.com/Team.Create,https://graph.microsoft.com/Sites.Manage.All" --grantAdminConsent
```

This step changes tenant state and therefore remains separately owner-gated.

## Required Handoff Before User Action

Before the agent asks the owner for values or needs an action in the Microsoft
tenant, it must provide a prepared handoff. A bare request such as `send
tenant-id and app-id` is not allowed.

The handoff contains at least:

| Section | Required content |
| --- | --- |
| Purpose and risk | Why the action is needed and whether it only reads or can change tenant state. |
| Exact values or actions | Concrete field names, expected format and which values do not belong in chat. |
| Source links | Direct links to Microsoft Entra, device login and relevant documentation. |
| Copy-paste commands | Commands with placeholders visible before execution. |
| Secret handling | Secrets, certificates and tokens are not stored in chat or the repository. |
| Owner gate and stop condition | What will not happen without explicit approval. |
| Next step | What the agent will run after the owner action. |

Prepared login handoff for this MVP:

| Needed | Where to find it | Comment |
| --- | --- | --- |
| Tenant ID | [Microsoft Entra Admin Center: Tenant Overview](https://entra.microsoft.com/#view/Microsoft_AAD_IAM/TenantOverview.ReactView) | Not a secret, but a tenant-specific identifier. |
| CLI Entra App ID | [Microsoft Entra Admin Center: App registrations](https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) | App for CLI login, not the later NaC runtime app. |
| Device code confirmation | [Microsoft Device Login](https://microsoft.com/devicelogin) | Needed only after the command has started. |
| CLI login docs | [CLI for Microsoft 365 login](https://pnp.github.io/cli-microsoft365/cmd/login/) | Reference for `--appId`, `--tenant` and `--authType deviceCode`. |

After that, the agent may only start this visible command:

```bash
HOME=/tmp/nac-m365-tools/home PATH=/tmp/nac-m365-tools/node-v24.18.0-linux-x64/bin:/tmp/nac-m365-tools/m365-cli/bin:$PATH m365 login --appId "<cli-entra-app-id>" --tenant "<tenant-id>" --authType deviceCode
```

After successful login, the first allowed smoke test is a read-only Graph call:

```bash
m365 request --url "@graph/organization" --method get --output json
```

Productive writes, admin consent and Teams/SharePoint provisioning remain
separately owner-gated.

## AADSTS7000218 Failure

If token retrieval fails with `AADSTS7000218`, the CLI app is not usable as a
public client for device code. Do not fix this by creating a secret.

Fix in the app registration:

1. [Microsoft Entra App registrations](https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Open app `NaC M365 CLI Admin`.
3. Open `Authentication`.
4. Add platform `Mobile and desktop applications`.
5. Set redirect URI:

```text
https://login.microsoftonline.com/common/oauth2/nativeclient
```

6. Set `Allow public client flows` to `Yes`.

Then start a new device-code login. Old codes do not need to be reused.

## Allowed Use

Only these uses are allowed:

```bash
m365 setup
m365 login --appId "<cli-entra-app-id>" --tenant "<tenant-id>" --authType deviceCode
m365 status
m365 request --url "@graph/organization" --method get --output json
m365 request --url "@graph/groups" --method get --output json
```

For an owner-gated Entra app bootstrap, this is also allowed:

```bash
m365 entra app add --name "NaC Graph Bootstrap" --certificateFile "<public-certificate.cer>" --apisApplication "https://graph.microsoft.com/Team.Create,https://graph.microsoft.com/Sites.Manage.All" --grantAdminConsent
```

The private certificate key never lives in the repository. If command output
contains app IDs, tenant IDs or other identifiers, store them only in local admin
notes or secure secret management.

## Blocked Use

These uses are blocked for the MVP data path:

```text
m365 spo ...
m365 request --url "@spo/..."
m365 request --url ".../_api/..."
m365 request --url "@graphbeta/..."
CSOM
PnPjs as a runtime dependency
Microsoft Graph SDKs in the provisioner
```

Hub sites, SharePoint admin commands or PnP-specific SharePoint functions are
later admin exceptions only. They are not part of the MVP.

## Smoke Test

After successful login, the smallest useful test is:

```bash
m365 request --url "@graph/organization" --method get --output json
```

After that, the product path runs through the central NaC CLI:

```bash
python3 scripts/nac.py m365 teams-sharepoint plan --format json
python3 scripts/nac.py m365 teams-sharepoint privileged-plan --format json
```

The repeatable privileged apply path also uses Microsoft Graph REST v1.0 only.
It is not a standard-user path and needs explicit owner approval:

```bash
M365_GRAPH_ACCESS_TOKEN_FILE="<local-token-file>" python3 scripts/nac.py m365 teams-sharepoint privileged-apply --owner-approved --format json
```

Later, an app-only configuration with `M365_TENANT_ID`,
`M365_PROVISIONER_CLIENT_ID` and `M365_PROVISIONER_CLIENT_SECRET` can be used
instead. Tokens, client secrets, certificates and private keys are not stored
in chat, shell output or repository artifacts.

Any further live apply remains owner-gated and may only run after plan review,
target team confirmation, drift snapshot and admin consent.

After a separately approved runtime-app credential exists, the smallest
product-like read smoke can verify the existing SharePoint lists through the
runtime app:

```bash
M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE="<local-runtime-token-file>" python3 scripts/nac.py m365 teams-sharepoint runtime-smoke --owner-approved --runtime-smoke-output out/m365/teams-sharepoint/runtime-smoke.redacted.json --format json
M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE="<local-runtime-token-file>" python3 scripts/nac.py m365 teams-sharepoint runtime-metadata --owner-approved --runtime-metadata-output out/m365/teams-sharepoint/runtime-metadata.redacted.json --format json
```

Alternatively, the smoke uses `M365_TENANT_ID`, `M365_RUNTIME_CLIENT_ID` and
`M365_RUNTIME_CLIENT_SECRET`. This step only reads the sites referenced in the
non-secret provisioned state and compares the discovered lists and document
libraries with the declarative MVP schema.
`runtime-metadata` explicitly does not read list items or mandate data. It does
not create teams, groups, app roles, site permissions or SharePoint list items.

These individual commands are the read-only diagnostic path. For full
runtime/MCP operating evidence after changes, `release-gate-run` below is the
standard.

## Canonical M365 MVP Operating Sequence

For new operator runs, the central `nac` CLI is the leading operating edge.
Direct calls to `scripts/provision_teams_sharepoint_graph.py` remain allowed as
internal compatibility, but product documentation and agent handoffs go through
`nac`.

The normal sequence is:

```bash
python3 scripts/nac.py m365 teams-sharepoint privileged-plan --format json
python3 scripts/nac.py m365 teams-sharepoint privileged-apply --owner-approved --format json
python3 scripts/nac.py m365 teams-sharepoint release-gate-run --owner-approved --mcp-smoke-workspace-id notary_team_01 --mcp-smoke-correlation-id <correlation-id> --format json
```

`privileged-plan` is read-only and creates the review plan.
`privileged-apply` changes tenant state and may run only after review, drift
snapshot and owner approval. `release-gate-run` is then the standard runtime
evidence after MCP/runtime changes because the one-shot runner performs runtime
certificate expiry monitoring, runtime smoke, runtime metadata, synthetic
write/read/cleanup, leftover dry-run and evidence export in one owner-gated
run. The covered runtime steps verify certificate expiry and Sites.Selected
runtime access without list items or matter data and write redacted evidence
artifacts without thumbprint, site IDs, URLs, list or drive IDs, raw Graph
responses, tokens, secrets or file content.

The `mcp-smoke-leftover-cleanup` dry-run is the follow-up when the suite failed,
a previous smoke was interrupted or the operator wants to rule out synthetic
leftovers. If the dry-run reports matches, the delete run remains a separate
owner gate:

```bash
python3 scripts/nac.py m365 teams-sharepoint mcp-smoke-leftover-cleanup --owner-approved --format json
```

All evidence files are redacted under `out/m365/teams-sharepoint/` and are not
versioned. Tokens, private keys, raw Graph responses, real matter values and
SharePoint file content belong neither in chat nor in the repository.
`release-gate-run` runs `release-gate-evidence` at the end and summarizes the
existing redacted runtime and MCP artifacts into
`out/m365/teams-sharepoint/release-gate-evidence.redacted.md` and performs no
Graph request in the evidence step itself.

The full runtime/MCP sequence can be rendered offline as a repeatable release
gate:

```bash
python3 scripts/nac.py batch-approval m365 --batch-mode release-gate --workspace-id notary_team_01 --correlation-id <correlation-id> --format json
```

The batch command renders the MVP Go/No-Go run by default with a redacted audit
pack, redacted MVP readiness status and
`--release-gate-readiness-require-audit-pack`. When the audit pack should
compare against a baseline instead of the current run itself, only the baseline
is added:

```bash
python3 scripts/nac.py batch-approval m365 \
  --batch-mode release-gate \
  --workspace-id notary_team_01 \
  --correlation-id <correlation-id> \
  --release-gate-compare-left <baseline-correlation-id> \
  --format json
```

The renderer performs no Graph request. It creates the copyable approval text
for exactly the one-shot `release-gate-run --owner-approved` command and
documents the covered internal steps. Individual commands remain the diagnostic
and fallback path when a runner step must be reproduced in isolation.
