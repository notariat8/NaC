# Notarkammer Demo: Entry Point

This folder contains the prepared demo map for presenting notariat8 to the
notary chamber. The path is designed for an approximately one-hour session:
public orientation on `notariat8.de`, process modeling (BPMN), XNP and
Kartenleser card-reader boundaries, login at `app.notariat8.de`, and a
deliberately closed work area until session and role checks are complete.

## Showable Core Path

1. Start with public orientation at `https://notariat8.de`.
2. Show the `Immobilienkaufvertrag` matter and the BPMN view.
3. Explain duration, parallel work and the critical path.
4. Explain XNP, Kartenleser card reader, register and land-register access as
   subject-matter access points, without claiming productive filings.
5. Move to `https://app.notariat8.de`, login and the fail-closed boundary.
6. Mention ATP healthcheck and store gate only as technical status evidence,
   not as a mandate-data view.

## Documents In Recommended Order

| Purpose | Document |
| --- | --- |
| Preparation before the presentation | [notarkammer-2026-06-demo-preflight.md](notarkammer-2026-06-demo-preflight.md) |
| Live order and browser paths | [notarkammer-2026-06-live-demo-runbook.md](notarkammer-2026-06-live-demo-runbook.md) |
| Login/portal diagnostics and fallback status classes | [notarkammer-2026-06-login-portal-diagnostics-runbook.md](notarkammer-2026-06-login-portal-diagnostics-runbook.md) |
| 60-minute script | [notarkammer-2026-06-60-minute-live-demo-script.md](notarkammer-2026-06-60-minute-live-demo-script.md) |
| Presenter wording and fallback phrases | [notarkammer-2026-06-demo-script.md](notarkammer-2026-06-demo-script.md) |
| Smoke readiness and fallbacks | [notarkammer-2026-06-demo-smoke-readiness.md](notarkammer-2026-06-demo-smoke-readiness.md) |
| Go/No-Go decision | [notarkammer-2026-06-demo-go-no-go.md](notarkammer-2026-06-demo-go-no-go.md) |
| Merge order and live-test card | [notarkammer-2026-06-merge-order-live-test-card.md](notarkammer-2026-06-merge-order-live-test-card.md) |
| Known gaps and boundaries | [notarkammer-2026-06-demo-gap-audit.md](notarkammer-2026-06-demo-gap-audit.md) |
| Questions and objections | [notarkammer-2026-06-demo-qa-objection-handling.md](notarkammer-2026-06-demo-qa-objection-handling.md) |
| First route smoke map for login, matter metadata and BPMN evidence | [notarkammer-first-route-smoke-map.md](notarkammer-first-route-smoke-map.md) |
| First matter as metadata-only contract | [notarkammer-first-matter-metadata.md](notarkammer-first-matter-metadata.md) |
| Duration, parallel work and critical path | [notarkammer-bpmn-critical-path-talking-points.md](notarkammer-bpmn-critical-path-talking-points.md) |
| Real estate purchase agreement as XNP/SNP closing path | [notarkammer-immobilienkaufvertrag-xnp-vollzug-map.md](notarkammer-immobilienkaufvertrag-xnp-vollzug-map.md) |
| Evidence matrix for the real estate purchase agreement | [notarkammer-immobilienkaufvertrag-xnp-evidence-matrix.md](notarkammer-immobilienkaufvertrag-xnp-evidence-matrix.md) |
| XNP/BPMN demo depth | [notarkammer-xnp-bpmn-demo-depth.md](notarkammer-xnp-bpmn-demo-depth.md) |
| XNP demo contract and boundaries | [notarkammer-xnp-demo-contract.md](notarkammer-xnp-demo-contract.md) |
| Source matrix for XNP, XNotar, registers, land register and card reader | [notarkammer-xnp-quellenmatrix.md](notarkammer-xnp-quellenmatrix.md) |
| ISV questions for XNP/SNP API and test access | [notarkammer-xnp-snp-api-testzugang.md](notarkammer-xnp-snp-api-testzugang.md) |

## Boundaries

- no mandate data
- no secrets
- no productive filing
- No mandate data, identity documents, deeds, register retrievals or
  land-register retrievals.
- No productive XNP action and no productive register or land-register filing.
- No credentials, tokens, secrets, PINs or provider operations details in the
  presentation.
- If login, session, role check or store gate does not open cleanly, the app
  remains fail-closed and the demo switches to script, BPMN and documented
  evidence.
