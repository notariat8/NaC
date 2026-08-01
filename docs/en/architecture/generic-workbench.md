# Generic NaC Workbench

## Decision

The generic workspace remains in the `notariat8/NaC` repository initially. It
is not developed as a separate product that must later be merged back. Source
boundaries preserve extractability without creating two release, governance
and security models today.

```text
workbench/core   -> contracts, runtime parser, selectors
workbench/nac    -> NaC BFF scope and producer binding
workbench/react  -> host-independent React view
SPFx/Teams       -> authentication, transport and host
NaC BFF          -> roles, delegation, truth, redaction and lease
```

The core imports no SPFx, React, Graph, MCP, BPMN or NaC runtime dependency.
The React layer imports only the core. The NaC adapter accepts only the
versioned redacted BFF snapshot.

## Authority Boundary

Tasks, attention, decisions, evidence and capabilities are server-side
projections. The browser derives no decision from `requiresApproval`, no
urgency from a deadline and no evidence authority from BPMN. BPMN is only a
hash-bound, non-authoritative model reference.

Every mutating capability is `deny` in the foundation slice. A later action
path requires fresh BFF authorization bound to matter, purpose, actor, role,
decision version, expiry, step-up/four-eyes policy, idempotency, correlation ID
and readback. The snapshot contains no URL, callback or executor.

Before emission, a redaction port must attest the canonical content as
`verified`, bound to policy, classifier, timestamp and SHA-256. The BFF checks
that binding and rejects a missing, mismatched or stale attestation.
`sourceRef` and `sourceSystem` are opaque technical identifiers only; URLs,
email addresses and known token or secret shapes are rejected at the
projection boundary. The attestation does not replace domain data
minimisation; it makes its server-side verification a technical prerequisite.

## Visibility And Freshness

`Today` shows attention only within the currently open, already authorized
matter. A future cross-matter daily view must be aggregated and access-filtered
by the BFF. Browser-side filtering across matters is excluded.

A snapshot and its access decision are valid for at most five minutes. Every
access decision is bound exactly to actor, role, workspace, matter and purpose.
Deputy access additionally requires a decision ID, decision version, reason,
issue time and expiry. Effective expiry is the minimum of projection lease and
delegation end. A mismatched binding, deny, invalid reference or expired
snapshot yields no data view.
The Python producer emits compact JSON in defined insertion order. The Python
producer and TypeScript consumer enforce the same 128 KiB limit on those exact
UTF-8 wire bytes. Both runtimes count text limits as at most 256 UTF-16 code
units; token-shaped values are forbidden in all external IDs and display text.

## Repository And Host Boundary

SPFx/Teams is the first compiled host candidate in Microsoft 365. The
foundation slice is built and tested with the SPFx package but is not imported
by the production web part yet. It therefore changes neither the deployed web
part nor its runtime data path. Live binding follows only after the BFF emits
the `nac.workbench.snapshot/v1` contract and the host refreshes the short lease
during operation.
CI transfers the compiled Workbench artifacts from the SPFx build into the
strict-gate job, where their bytes are checked against the visual evidence.

An Office add-in and local on-prem shell are later hosts of the same contract.
Repository extraction is considered only when a second independently released
consumer exists and the contract is stably versioned.

Contract: [generic-workbench.contract.json](../../../workflows/contracts/generic-workbench.contract.json)

Verification contract: [generic-workbench.verification.json](../../../workflows/verification-contracts/generic-workbench.verification.json)
