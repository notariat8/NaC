# Plan - Azure BFF Step-7 Reconciliation

Status: `IMPLEMENTED_OFFLINE`

Date: 11 September 2026
Spec: [Design](../specs/2026-09-11-m365-azure-bff-function-deployment-reconciliation-design.md)
Leading issue: [#739](https://github.com/notariat8/NaC/issues/739)
Delivery Mode: Owner Direct
Risk Gate: Human Approval

## Implementation

1. Add the exact ARM GET allowlist and redacted `FUNCTION_DEPLOYMENT_NOT_APPLIED` projection.
2. Validate terminal step-7 state, ledger, evidence, and prepared artifacts byte for byte.
3. Produce an owner-free double inspection and hash-bound #739 comment.
4. Implement owner-verified, crash-safe append-only release of all three lock journals.
5. Add the central CLI command, domain and verification contracts, and DE/EN documentation.
6. Run negative tests, contract validators, the full suite, and strict doctor.
7. Commit and push, then execute read-only live inspection, exact #739 approval, and controlled release.

## Guardrails

The fix does not write to Azure, start a login, or request another key. The
subsequent new live run remains a separate owner-gated step and uses the
external-only sandbox.
