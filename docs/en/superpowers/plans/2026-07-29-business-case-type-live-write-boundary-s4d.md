# BusinessCaseType Live Write Boundary S4d Plan

**Spec:** [S4d Design](../specs/2026-07-29-business-case-type-live-write-boundary-s4d-design.md)

1. Add domain and verification contracts with `S4D_READY_OFFLINE` plus a
   standalone validator.
2. Implement typed hash-bound owner attestation, cycle-free canonical plan
   binding, `owner-approval-v1` authorization and final plan rebuild and
   revalidation.
3. Implement separate read-only identity inspection and business-write token
   factory ports.
4. Version the S6 event model for the five S4b operations.
5. Implement a composed evidence hook: local intent before canonical intent,
   WORM finalization before local closure.
6. Build the S4d boundary and synthetic offline factory for all five
   operations; no live factory.
7. Add gate, crash, replay, redaction, contract and CLI tests.
8. Update documentation, context, roadmap and quality-gate indexes.
9. Run unit, contract and strict gates, independent review and remote CI.
10. Merge the protected PR and clean branch and worktree.
11. Then prepare one bundled approval for production adapter binding, a bound
    synthetic write in `notary_team_01`, readback, WORM evidence and
    idempotency.

## Review hardening

12. Separate the approval candidate from the independent owner-verifier port.
13. Move final plan revalidation before all owner, identity, and credential
    access.
14. Attest identity inspection source, observation time, principal, and
    approval binding.
15. Bind the S6 v0.2 chain to the concrete mutation and provider-readback
    digest.
16. Run foreign-chain, S6-intent, plan, owner, and inspection negative tests
    before the PR can merge.

