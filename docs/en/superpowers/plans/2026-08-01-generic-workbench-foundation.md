# Implementation Plan: Generic Workbench Foundation

Status: `IMPLEMENTED_OFFLINE`

Date: August 1, 2026

Leading issue: [#721](https://github.com/notariat8/NaC/issues/721)

Design: [Generic Workbench Foundation](../specs/2026-08-01-generic-workbench-foundation-design.md)

## Work Packages

1. Create directed `core`, `nac` and `react` import boundaries in the existing SPFx package.
2. Implement an exact short-lived snapshot parser with compact JSON serialization, a shared 128 KiB wire limit, a shared 256 UTF-16-code-unit text limit plus ID, token, reference and lease checks.
3. Add NaC BFF projection composition without domain inference, with content-bound redaction attestation and deny-only capabilities.
4. Implement Today, Matter and Decision Center views with a synthetic preview.
5. Add contract, import DAG, read-only, UI, BFF and visual tests plus mandatory CI verification of compiled evidence artifacts.
6. Add DE/EN documentation, agent-context routing and the central `nac frontend workbench-verify` edge.
7. Complete independent review, strict gate, protected PR and green remote CI.

## Not Executed

No tenant write, App Catalog deployment, Graph/MCP browser edge, new
permission or change to the existing live BFF endpoint is executed.
