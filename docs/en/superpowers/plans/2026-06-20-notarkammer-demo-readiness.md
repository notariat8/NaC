# Notarkammer Demo Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing notariat8/NaC capability credible and live-demo-ready for a one-hour Notarkammer presentation within four days.

**Architecture:** NaC remains the source of truth for notarial process models, with BPMN 2.0 as the canonical business model and `bpmn-js` as the editable modeling surface. `www-n8` becomes the polished public entry and demonstration path; `xyflow`-style graph views may render duration, parallelism and critical-path overlays, but they must not replace BPMN as the source.

**Tech Stack:** NaC Python validators and CLI, BPMN 2.0, bpmn-js, static `www-n8` GitHub Pages, `app.notariat8.de` OCI Functions runtime, GitHub protected PRs, no mandate data.

---

## Hard Deadline

- Presentation window: 4 days from June 20, 2026.
- Target demo duration: 60 minutes.
- Target state: polished and credible, not complete.
- Time zone for planning: CEST.

## Non-Negotiable Scope Boundaries

- No mandate data in Git, logs, public pages or demo URLs.
- No live portal writes, no real Grundbuch/Register actions, no customer mail dispatch.
- No OCI apply, release, secret read or destructive Git action without a separate owner gate.
- BPMN 2.0 is the canonical source for business process models.
- `xyflow` is an overlay/rendering surface for comprehension, not a second business source.
- Duration values are editable planning parameters. They are not presented as official averages unless backed by a cited official statistical source.

## Demo Thesis

Notarial work is not a four-step linear checklist. NaC can show a controlled, auditable and editable process model where:

- legal and operational gates are explicit,
- parallel work is visible,
- blocked work is clear,
- the critical path is understandable,
- expected duration is a parameter for planning,
- public views contain no mandate data,
- the app opens only after identity/session/role gates.

## Current Evidence State

This plan is no longer the starting point of the demo preparation. Issue #211 is
the current review and smoke-test evidence for the Notarkammer demo.

Completed and merged:

- NaC PR #215: demo smoke readiness runbook.
- NaC PR #216: XNP/BPMN demo depth.
- NaC PR #217: Notarkammer demo gap audit.
- www-n8 PR #18: public process-model demo.

Live smoke according to Issue #211:

- `https://notariat8.de/` returns 200.
- `https://notariat8.de/prozessmodell.html` returns 200.
- `https://app.notariat8.de/healthz` returns 200.
- `https://app.notariat8.de/workspace` returns 401 without a verified session;
  this is the expected fail-closed behavior.

Remaining Gaps for the demo stay intentionally narrow:

- do not claim or show productive XNP coupling,
- do not open the full workspace,
- do not perform real land-register, register, card-reader or XNP write actions,
- do not expose mandate data, session IDs, provider details or internal
  operating details.

## Four-Day Delivery Plan

### Day 1: Source Model And Demo Slice

**Objective:** Establish the demo truth: two usecases, one deep and one short.

- [ ] Confirm current GitHub state for NaC, `www-n8` and `oci-landing-zone`.
- [ ] Create a demo-readiness issue in NaC with links to all PRs and gates.
- [ ] Model `Immobilienkaufvertrag` as the main deep process.
- [ ] Model `Unterschriftsbeglaubigung` as the short comparison process.
- [ ] Define a process metadata contract for:
  - planning duration minimum,
  - planning duration maximum,
  - duration unit,
  - dependency/blocker references,
  - parallel group,
  - critical-path candidate,
  - role,
  - evidence requirement.
- [ ] Keep the first contract file small enough to validate and demo.

### Day 2: Editable BPMN And Visual Overlays

**Objective:** Make the process feel editable and explainable.

- [ ] Add or expose a `bpmn-js` editor/viewer route for demo process models.
- [ ] Ensure editor mode is clearly demo/sandbox and not connected to real mandate data.
- [ ] Add a duration and dependency overlay contract derived from BPMN/KG metadata.
- [ ] Add an `xyflow`-style critical-path view only as a derived rendering layer.
- [ ] Demonstrate at least:
  - one parallel split,
  - one join,
  - one blocking gate,
  - one critical-path segment,
  - one editable duration parameter.

### Day 3: Public Demo Polish

**Objective:** Make `www-n8` understandable to a Notarkammer audience.

