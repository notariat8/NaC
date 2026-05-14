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
    IDaaS plugin migration                       :active,  a3, 2026-05-14, 14d
    Repository consolidation ledger              :active,  a4, 2026-05-14, 7d
    Notary pilot plugin readiness                :         a5, after a4, 35d
    Publication and support operations           :         a6, after a5, 28d

    section B: Notary workflows
    Workflow layer separation                    :active,  b1, 2026-05-14, 14d
    Skill plus Python workflow contracts         :         b2, after b1, 28d
    Deterministic workflow runner MVP            :         b3, after b2, 35d
    Day2 evidence and drift operations           :         b4, after b3, 28d

    section C: Notary usecases
    GitHub usecase intake                        :done,    c1, 2026-05-14, 1d
    GmbH formation canonicalization              :active,  c2, 2026-05-14, 21d
    AO52 nonprofit formation intake              :active,  c3, 2026-05-14, 21d
    Steuer-aaS tax usecase intake                :active,  c4, 2026-05-14, 21d
    Purchase contract and testament starters     :         c5, after c4, 28d
    Pilot-ready usecase packages                 :         c6, after c5, 35d
```

## Progress Snapshot

| Track | Scope | Status | Progress | Current gate |
| --- | --- | --- | --- | --- |
| A | Installable plugins for notary offices | Active | 54% | `noc-cyberjack-rfid` now includes Linux driver/PCSC/USB preflight; Omnistation testing needs USB passthrough and a policy exception before driver installation. |
| B | Installable skills and deterministic Python workflows | Active | 10% | Workflow root and execution boundaries are now explicit. |
| C | Notarial usecases such as GmbH formation, AO52 nonprofit formation, tax readiness, purchase contract, testament | Active | 22% | GitHub intake identified `ofunk/Online-GmbH-Gruendung`, `ofunk/AO52aaS`, and `ofunk/Steuer-aaS` as canonical usecase sources. |

## Rule

The strict quality gate includes `scripts/validate_gantt_progress.py`. A change
set that does not update `roadmap/GANTT.md` is not push-ready. A change set that
touches `plugins/`, `workflows/`, or `usecases/` must update the matching area
Gantt as well.
