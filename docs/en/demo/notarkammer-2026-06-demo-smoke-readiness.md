# Notarkammer Demo 2026-06: Smoke Readiness

Smoke-ID: `NK-DEMO-SMOKE-2026-06`
Version: `1.0.0`
Status: Protected PR, Review/Merge Gate, no OCI apply.

Scope: `docs/de/demo/`, `docs/en/demo/`, `src/nac_observability/`,
`scripts/notarkammer_demo_smoke.py` and `tests/`. This artifact is a runbook
smoke check for the presentation, not monitoring; no live network test in unit
tests. No secrets, no mandate data, no OCI or IdP write, no infrastructure or
runtime change. All examples use synthetic demo data, a test user and
pre-approved demo views.

## T-15 Minute Smoke Check

| Check | Manual view check | Expectation | Fallback |
| --- | --- | --- | --- |
| www-n8 process model | Open `https://notariat8.de/prozessmodell.html` in a fresh or already loaded browser tab. | The process model is reachable; Immobilienkaufvertrag, gate and critical path are visible. | Show an already loaded tab or cached screenshot; do not deploy live. |
| App health | Open `https://app.notariat8.de/healthz` in the browser or by read-only curl. | Short, non-sensitive status; no secret and no matter reference. | Close the health tab and show the workspace boundary. |
| Workspace without session | Open `https://app.notariat8.de/workspace` without a session. | Expected result is `401`, `403` or a closed view: fail-closed, no workspace content, keine Workspace-Inhalte, no matter data. | Explain fail-closed as security evidence. |
| Login/OIDC | Continue `https://app.notariat8.de/login` only with an approved test user. | Login/OIDC stays demo-bound; no real credentials and no real files. | If OCI or IdP is cold or slow: do not debug live, nicht live debuggen; switch to the process model and workspace boundary. |

Optional machine-readable precheck, read-only only:

```bash
python scripts/notarkammer_demo_smoke.py --timeout-seconds 15
```

The script checks only the fixed demo URLs, accepts the closed workspace as the
expected fail-closed boundary and redacts query values plus login/callback
responses in the JSON output.

## Speaker Lines

- Speaker line: This public process view is the audited demo path.
- Speaker line: The app entry stays protected until the approved demo sign-in is complete.
- Speaker line: A closed workspace is the expected safety result before sign-in.
- Speaker line: If sign-in is slow, we continue with the process model and the protected boundary.

## Guardrails

- Customer text and Speaker line entries mention only notariat8, the demo path,
  process model, app entry and protected workspace.
- Internal provider, OCI, IdP, ATP, Vault, Wallet, tenant and secret details
  stay out of customer text.
- No live debugging during the presentation; do not switch into the OCI
  console, IdP console, secrets, wallets, ATP schema or productive logs.
- No apply, no release, no runtime action and no cloud change.
- Evidence for the Protected PR is limited to branch, commit SHA, test output,
  Review/Merge Gate and this versioned runbook.

## Cold or Slow OCI/IdP Path

If OCI or IdP is kalt oder langsam, cold or slow, do not wait and do not debug
live:

1. Show the already loaded tab or cached screenshot of the process model.
2. Show `https://app.notariat8.de/workspace` without session.
3. Explain the workspace boundary as the fail-closed result.
4. Document only `manual_review` or `blocked` in the PR, without copying
   secrets or mandate data.
