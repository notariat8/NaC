# Implementation Plan: SPFx Role and Deadline Cockpit

Status: `IMPLEMENTED_OFFLINE`

Date: July 29, 2026
Leading issue: [#710](https://github.com/notariat8/NaC/issues/710)
Design: [SPFx Role and Deadline Cockpit](../specs/2026-07-29-spfx-role-deadline-cockpit-design.md)

## Objective and boundaries

This plan extends the existing read-only SPFx/BPMN workspace for
`notary_team_01`. It uses only the strictly validated synthetic BFF DTO and
existing BPMN viewer behavior. It performs no Graph browser requests, writes,
permission changes, App Catalog deployments, site installations, or tenant
actions.

The initial reference timestamp is bound at the web-part boundary and passed
through as `evaluationTimestamp`; the component then refreshes the visible
deadline evaluation every minute. All filter and deadline derivations remain
pure local view-model functions with an explicit time input. Current Step stays
read-only; Selected Step is local orientation only.

## AC mapping

| AC | Implementation | Evidence |
| --- | --- | --- |
| `AC-710-01` | `all/open/deadline/notary` filter model, ordering, selection transition, and ARIA | view-model and component tests |
| `AC-710-02` | fixed reference time, boundaries, and text-redundant deadline traffic light | view-model boundary tests and visual traffic-light check |
| `AC-710-03` | `assigned/deputy`, role frame, notary badge, and approval text | component tests and light/dark screenshots |
| `AC-710-04` | separate Current/Selected Step markers and synchronized detail view | runtime contract and component tests |
| `AC-710-05` | loading, empty, access denied, error, abort, and exactly one retry read | component tests and error screenshot |
| `AC-710-06` | responsive/dark, visual evidence, build, and repository gates | evidence matrix and complete validation |

## Work packages

1. **Traceability and immutable boundary**
   - Bind issue #710, DE/EN specs, DE/EN plans, and `AC-710-01` through
     `AC-710-06`.
   - Preserve the existing `Matter.Read` BFF read, exact-shape parsing, size
     bounds, and BPMN SHA-256 verification unchanged.
   - Statically verify that no Graph client, modeler, `saveXML`, or
     SharePoint/Teams write path is introduced.

2. **Extend the view model test-first**
   - In `WorkspaceViewModel.test.ts`, first cover the four stable filter IDs,
     DTO ordering, `offen`/`open` normalization, and empty results.
   - Use the fixed `2026-08-25T16:00:00Z` test timestamp and test one
     millisecond before the reference, exactly at the reference, exactly seven
     days, and seven days plus one millisecond.
   - Test `none`, `overdue`, `urgent`, `scheduled`, and their German text
     labels as well as `assigned`/`deputy`.
   - Only then implement the pure derivations without implicit clock access in
     `WorkspaceViewModel.ts`.

3. **Bind reference time and role frame**
   - In `NacBpmnViewerWebPart.ts`, bind an initial valid UTC
     `evaluationTimestamp` per instance and pass it as a required prop.
   - In `NacBpmnViewer.tsx`, refresh the visible reference value every 60
     seconds and on retry, and classify matter/task deadlines exclusively
     against that explicit value.
   - Display `accessMode`, host display name, notarial approval count, notary
     badge, and spelled-out approval state without deriving an authorization
     decision from them.

4. **Implement filters and selection consistently**
   - Render filters as a button group with visible focus, `aria-pressed`, and
     stable labels; display result and total counts.
   - If a filter removes the selection, select the first visible task in DTO
     order. With zero matches, remove details and `nac-selected-step`.
   - On task selection, atomically bind list state, `data-nac-selected-step`,
     BPMN marker, and detail view to the same `taskId`/`stepCode`.
   - Never change `nac-current-step` through filters or selection. Continue to
     treat missing, duplicate, or noncanonical BPMN tasks as fail closed.

5. **Secure empty, error, and retry states**
   - Test loading, filtered empty, access denied, BFF unavailability, invalid
     BPMN, and render failure as separate states.
   - Offer retry only for transient unavailability, invalid assets, and render
     failure; access denied remains without retry.
   - On retry, destroy the old viewer, abort an outstanding read, reset the
     filter to `all`, and start exactly one new bounded BFF read.

6. **Finish responsive and dark behavior**
   - Verify the wide two-column layout, container-based single-column layout through `760px`,
     and stacked summary/tasks through `420px`.
   - Keep BPMN scrollable on narrow viewports; render filters, long UTC
     timestamps, badges, focus, and retry without overflow or overlap.
   - Verify semantic danger/warning/success tokens, role/approval states, and
     distinct Current/Selected Step markers in light and dark themes.

7. **Produce visual evidence**
   - Use a standalone synthetic offline visual contract with production CSS,
     canonical BPMN, a fixed display name, and
     `evaluationTimestamp=2026-08-25T16:00:00Z`; open no tenant or live
     connection and do not present it as React/SPFx E2E.
   - Capture `VIS-710-01` through `VIS-710-06` from the spec with the exact
     viewport, theme, filter, and state.
   - Bind browser, viewport, container width, theme, filter, reference time,
     complete SHA-256 values, and source hashes in the manifest; the PR binds
     that manifest to the reviewed head commit.
   - Check for real display names, matter data, tenant URLs, tokens, and
     correlation values before storing the evidence.

8. **Validate, review, and deliver**
   - Run the following commands from the repository root:

     ```bash
     (cd spfx/nac-bpmn-viewer && npm run validate:current-step)
     (cd spfx/nac-bpmn-viewer && npm run build)
     python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
     python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
     python3 scripts/validate_spec_traceability.py
     python3 scripts/validate_language_parity.py
     python3 scripts/validate_doc_links.py
     git diff --check
     python3 scripts/nac.py doctor --profile strict
     ```

   - Before PR approval, inspect the complete `origin/main...HEAD` diff, file
     list, and commit list; do not revert unrelated parallel changes.
   - Reference `AC-710-01` through `AC-710-06`, all six evidence IDs, and
     command outputs in the PR.
   - Await independent review and green remote CI, and deliver only through
     the protected PR against `main`.

## Acceptance matrix

| State | Automated | Visual |
| --- | --- | --- |
| four filters and selection transitions | view model + component | `VIS-710-01` through `VIS-710-03` |
| deadline boundaries and text labels | view model | `VIS-710-01`, `VIS-710-03` |
| `assigned/deputy` and notarial approval | view model + component | `VIS-710-01`, `VIS-710-03` |
| Current/Selected Step separation | runtime contract + component | `VIS-710-01` |
| empty and narrow layout | component | `VIS-710-02`, `VIS-710-04` |
| error, abort, and retry | component | `VIS-710-05` |
| read-only/BFF boundary | Python contract + static check | evidence data check |

## Done criteria

- All six ACs have automated or visual evidence.
- Visual evidence covers desktop, narrow, light, dark, empty, and retry.
- Build, focused tests, spec/language/link validators, `git diff --check`, and
  strict doctor pass.
- The UI contains synthetic data only and remains within the existing
  read-only BFF boundary.
- The complete PR diff has independent review and remote CI is green.
