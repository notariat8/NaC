# Agent Runtime Registry And Sandbox Leases

Status: contract and schema artifact, no productive apply
Last content update: 2026-07-02

## Purpose

This page makes the Variant C architecture concrete for `agent.notariat8.de`.
OCI remains the public identity, policy and routing layer. `notoclaw01` remains
the target runtime and connects outbound through mTLS or WebSocket/HTTPS. The
raw NemoClaw/OpenClaw UI is not published directly.

The machine-readable contract is
[workflows/contracts/agent-runtime-registry.contract.json](../../../workflows/contracts/agent-runtime-registry.contract.json).
The matching DDL artifact is
[deploy/database/atp-agent-runtime-registry-schema.sql](../../../deploy/database/atp-agent-runtime-registry-schema.sql).
Both are contract-first and must not be applied to ATP without a separate owner
apply gate.

## Runtime Flow

1. The browser reaches `agent.notariat8.de`.
2. OCI Identity Domain authenticates the user.
3. API Gateway or BFF checks session, tenant, role and purpose.
4. ATP resolves agent, endpoint, sandbox binding and active lease.
5. `notoclaw01` accepts only verified work through the outbound connector.
6. NemoClaw/OpenClaw keeps the local sandbox; productive matter data remains
   blocked until a private operating frame exists.

SSH remains an operations and diagnostic path. Productive user traffic does not
run through SSH and does not point directly to Brev or the raw OpenClaw UI.

## ATP Metadata

The schema artifact defines only safe metadata anchors:

| Table | Purpose |
| --- | --- |
| `nac_agent_registry` | approved agent types, runtime class and Git contract reference |
| `nac_agent_endpoints` | outbound connector endpoints and redacted health status |
| `nac_sandbox_bindings` | tenant, user, role, optional matter and sandbox relation |
| `nac_sandbox_leases` | active, expired or revoked sandbox lease |
| `nac_agent_session_bindings` | server-side binding between session and sandbox lease |

The tables must not contain tokens, raw claims, secrets, private keys,
dashboard tokens, environment dumps or unredacted matter content.

## Isolation

The minimum isolation is `tenant + user`. Once matter or role context is
loaded, `tenant + user + matter + role` is the preferred isolation. A sandbox
must not be shared by multiple independent users. Reuse is allowed only when
ATP confirms an active, non-revoked and non-expired lease.

## Owner Gates

Separate approval is required for:

- productive ATP schema apply,
- connector credentials and mTLS material,
- productive connector start,
- sandbox auto-start policy,
- private payload access.

This decision starts no connector, changes no OCI gateway and applies no
schema.
