# Plan — Sealed tenant-deploy allowlist for attested SPFx package path

Status: `IMPLEMENTED_OFFLINE`

Date: 30 August 2026
Spec: [2026-08-30-sealed-tenant-deploy-attested-package-allowlist-design.md](../specs/2026-08-30-sealed-tenant-deploy-attested-package-allowlist-design.md)
Leading issue: [#740](https://github.com/notariat8/NaC/issues/740)
Delivery Mode: Protected PR
Risk Gate: None (local allowlist + tests; no secret, no tenant write in the fix)

## Purpose

Implementation of the approved design **A1**: extend the sealed
`test-environment-deploy` control-plane runner allowlist so that alongside the
isolated BFF build output (`PACKAGE_RELATIVE_PATH`) the attested package path
(`ATTESTED_PACKAGE_RELATIVE_PATH`) is also accepted as a bound artifact for
`m365 spo app add --filePath` — without weakening the security boundary.

## Changes

- `src/nac_m365_graph/mvp_test_environment_deploy.py`:
  - additionally import `ATTESTED_PACKAGE_RELATIVE_PATH`,
  - extend `_is_bound_package_path` with the attested path shape
    `assets/docs/spfx-hermetic-build/nac-bpmn-viewer-715.sppkg`,
    **only** for the bound sppkg (`filename == PACKAGE_NAME`), so the
    zip/publish allowlist shapes are not widened,
  - hard checks remain: absolute, no `..`, fixed suffix, regular file
    (via plan validation),
  - intent comment in `_matches_spfx_app_add` (accepts both shapes via
    `_is_bound_package_path`, no tail change needed).
- `tests/test_m365_mvp_test_environment_deploy.py`:
  - import of `_is_bound_package_path` and `_matches_spfx_app_add`,
  - `test_spfx_app_add_allowlist_accepts_attested_and_spfx_package_paths`
    (predicates, both path shapes + negatives `..`/wrong suffix/relative, no
    widening to zip),
  - `test_m365_bound_artifact_accepts_attested_package_path` (sealed runner
    end-to-end, memfd basename `nac-bpmn-viewer-715.sppkg`).

## Validation

```bash
graft build
python3 scripts/validate_graft_context_layer.py
PYTHONPATH=src python3 -m unittest tests.test_m365_mvp_test_environment_deploy tests.test_m365_spfx_site_deployment
python3 scripts/validate_spec_traceability.py
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
python3 scripts/nac.py doctor --profile strict
```

## Implementation status

A1 has already been implemented and locally validated in the continuation
session (2026-08-30): 89 affected unit tests OK, full suite 2763 OK, `graft
check` PASSED, `nac doctor --profile strict` exit 0, and the diagnosis
reproduction shows `_matches_spfx_app_add` now `True` for the attested path).
Code and tests stay uncommitted until the leading issue exists; then a single
commit on feature branch `fix/sealed-tenant-deploy-attested-package-allowlist`.

## Guardrails

- No widening of the `m365 spo` allowlist beyond the existing control-plane command shape.
- No memfd or sealed-toolchain change.
- No secrets, no matter data, no tenant writes in the fix.
- "Done" only when `nac doctor --profile strict` is fresh-green, HEAD matches
  the GitHub target, the workspace is clean, and the three remote checks
  (`secret-scan`, `privacy-lint`, `quality-gate`) are green.
