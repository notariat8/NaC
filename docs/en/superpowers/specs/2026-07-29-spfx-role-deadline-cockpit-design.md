# SPFx Role and Deadline Cockpit

Status: `IMPLEMENTED_OFFLINE`

Date: July 29, 2026
Leading issue: [#710](https://github.com/notariat8/NaC/issues/710)
Scope: synthetic, read-only SPFx workspace for `notary_team_01`

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: spfx-role-deadline-cockpit
leading_issue: https://github.com/notariat8/NaC/issues/710
risk_gate: None
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-07-29-spfx-role-deadline-cockpit.md
review_gates:
  - Privacy
  - Human Approval
acceptance_ids:
  - AC-710-01
  - AC-710-02
  - AC-710-03
  - AC-710-04
  - AC-710-05
  - AC-710-06
validation_commands:
  - cd spfx/nac-bpmn-viewer && npm run validate:current-step
  - cd spfx/nac-bpmn-viewer && npm run build
  - python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
  - python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - git diff --check
  - python3 scripts/nac.py doctor --profile strict
```

## Objective

The existing SPFx/BPMN workspace is extended into a scannable role, deadline,
and task cockpit. The UI remains a read-only projection of the synthetic BFF
DTO. It supports selection and orientation but does not change task status,
the process instance, Current Step, permissions, or tenant data.

## Scope

In scope:

- only the synthetic `notary_team_01` workspace and synthetic matter
  `NAC-SYN-MATTER-001`,
- local filtering of already loaded tasks with `all`, `open`, `deadline`, and
  `notary`,
- deterministic deadline classification from an explicitly bound reference
  timestamp,
- visible `assigned` or `deputy` access mode, signed-in role, and notarial
  approval boundary,
- consistent task selection in the list, detail view, and BPMN marker,
- loading, empty, access-denied, error, and retry states,
- responsive layout and light and dark themes,
- focused automated checks and visual evidence.

Out of scope:

- new BFF endpoints, new Graph permissions, or browser access to Microsoft
  Graph,
- BFF DTO changes beyond the existing strictly validated fields,
- writes to BPMN, tasks, matters, SharePoint lists, documents, Teams settings,
  roles, or deputy assignments,
- App Catalog deployment, site installation, tenant action, or live smoke,
- real matter data or production identities.

## Read-only and BFF boundary

The browser loads exactly the existing, strictly shaped workspace through the
delegated NaC BFF `Matter.Read` scope. `NacBffClient` bounds size and field
shape and verifies the canonical BPMN XML using SHA-256. The UI only consumes
`matter.accessMode`, `matter.deadline`, `matter.tasks`, and the verified BPMN
model.

Filters, deadline states, and selection are pure in-memory view-model
derivations. They create neither a second data path nor a mutation. Retry only
repeats the same bounded BFF read, aborts any outstanding read, and resets the
local filter to `all`. `401` and `403` remain closed as access denied without
retry. No UI label may be interpreted as a separate authorization decision;
the server-side BFF decision remains authoritative.

## Explicit reference timestamp

The SPFx web part binds an initial UTC timestamp per viewer instance as
`evaluationTimestamp`. The component adopts it explicitly and then refreshes
its visible deadline evaluation every 60 seconds from the browser clock. The
cockpit displays the exact timestamp used. Filtering, selection, and the pure
view-model functions never access the clock implicitly; every derivation
receives its reference timestamp as an argument. Retry also resets the value to
a current UTC timestamp.

`evaluationTimestamp` and `dueAt` are evaluated as valid ISO-8601 UTC
timestamps with `Z`. Automated boundary tests and synthetic visual evidence
use `2026-08-25T16:00:00Z` as the mandatory value. `dueAt=null` is treated as
`none`. An invalid reference or deadline timestamp violates the already
validated DTO contract and fails closed into the render-error state.

## Filter contract

The four stable technical IDs and their German display labels are:

| ID | Display | Predicate |
| --- | --- | --- |
| `all` | Alle Aufgaben | all tasks in DTO order |
| `open` | Offene Aufgaben | status after trim and lowercasing is exactly `offen` or `open` |
| `deadline` | Aufgaben mit Frist | `dueAt` is not `null` |
| `notary` | Aufgaben mit Notarfreigabe | `requiresNotaryApproval` is `true` |

The filters form an accessible button group with a visible focus state and
`aria-pressed`. The result and total counts remain visible. If the selected
task remains in the result, selection stays stable. Otherwise, the first
visible task is selected deterministically. With zero matches, task details
and the Selected Step marker are removed while the immutable Current Step
remains visible.

## Deadline traffic light

Every traffic-light state has a redundant text label and must not communicate
through color alone:

| Status | Rule relative to `evaluationTimestamp` | Display |
| --- | --- | --- |
| `none` | `dueAt` is `null` | Keine Frist |
| `overdue` | `dueAt < evaluationTimestamp` | Frist überschritten |
| `urgent` | remaining time from zero through seven days, inclusive | Frist innerhalb von sieben Tagen |
| `scheduled` | remaining time greater than seven days | Frist geplant |

`overdue`, `urgent`, and `scheduled` use semantic danger, warning, and success
tokens with sufficient contrast in light and dark themes. The matter deadline
and every task deadline continue to show the bound UTC value next to the
localized time so the derivation remains auditable.

## Role, deputy, and approval display

`accessMode=assigned` is displayed as `Zugeordnetes Team (assigned)` and
`accessMode=deputy` as `Aktive Vertretung (deputy)`. The role frame shows the display
name supplied by the host and the number of tasks requiring notarial approval.
Every affected task also carries the `Notar` text badge; the detail view spells
out whether notarial approval is required.

The display grants no additional authority. In particular, showing deputy or
notary state neither changes a role nor performs an approval.

## Selection and BPMN consistency

The first DTO entry is the read-only Current Step. Its `nac-current-step`
marker is set once and is not moved by filtering or selection. Selecting a
task separately sets `nac-selected-step` and updates `aria-pressed`,
`data-nac-selected-step`, and the detail view to the same `taskId`/`stepCode`
binding. Missing, duplicate, or non-`bpmn:Task` step codes fail closed into the
render-error state.

## Empty, error, and retry

- A clear loading state is displayed while reading.
- An empty filter displays `Keine passenden Aufgaben` and keeps filters
  available for correction.
- Access denied shows no technical details and no retry.
- BFF unavailability, invalid BPMN, or a render failure shows a comprehensible
  error and `Erneut laden`.
- Retry resets local filter and selection derivations, destroys the old viewer
  instance, and starts exactly one new BFF read.
- Error text, focus states, and actions remain keyboard accessible.

## Responsive and dark

On wide web-part containers, BPMN and the task inventory are side by side.
Container queries, rather than browser width, switch to one column at no more
than `760px`; BPMN remains horizontally scrollable and is not shrunk until
unreadable. At no more than `420px` container width, the summary and task rows
stack. Filters, badges, timestamps, and retry must neither overflow nor obscure
other content.

Dark theme is derived only from the SPFx host theme. All status colors, focus
rings, text and surface contrast, and Current and Selected Steps remain
distinguishable in both themes.

## Visual evidence

The reproducible Playwright run renders a standalone synthetic offline visual
contract. It uses the exact production stylesheet source, canonical BPMN, and
`bpmn-js`, but not the bundled React component, BFF, or an SPFx/SharePoint host.
It is therefore explicitly not a component or live E2E test. React behavior,
ARIA states, retry, and clock refresh are covered separately by the 82 SPFx
tests; a real host E2E remains part of a later owner-gated deployment.

The PNG files are element crops within the listed viewports:

| Evidence ID | Viewport/container/theme | Required state |
| --- | --- | --- |
| `VIS-710-01` | `1440x1000`, full container, light | `all`, role frame, traffic light, distinct Current/Selected markers, and detail |
| `VIS-710-02` | `390x844`, full container, light | narrow single-column view with `deadline` and horizontally usable BPMN |
| `VIS-710-03` | `1440x1000`, full container, dark | `notary`, readable role/approval and traffic-light states |
| `VIS-710-04` | `390x844`, full container, dark | empty state and functional recovery to `all` without overflow or overlap |
| `VIS-710-05` | `390x320`, light | transient error with functional retry and narrow-container check |
| `VIS-710-06` | `1440x1000`, `390px` web-part container, light | container query in a wide browser without overflow or overlap |

Versioned synthetic evidence:

- [VIS-710-01 Desktop Light](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-01-desktop-light.png) (`26432468...83f6fe`)
- [VIS-710-02 Narrow Light](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-02-narrow-light.png) (`1293bf10...aaa86f`)
- [VIS-710-03 Desktop Dark](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-03-desktop-dark.png) (`dee4419c...84bb2d`)
- [VIS-710-04 Narrow Dark Empty](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-04-narrow-dark-empty.png) (`09584ea0...d521e8`)
- [VIS-710-05 Error/Retry](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-05-error-retry.png) (`279cea84...4eb559`)
- [VIS-710-06 Narrow Container](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-06-narrow-container-light.png) (`d0a67f9e...d2decc`)
- [Evidence manifest](../../../../assets/docs/spfx-role-deadline-cockpit/VIS-710-manifest.json) (`nac.spfx-role-deadline-visual-evidence/v0.2`)

The manifest binds the Chromium version, reference timestamp, query, viewport,
container width, complete screenshot hashes, and hashes of every visual
contract source. The local run confirms without tenant access: no page
overflow, no clipped text, 41 rendered BPMN elements in each ready state,
exactly one Current Step, at most one Selected Step, and functional empty and
retry recovery. The PR binds the manifest to the reviewed head commit.

Screenshots must not contain real display names, matter data, tenant URLs,
tokens, or correlation values.

## Acceptance criteria

- **AC-710-01:** `all`, `open`, `deadline`, and `notary` filter
  deterministically in DTO order, are keyboard accessible, and keep selection
  and result count consistent.
- **AC-710-02:** Deadline state and traffic light are derived exclusively from
  the explicitly bound reference timestamp with tested boundary values and
  are also emitted as text.
- **AC-710-03:** The role frame, `assigned`/`deputy`, and notarial approval
  boundary are visibly readable without changing authorization or approval.
- **AC-710-04:** Task selection keeps list, detail view, and Selected Step
  synchronized while Current Step and all server data remain unchanged.
- **AC-710-05:** Loading, empty, access-denied, error, and bounded retry states
  are robust, accessible, and add no data or write path.
- **AC-710-06:** Desktop, narrow, light, and dark views pass visual evidence;
  the SPFx build, focused tests, repository validators,
  `nac doctor --profile strict`, independent review, and protected PR are
  green.
