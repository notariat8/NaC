# M365 Site Permission Boundary Implementation Plan

**Spec:** [M365 Site Permission Boundary](../specs/2026-07-19-m365-site-permission-boundary-design.md)
**Leading Issue:** [#671](https://github.com/notariat8/NaC/issues/671)
**Delivery Mode:** Protected PR
**Risk Gate:** Human Approval
**Live calls and tenant writes:** exactly zero each

## Work Packages

- [x] Target contract `v0.2` with separate schema and site-permission lanes.
- [x] Bind the BFF plan and live contract to `Sites.FullControl.All`.
- [x] Fail closed on provisioner state before live-factory creation.
- [x] Keep the BFF UAMI restricted to `Sites.Selected`/`read`.
- [x] Preserve historical applied state as evidence captured before Issue #671.
- [x] Add validators, negative tests, and German and English documentation.
- [ ] Complete full-diff review, strict gate, independent review, and remote CI.

After merge, the actual Entra assignment, admin consent, and a newly hash-bound
live retry remain a separate owner gate.
