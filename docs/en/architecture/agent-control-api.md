# Agent Control API For agent.notariat8.de

Status: metadata-only route implementation, no gateway or runtime apply
Last content update: 2026-07-02

## Purpose

This page describes the allowed API boundary between OCI/BFF,
`agent.notariat8.de`, ATP and the outbound connector on `notoclaw01`. It builds
on the [agent runtime registry](agent-runtime-registry.md) and defines local
metadata-only handlers without a productive gateway route, API Gateway apply or
connector start.

The machine-readable contract is
[workflows/contracts/agent-control-api.contract.json](../../../workflows/contracts/agent-control-api.contract.json)
and is validated by
[scripts/validate_agent_control_api.py](../../../scripts/validate_agent_control_api.py).

## Route Groups

Browsers reach only the OCI layer. The raw NemoClaw/OpenClaw UI is not
published.

| Group | Route | Purpose |
| --- | --- | --- |
| Browser session | `GET /agent/status` | redacted agent and lease status for the verified session |
| Browser session | `POST /agent/leases/prepare` | server-side lease preparation after tenant, role, purpose and optional matter gate |
| Connector control | `POST /api/agent/connect` | register or refresh the outbound connector endpoint |
| Connector control | `POST /api/agent/heartbeat` | report redacted connector and sandbox health |
| Connector control | `GET /api/agent/work/next` | fetch the next metadata-only work envelope for an active lease |
| Connector control | `POST /api/agent/work/result` | submit a redacted result or failure class |

## Payload Boundary

Allowed fields are metadata only, such as request ID, tenant ID, user-binding
ID, agent ID, endpoint ID, sandbox-binding ID, sandbox-lease ID, lease status,
redacted health state, work-envelope ID, status, reason class and expiry time.

Blocked fields include IdP tokens, session cookies, provider claims, dashboard
tokens, private keys, client secrets, environment dumps, raw mandate data,
document full text, card PINs and XNP payloads.

## Lease Rule

`/api/agent/work/next` may answer only for an active, non-expired and
non-revoked lease. Expired or revoked leases fail closed. The minimum
isolation remains `tenant + user`; the preferred key is
`tenant + user + matter + role`.

## Implementation Boundary

`src/nac_web/server.py` implements the routes as local BFF handlers. These
handlers return metadata only, fail closed without a verified session or active
lease, and explicitly mark that no raw matter data, secrets, dashboard tokens,
ATP schema apply, OCI Gateway apply or `notoclaw01` connector start happened.

Connector-control routes do not accept a header by itself in this slice. The
local metadata-only test path also requires
`NAC_AGENT_CONTROL_ALLOW_METADATA_CONNECTOR_HEADER=true`; productive mTLS or
signed-connector authentication remains separately owner-gated.

## Non-Goals

- no productive API Gateway route,
- no OCI API Gateway apply,
- no ATP schema apply,
- no start or restart of the `notoclaw01` connector,
- no access to secrets or matter data.
