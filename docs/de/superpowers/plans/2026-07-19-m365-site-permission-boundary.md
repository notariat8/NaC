# M365 Site-Permission-Grenze Implementierungsplan

**Spec:** [M365 Site-Permission-Grenze](../specs/2026-07-19-m365-site-permission-boundary-design.md)
**Leading Issue:** [#671](https://github.com/notariat8/NaC/issues/671)
**Delivery Mode:** Protected PR
**Risk Gate:** Human Approval
**Live-Aufrufe und Tenant-Writes:** jeweils exakt null

## Arbeitspakete

- [x] Sollvertrag `v0.2` mit getrennter Schema- und Site-Permission-Lane.
- [x] BFF-Plan und Live-Contract an `Sites.FullControl.All` binden.
- [x] Provisioner-State vor Live-Factory fail-closed prüfen.
- [x] BFF-UAMI unverändert auf `Sites.Selected`/`read` begrenzen.
- [x] Historischen Applied-State als vor Issue #671 erfassten Ist-Stand erhalten.
- [x] Validatoren, Negativtests sowie deutsche und englische Doku ergänzen.
- [ ] Vollständigen Diff, Strict-Gate, unabhängigen Review und Remote-CI abschließen.

Nach Merge bleiben die tatsächliche Entra-Zuweisung, Admin-Consent und ein neu
hashgebundener Live-Retry ein separates Owner-Gate.
