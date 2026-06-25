# Notarkammer Demo: First Route Smoke Map

Status: 2026-06-23

This protected-PR-only checklist is the shortest live validation route for
the first `Immobilienkaufvertrag` matter. It connects login status, the first
matter metadata fixture, XNP/SNP BPMN touchpoints and fail-closed boundaries
without changing runtime behavior.

Scope: documentation, tests and synthetic fixture references only. No OCI
writes, no secrets, no mandate data, no productive XNP action.

## Evidence Anchors

| Anchor | Evidence to have ready | Demo-safe statement |
| --- | --- | --- |
| `login_status` | `https://app.notariat8.de/login` opens or falls back to the cached presenter tab. | Login is a status boundary, not a data view. |
| `workspace_fail_closed` | `https://app.notariat8.de/workspace` stays closed without a valid session and role. | A closed workspace is acceptable evidence when session or role proof is missing. |
| `protected_first_matter_status` | `https://app.notariat8.de/workspace/immobilienkaufvertrag` opens only after approved session, role and binding. | The protected matter status remains metadata-only and does not open the full workspace. |
| first matter metadata | `tests/fixtures/demo/notarkammer-first-immobilienkaufvertrag.metadata.json` with `DEMO-MATTER-IMMOBILIENKAUF-01`, `notarkammer-first-matter-demo/v0.1` and `xnp_snp_target_metadata_only`. | The first matter is metadata-only and references `notarkammer-first-matter-metadata.md`. |
| XNP/SNP BPMN touchpoints | `bpmn/immobilienkaufvertrag.bpmn` and `notarkammer-immobilienkaufvertrag-xnp-evidence-matrix.md`. | XNP/SNP is shown as a modeled boundary for evidence, parallel work and critical path. |

## Four-Step Live Validation Route

| Step | Check | Go | Fallback |
| --- | --- | --- | --- |
| R1 | Open `https://app.notariat8.de/login` and confirm `login_status` can be described. | State that login status is visible. | Use cached screenshot or presenter wording; do not inspect provider internals. |
| R2 | Open `https://app.notariat8.de/workspace` without relying on hidden session state. | If session and role are present, show only safe workspace shell status. | If closed, name `workspace_fail_closed` as the expected protection boundary. |
| R3 | Open `https://app.notariat8.de/workspace/immobilienkaufvertrag` as `protected_first_matter_status`. | Connect first matter `DEMO-MATTER-IMMOBILIENKAUF-01`, matter type `immobilienkaufvertrag` and `bpmn/immobilienkaufvertrag.bpmn`. | If closed, name `protected_first_matter_status` as the expected fail-closed boundary; otherwise stay on `notarkammer-first-matter-metadata.md` and explain metadata-only scope. |
| R4 | Explain XNP/SNP and BPMN evidence touchpoints. | Use the evidence matrix to connect draft, signature, closing and response classes. | Switch to BPMN and matrix docs; make no productive access claim. |

## Boundaries To Say Out Loud

- no mandate data
- no secrets
- no productive XNP action
- no productive filing
- no OCI writes
- fail-closed is a valid demo outcome
