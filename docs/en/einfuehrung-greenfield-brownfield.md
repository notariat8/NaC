# Introduction: Greenfield And Brownfield

## Goal

This document separates introduction paths for:

- `greenfield`: organizations without a stable existing process in the target
  area,
- `brownfield`: organizations with already established legacy processes.

## Greenfield Path

### Entry

1. Create an organization fork from the reference model.
2. Activate roles, approvals and policies.
3. Select one or two core processes as a pilot.
4. Start the pilot on the current approved release.

### Rollout

1. Evaluate the pilot from subject-matter, regulatory and operational angles.
2. Bring improvements into the fork as change requests.
3. Tag an organization release.
4. Expand step by step to additional teams or locations.

## Brownfield Path

### Entry

1. Document existing current-state processes as a `legacy` version.
2. Perform a risk and gap analysis against the reference model.
3. Select prioritized target processes for migration.
4. Define a clearly bounded pilot area.

### Staged Migration

1. Continue the `legacy` flow in an audit-proof way.
2. Build the target flow as a new version in the fork.
3. Start new matters on the new version.
4. Close running legacy matters on `legacy`.
5. After legacy matters are complete, retire `legacy` in an orderly way.

## Decision Rules For Both Paths

- No full rollout without pilot evidence.
- Every productive process version needs a release tag and approval.
- In compliance conflicts, evidence capability takes priority over speed.
- Mixed operation is controlled through version binding at the start of each
  matter.

## 90-Day Orientation

### Greenfield

- Days 1-15: target picture, roles, core processes.
- Days 16-45: pilot for invoice/bookkeeping.
- Days 46-75: expansion to additional processes.
- Days 76-90: stabilization and release `v1.0.0`.

### Brownfield

- Days 1-20: capture current processes and define `legacy`.
- Days 21-50: model target process and set up pilot.
- Days 51-75: mixed legacy/new operation with version binding.
- Days 76-90: evaluate migration and plan additional conversions.
