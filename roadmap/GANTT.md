# NoC Global Gantt

Last update: 2026-05-15

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
    PKCS7 local certificate-bundle evidence      :active,  a4a, 2026-05-15, 14d
    SBOM for AI governance baseline              :active,  a4b, 2026-05-15, 21d
    Notary pilot plugin readiness                :         a5, after a4, 35d
    Publication and support operations           :         a6, after a5, 28d

    section B: Notary workflows
    Workflow layer separation                    :active,  b1, 2026-05-14, 14d
    KG runtime status CLI MVP                    :done,    b1a, 2026-05-15, 1d
    Skill plus Python workflow contracts         :active,  b2, 2026-05-15, 28d
    Deterministic workflow runner MVP            :active,  b3, 2026-05-15, 35d
    Day2 evidence and drift operations           :         b4, after b3, 28d

    section C: Notary usecases
    GitHub usecase intake                        :done,    c1, 2026-05-14, 1d
    Top-10 notarial KG baseline                  :done,    c2, 2026-05-15, 1d
    Next-10 notarial KG baseline                 :done,    c3, 2026-05-15, 1d
    GmbH formation canonicalization              :active,  c4, 2026-05-14, 21d
    AO52 nonprofit formation intake              :active,  c5, 2026-05-14, 21d
    Steuer-aaS tax usecase intake                :active,  c6, 2026-05-14, 21d
    Static KG-fed workflow state model           :active,  c7, 2026-05-15, 28d
    Pilot-ready usecase packages                 :         c8, after c7, 35d
```

## Progress Snapshot

| Track | Scope | Status | Progress | Current gate |
| --- | --- | --- | --- | --- |
| A | Installable plugins for notary offices | Active | 64% | `noc-cyberjack-rfid` now detects REINER SCT DriverPackage, morris browser middleware and the optional morris loopback API/PCSC path locally; `noc-pkcs7-certbundle` adds a separate local certificate-bundle evidence track without signing; OpenAI-backed processing has an AVV/DPA governance section; and SBOM for AI now has a repo-wide baseline, draft artifact and strict validator. |
| B | Installable skills and deterministic Python workflows | Active | 24% | First executable KG runtime package and CLI are implemented with unit tests; next step is KG-to-contract generation. |
| C | Notarial usecases such as property, register, company, association, estate, family and power-of-attorney matters | Active | 52% | Top-10 and Next-10 usecase catalogs now exist with static KG nodes, detailed usecase folders and a strict KG validator. |

## Rule

The strict quality gate includes `scripts/validate_gantt_progress.py`. A change
set that does not update `roadmap/GANTT.md` is not push-ready. A change set that
touches `plugins/`, `workflows/`, or `usecases/` must update the matching area
Gantt as well.
