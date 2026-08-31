# Sealed tenant-deploy allowlist for attested SPFx package path

Status: `IMPLEMENTED_OFFLINE`

Date: 30 August 2026
Leading issue: [#740](https://github.com/notariat8/NaC/issues/740)
Scope: Control-plane allowlist of the sealed `test-environment-deploy`

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: sealed-tenant-deploy-attested-package-allowlist
leading_issue: https://github.com/notariat8/NaC/issues/740
risk_gate: None
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-08-30-sealed-tenant-deploy-attested-package-allowlist.md
review_gates:
  - Privacy
  - Human Approval
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
validation_commands:
  - python3 -m unittest tests.test_m365_mvp_test_environment_deploy tests.test_m365_spfx_site_deployment
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - git diff --check
  - python3 scripts/nac.py doctor --profile strict
```

## Purpose

The sealed `test-environment-deploy` control plane
(`nac m365 teams-sharepoint test-environment-deploy`) fails at the
`add_or_overwrite_tenant_app` step with `M365_CLI_COMMAND_NOT_ALLOWLISTED`,
wrapped as `command_runner_exception`. The cause is a regression: the plan
builder `build_spfx_site_deployment_plan` defaults
`package_relative_path` to `ATTESTED_PACKAGE_RELATIVE_PATH`
(`assets/docs/spfx-hermetic-build/nac-bpmn-viewer-715.sppkg`), while the runner
allowlist `_matches_spfx_app_add` / `_is_bound_package_path` accepts only
`PACKAGE_RELATIVE_PATH` (`spfx/nac-bpmn-viewer/sharepoint/solution/nac-bpmn-viewer.sppkg`)
as the `--filePath` for `m365 spo app add`. The committed past evidence
(PASSED, 14 commands) used `PACKAGE_RELATIVE_PATH` and proves that the sealed
memfd upload via `spo app add --filePath /proc/self/fd/N` works. Only the
allowlist path shape blocks the attested path.

## Scope

In scope:

- Extending `_is_bound_package_path` and `_matches_spfx_app_add` in
  `src/nac_m365_graph/mvp_test_environment_deploy.py` so that alongside
  `spfx/nac-bpmn-viewer/sharepoint/solution/nac-bpmn-viewer.sppkg` the path
  `assets/docs/spfx-hermetic-build/nac-bpmn-viewer-715.sppkg` is also accepted
  as a bound artifact for `m365 spo app add --filePath`,
- Keeping the hard path checks: absolute, no `..`, fixed expected suffix,
  regular file,
- A regression test that lets both path shapes through the allowlist and fails
  if the attested path is rejected again,
- Confirming the existing `PACKAGE_RELATIVE_PATH` shape stays accepted (no loss
  of existing coverage).

Out of scope:

- Changes to memfd upload behavior, the sealed toolchain, or the
  Node-runtime-integrity preloader,
- Changes to the `build_spfx_site_deployment_plan` default or the
  BFF-activation flow,
- New Graph permissions, secrets, certificates, or tenant writes as part of
  the code fix,
- Changes to the data plane or to `m365 spo` usage beyond the existing
  control-plane allowlist,
- Live-deployment verification (remains owner-gated and separate).

## Constraints

- The allowlist must not weaken the security boundary: the path must be
  absolute, must not contain `..`, and must end with the fixed suffix; only
  regular files are allowed.
- The attested path already passes existing plan validation
  (`_validate_plan`, `_validate_control_plane_plan_binding`,
  `verify_package_sha256`) — only the runner allowlist blocks it.
- memfd upload is proven by past evidence and remains unchanged.
- No real secrets, no matter data, no tenant writes in the fix.

## Design decisions

- **A1 (approved):** Extend the allowlist to accept the attested path. The
  expected-suffix check is extended with the attested shape
  (`assets/docs/spfx-hermetic-build/nac-bpmn-viewer-715.sppkg`) without
  dropping the `PACKAGE_RELATIVE_PATH` shape. This is intent-faithful with the
  code comment "The standalone tenant deployment is bound to the reviewed,
  reproducible package artifact."
- Alternatives A2 (materialize at the spfx path) and A3 (revert default to the
  spfx path) were weighed and rejected: A2 writes into the workspace and
  contradicts the attested intent; A3 breaks the documented standalone-deploy
  intent and shifts responsibility to the build step.

## Risks

- **Low:** the allowlist surface grows minimally by a second accepted path
  shape; the hard checks remain in place.
- **No memfd risk:** upload behavior stays unchanged and is proven.
- **No privacy/secret risks:** the fix touches no secrets, matter data, or
  tenant writes.

## Acceptance criteria

- **AC-001:** `m365 spo app add --filePath <attested-path>` (absolute path to
  `assets/docs/spfx-hermetic-build/nac-bpmn-viewer-715.sppkg`) is accepted by
  `_matches_spfx_app_add`; `_is_bound_package_path` returns `True` for the
  attested path and `False` for paths with `..` or a wrong suffix.
- **AC-002:** `m365 spo app add --filePath <spfx-path>` (suffix
  `spfx/nac-bpmn-viewer/sharepoint/solution/nac-bpmn-viewer.sppkg`) stays
  accepted (no loss of existing coverage).
- **AC-003:** A regression test covers both path shapes and fails if the
  attested path is rejected again.
- **AC-004:** `python3 -m unittest tests.test_m365_mvp_test_environment_deploy
  tests.test_m365_spfx_site_deployment` is green;
  `python3 scripts/validate_spec_traceability.py` is green;
  `python3 scripts/nac.py doctor --profile strict` is green.
- **AC-005 (optional, owner-gated, not part of the code fix):** After CLI login
  and owner approval, a sealed
  `test-environment-deploy --owner-approved` against `notary_team_01` runs
  through `add_or_overwrite_tenant_app` (control-plane evidence PASSED).

## Non-goals

- No fix to memfd upload, the sealed toolchain, or the Node-runtime preloader.
- No change to the `build_spfx_site_deployment_plan` default.
- No live deployment as part of the code fix.
- No widening of the `m365 spo` allowlist beyond the existing control-plane
  command shape.
