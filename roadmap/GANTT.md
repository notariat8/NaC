# NoC Global Gantt

Last update: 2026-05-14

Every push must update this global Gantt. Changes under `plugins/`,
`workflows/`, or `usecases/` must also update the matching area Gantt:

- `plugins/GANTT.md`
- `workflows/GANTT.md`
- `usecases/GANTT.md`

```mermaid
gantt
    title NoC global delivery plan
    dateFormat  YYYY-MM-DD
    axisFormat  %Y-%m

    section A: Plugins and marketplace readiness
    Plugin inventory and installability gate     :done,    a1, 2026-04-01, 2026-05-14
    GPT Store and workspace packaging split      :active,  a2, 2026-05-14, 21d
    Notary pilot plugin readiness                :         a3, after a2, 35d
    Publication and support operations           :         a4, after a3, 28d

    section B: Notary workflows
    Workflow layer separation                    :active,  b1, 2026-05-14, 14d
    Skill plus Python workflow contracts         :         b2, after b1, 28d
    Deterministic workflow runner MVP            :         b3, after b2, 35d
    Day2 evidence and drift operations           :         b4, after b3, 28d

    section C: Notary usecases
    GitHub usecase intake                        :done,    c1, 2026-05-14, 1d
    GmbH formation canonicalization              :active,  c2, 2026-05-14, 21d
    Purchase contract and testament starters     :         c3, after c2, 28d
    Pilot-ready usecase packages                 :         c4, after c3, 35d
```

## Progress Snapshot

| Track | Scope | Status | Progress | Current gate |
| --- | --- | --- | --- | --- |
| A | Installable plugins for notary offices | Active | 35% | Publish track must separate public GPT Store packages from workspace-only apps. |
| B | Installable skills and deterministic Python workflows | Active | 10% | Workflow root and execution boundaries are now explicit. |
| C | Notarial usecases such as GmbH formation, purchase contract, testament | Active | 15% | GitHub intake identified `ofunk/Online-GmbH-Gruendung` as the first canonical usecase. |

## Rule

The strict quality gate includes `scripts/validate_gantt_progress.py`. A change
set that does not update `roadmap/GANTT.md` is not push-ready. A change set that
touches `plugins/`, `workflows/`, or `usecases/` must update the matching area
Gantt as well.
