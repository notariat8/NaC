# Working Model In The Organization: Agile And Kanban Cadence

## Goal

This document defines selectable working modes for operational work in the
organization fork. It contains two approved methods with standardized cadence
options.

## Working Methods

- `agile` is the starting standard for introduction and continuous improvement.
- `kanban` is allowed as a continuous-flow mode.
- The concrete variant can differ by team, but must be documented in the
  repository.

## Agile: Sprint Duration, Selection

Allowed sprint durations:

- `1w`, one week
- `2w`, two weeks
- `4w`, four weeks

## Agile: Daily Duration, Selection

Allowed daily durations:

- `5m`, five minutes
- `10m`, ten minutes
- `20m`, twenty minutes

## Decision Aid

- `1w + 5m`: high dynamics, small teams, fast feedback cycle.
- `2w + 10m`: standard for mixed subject/Ops teams.
- `4w + 20m`: high regulatory review share, longer planning windows.

## Kanban: Review Cadence, Selection

Allowed review cadences:

- `1w`, weekly
- `2w`, biweekly
- `4w`, monthly review cycle

## Kanban: Sync Duration, Selection

Allowed sync durations:

- `5m`
- `10m`
- `20m`

Recommendation:

- daily short sync in `5m|10m|20m`,
- Kanban review at `1w|2w|4w`,
- replenishment together with the review or as a separate short meeting.

## Binding Documentation Per Team

Every team documents in the organization fork:

- chosen working method: `agile` or `kanban`,
- for `agile`: sprint duration and daily duration,
- for `kanban`: review cadence and sync duration,
- start date of the cadence,
- responsible role for adjustments.

## Adjustment Rule

- Cadence changes happen only through change request.
- Effect is evaluated after one or two cycles.
- After approval, the new cadence is adopted in a versioned way.
