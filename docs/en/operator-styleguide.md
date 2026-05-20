# NaC Operator Style Guide

Status: first version for consistent office navigation on 2026-05-20

## Purpose

The operator web app is an office work surface for the notary, not a
documentation page and not an unrestricted modeling tool. Every view must make
clear:

- where the user is,
- how to return to the overview,
- which actions are daily matter work,
- which actions affect office master data or approval-bound changes,
- which workflow and checklist version a matter is bound to.

The design follows [WCAG 2.2 consistent navigation](https://www.w3.org/TR/WCAG22/#consistent-navigation)
and public-service patterns such as [GOV.UK Service Navigation](https://design-system.service.gov.uk/components/service-navigation/)
and [Navigate a service](https://design-system.service.gov.uk/patterns/navigate-a-service/).

## Navigation Rule

Every work view outside the overview gets a simple text navigation at the top:

- `← Zurück` returns to the previous app view.
- `Übersicht` always returns to the case overview.

This navigation is not a large action button. It is orientation and escape
path. Primary buttons are reserved for subject-matter actions.

## Action Hierarchy

Case cards are always split into three blocks:

| Block | Visibility | Purpose | Audience |
| --- | --- | --- | --- |
| `Aktenverwaltung` | always open | open matters, create a new demo matter, see status counters | daily office work, all authorized users |
| `Kontrolle` | always open, but secondary | inspect the checklist | clerks, notary, quality review |
| `Kanzlei-Workflow` | collapsed | view flow, propose a change | notary, process owners, review |

`Akten öffnen` is the primary daily action. `Neu` is secondary because users
should first check whether a matter or inbox item already exists. `Checkliste
prüfen` is visible in daily office work but is not equal to matter management.
`Ablauf ansehen` and `Änderung vorschlagen` are not daily matter actions; they
affect approved office master data.

The checklist is therefore not just a use-case template. The use-case template
defines the control points. When a matter starts, a matter-specific checklist
state is created from that template. The matter view shows the next open step,
open items and completed items from exactly that matter-specific state.

## Workflow As Office Master Data

A workflow does not belong to one matter. It belongs to the approved office
standard for each use case. It includes at least:

- BPMN flow,
- KG/checklist artifact,
- version, for example `v1`,
- tamper-evident hash of the approved artifacts,
- approval state and approval role.

A flow change is therefore a change to the office workflow. It must not happen
casually from inside a matter. The expected path is:

1. Propose a change.
2. Run validation and subject-matter review.
3. The notary or process owner approves a new version.
4. New matters use the new version from then on.
5. Running matters stay on their bound version until a documented version
   migration is recorded.

## Matter Binding

Every matter receives `workflow_binding` metadata when it is created. This
binds the matter to:

- `workflow_id`,
- `workflow_version`,
- `workflow_revision_hash`,
- BPMN and checklist artifacts with SHA-256,
- binding timestamp,
- the rule that the matter stays on this version.

This lets a matter started on `Unterschriftsbeglaubigung v1` keep running on
`v1` even after `v2` is approved. Moving it to `v2` is a separate matter
decision and must be recorded as an event.

The current MVP binds matters to `v1` plus a hash of the available BPMN and
checklist artifacts. Productive office operation additionally needs an
approval registry per office and use case with version, approval timestamp,
approval role, approving person, effective date and replacement rule. This is
tracked in the global Gantt as `Kanzlei-Workflow-Freigaberegister bauen`.

## Matter-Specific Checklist

Every matter additionally receives a `checkliste.json` file. This file is the
case state of the checklist, not only a link to the template. It contains:

- the bound workflow version,
- the hash of the KG checklist template,
- the sections `Offene Angaben`, `Dokumente`, `Entscheidungen`, `Prüfgates`
  and `Nachweise`,
- status per control step,
- the next open step for the matter overview.

Later changes to the office template do not change this matter checklist
automatically. Moving a matter to a newer version requires its own matter
event.

## Button Rules

- Each context has at most one primary button.
- The primary button is only the next normal daily action.
- Secondary buttons complement the daily action.
- Governance actions are grouped in a named area and are not placed next to
  daily actions.
- Links to read-only views remain recognizable as links or secondary actions.
- Write or approval-relevant actions need a status message, validation and a
  review path.

## Terms

The UI uses office terms:

- `Übersicht` instead of a technical start point,
- `Aktenverwaltung` for opening and creating matters,
- `Kontrolle` for checklist inspection,
- `Kanzlei-Workflow` for flow and editing,
- `Änderung vorschlagen` instead of direct editing when master data is
  affected.