- [ ] Rework `www-n8` copy to emphasize notarial control, not software jargon.
- [ ] Make "Prozessmodell ansehen" a real user-facing viewer path, not a GitHub jump.
- [ ] Add a visible "Dauer und kritischer Pfad" explanation for the real-estate process.
- [ ] Add a "Was wird nicht gespeichert" section for public and app demo trust.
- [ ] Add a direct demo path:
  - `notariat8.de`
  - process overview
  - real-estate process model
  - app login
  - protected start/workspace status
  - editor/viewer

### Day 4: Rehearsal, Fallbacks And Script

**Objective:** Make the live demonstration reliable.

- [ ] Run live smoke tests for all demo URLs.
- [ ] Prepare fallback screenshots or static HTML for the process viewer and app status.
- [ ] Prepare a 60-minute presenter script.
- [ ] Prepare a 5-minute short version.
- [ ] Verify no public page exposes Oracle/OCI/internal provider terminology unless intentionally in technical governance sections.
- [ ] Verify all checks pass before any release or deploy gate.

## Parallel Agent Work Packages

### Package A: Domain Research And Timing Evidence

**Owner:** research agent.

**Output:** `docs/de/superpowers/specs/2026-06-20-notarkammer-demo-domain-evidence.md`

- [ ] Collect primary legal anchors for real-estate purchase execution.
- [ ] Identify common blockers and dependencies:
  - land-register status,
  - priority/rank,
  - financing and land charge,
  - public-law approvals,
  - municipal pre-emption right,
  - tax clearance,
  - payment maturity,
  - ownership transfer.
- [ ] Define demo-safe duration buckets:
  - hours,
  - days,
  - weeks,
  - months.
- [ ] Mark every non-official duration as "Planwert" or "Erfahrungswert".

### Package B: BPMN/KG Process Depth

**Owner:** NaC BPMN agent.

**Output:** protected NaC PR.

- [ ] Extend `Immobilienkaufvertrag` to a rich notarial process with 20-35 meaningful steps.
- [ ] Preserve BPMN validity and NaC BPMN profile rules.
- [ ] Add metadata only where validators permit it.
- [ ] Add or update tests for metadata extraction.
- [ ] Keep `Unterschriftsbeglaubigung` short but credible.

### Package C: Public Website Demo Path

**Owner:** `www-n8` agent.

**Output:** protected `www-n8` PR.

- [ ] Improve homepage path to process model.
- [ ] Add duration/critical-path language for non-technical users.
- [ ] Add clear app transition.
- [ ] Preserve existing content tests and style guide constraints.
- [ ] Keep customer-facing copy free of OCI/provider/internal wording.

### Package D: Editor And Visualization Contract

**Owner:** app/editor agent.

**Output:** protected NaC PR, no OCI apply.

- [ ] Identify current web routes and safe extension point.
- [ ] Add editor/viewer contract before runtime wiring.
- [ ] Add tests for fail-closed behavior and no mandate data.
- [ ] Add derived graph view contract for duration/parallel/critical-path overlay.

### Package E: Demo Script And Fallback Evidence

**Owner:** QA/demo agent.

**Output:** `docs/de/demo/notarkammer-2026-06-demo-script.md`.

- [ ] Write the 60-minute script.
- [ ] Write the 5-minute version.
- [ ] List live URLs and fallback artifacts.
- [ ] Include exact "what to click" sequence.
- [ ] Include stop line if login or IdP is slow.

## Real-Estate Process Skeleton For Day 1

The first detailed process should include at least these logical blocks:

