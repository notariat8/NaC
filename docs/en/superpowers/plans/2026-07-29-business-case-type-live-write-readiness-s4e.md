# BusinessCaseType Live Write Readiness S4e Plan

**Spec:** [S4e Design](../specs/2026-07-29-business-case-type-live-write-readiness-s4e-design.md)

1. Add domain and verification contracts for issue #702.
2. Implement a typed local-only readiness model using redacted hash bindings.
3. Fail closed on principal, permission, or site-role drift.
4. Check owner, Graph, certificate, and Azure Blob WORM adapter bindings.
5. Report the current state without a dedicated write identity as `BLOCKED`.
6. Verify a complete synthetic binding as `S4E_READY_OFFLINE`.
7. Add central `nac` CLI, validator, negative tests, and DE/EN documentation.
8. Complete strict gate, independent review, protected PR, remote CI, and
   cleanup.
9. Only then prepare one bundled owner approval for missing identity/adapter
   binding and one synthetic write.
