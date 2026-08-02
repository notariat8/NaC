# Implementation Plan: Workbench Live Read Binding

Status: `IN_REVIEW`

Date: 1 August 2026

Leading issue: [#725](https://github.com/notariat8/NaC/issues/725)

Design: [Workbench Live Read Binding](../specs/2026-08-01-workbench-live-read-binding-design.md)

## Work packages

1. **AC-1, AC-2, AC-3:** Define a dedicated live-binding contract and verification contract with a normative hash/wire fixture, AC test matrix, synthetic allowlist, and authentication/deny/cache semantics.
2. **AC-1, AC-2:** Add a rich access decision and test assigned/deputy/deny behavior without changing the existing v0.2 DTO.
3. **AC-1, AC-3, AC-4:** Implement the Workbench orchestrator and recursive redaction verifier with exact wire serialization, pre-Graph allowlist and fail-closed error mapping.
4. **AC-1, AC-2, AC-7:** Additively bind the FastAPI route and Azure composition while keeping the old route unchanged and testing `no-store` on all response paths.
5. **AC-5, AC-6, AC-8:** Implement the strict SPFx Workbench client and refresh host with immediate data discard, monotonic generation, and race/unmount tests.
6. **AC-5, AC-7:** Integrate Workbench as the primary view and the BPMN cockpit as a detail view in the existing web part.
7. **AC-1 through AC-8:** Update validators, DE/EN documentation and agent-context routing.
8. **AC-1 through AC-8:** Run focused tests, build, desktop/mobile evidence, independent implementation review and strict gate.
9. **AC-1 through AC-8:** Review the complete `main...head` diff, create a protected PR and drive remote CI to green.
10. **AC-8:** Check deployment readiness against the existing App Catalog/Teams/BFF automation; do not deploy from an unreviewed branch.

## Parallelism

After freezing the shared contract, the server and SPFx host are implemented in separate
file scopes. Contract/security review and visual verification run in parallel
with focused test loops. Subagents receive only isolated, path-specific context.