1. Anfrage und Beteiligte aufnehmen.
2. Grundstücks-/Wohnungseigentumsdaten erfassen.
3. Verkäufer-/Käuferidentität und Vertretung prüfen.
4. Aktuellen Grundbuchstand abrufen oder erfassen.
5. Belastungen und Löschungsbedarf prüfen.
6. Finanzierung/Grundschuldbedarf klären.
7. Öffentlich-rechtliche Genehmigungen prüfen.
8. Vorkaufsrechts-/Gemeindeprozess prüfen.
9. Kaufpreis, Fälligkeit, Besitzübergang, Nutzen/Lasten klären.
10. GNotKG-Geschäftswert prüfen.
11. Entwurf erstellen.
12. Verbraucherfrist prüfen, falls einschlägig.
13. Entwurf versenden.
14. Rückfragen/Beteiligtenfreigabe dokumentieren.
15. Beurkundung vorbereiten.
16. Beurkundung durchführen.
17. Ausfertigungen/Abschriften erstellen.
18. Auflassungsvormerkung beantragen.
19. Finanzierungsgrundschuld koordinieren.
20. Löschungsunterlagen/Treuhandauflagen koordinieren.
21. Anzeigen an Finanzamt/Behörden senden.
22. Genehmigungen/Negativzeugnis nachhalten.
23. Steuerliche Unbedenklichkeitsbescheinigung nachhalten.
24. Kaufpreisfälligkeit prüfen.
25. Fälligkeitsmitteilung versenden.
26. Zahlungseingang oder Zahlungsnachweis erfassen.
27. Eigentumsumschreibung beantragen.
28. Grundbuchvollzug prüfen.
29. Kosten/GNotKG-Abrechnung prüfen.
30. Abschlussnachweise und Aktenabschluss dokumentieren.

## Duration And Critical Path Model

Use conservative presentation language:

```yaml
duration:
  min: 2
  max: 6
  unit: weeks
  basis: planning_value
critical_path:
  candidate: true
  blocked_by:
    - land_register_priority_notice
    - tax_clearance_certificate
parallel_group: post_notarization_execution
```

Display model:

- Green: can start now.
- Yellow: can run in parallel but waits for outside response.
- Red: blocks the critical path.
- Gray: not relevant in this case.

## One-Hour Demo Script Outline

1. **5 min:** Start at `notariat8.de`; explain public, mandate-data-free process reference.
2. **10 min:** Open Immobilienkaufvertrag process; show it is not a linear checklist.
3. **10 min:** Show parallel work and critical path: Grundbuch, Finanzierung, Genehmigungen, Steuer.
4. **10 min:** Show editable BPMN/process model surface.
5. **10 min:** Switch to app login/protected start; explain fail-closed workspace.
6. **10 min:** Show short process comparison: Unterschriftsbeglaubigung.
7. **5 min:** Governance close: GitHub, protected PRs, no mandate data, controlled release.

## Owner Gates Expected During The Four Days

Batch gates whenever possible:

1. PR review/merge gates for NaC and `www-n8`.
2. Release gates for app/runtime only after merged commits are known.
3. Apply gates only if new OCI routing/config is required.
4. No secret gates unless a new runtime integration truly needs one.

## Current Day Mode For Larger Steps

The default mode for the remaining Notarkammer preparation is a multi-hour
multi-agent block. The controller starts independent PR-only tracks in parallel
and collects the results into one gate packet instead of interrupting the owner
for routine evidence.

### Owner-free during the block

- Read GitHub PR, issue, branch, check and diff status.
- Run local tests, documentation validators and quality gates.
- Read non-sensitive public references and already versioned demo artifacts.
- Prepare PRs, comments and review-packet summaries.
- Inspect worktree and branch hygiene in read-only mode.

### Owner gates remain separate

- Design Approval when professional scope or architecture is new.
- Review/Merge when a protected PR is ready.
- Release Approval when a concrete commit is built or deployed live.
- Apply Approval when Resource Manager or OCI configuration changes.
- Secret, credential, destructive Git and real live-data actions.

### Parallelization

A block should use at least three separate lanes when the scope allows it:

1. `www-n8` public demo surface.
2. NaC BPMN/usecase depth.
3. Live demo runbook, fallbacks and smoke paths.
4. Optional governance/queue memory when process friction becomes visible.

Each lane works in an isolated worktree on its own branch. After merge, cleanup
is emitted as a separate exact owner-gate sentence when branch or worktree
deletion is needed.

## Verification Baseline

NaC:

```bash
PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
```

`www-n8`:

```bash
node --test tests/content.test.js
git diff --check
```

OCI Landing Zone, only if touched:

```bash
PYTHONPATH=. /home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
```

## First Recommended Owner Packet

After the initial PRs are prepared, request exactly one packet:

```text
Owner Review/Merge for the Notarkammer demo readiness planning PRs:
- NaC process/domain plan PR
- www-n8 public demo path PR
- optional NaC BPMN/editor contract PR
```

Release and apply gates are separate and must include exact commit/image/plan identifiers.
