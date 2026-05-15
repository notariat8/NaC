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
    Runtime and HW minimum requirements SBOM     :active,  a4c, 2026-05-15, 14d
    Notary pilot plugin readiness                :         a5, after a4, 35d
    Publication and support operations           :         a6, after a5, 28d

    section B: Notary workflows
    Workflow layer separation                    :active,  b1, 2026-05-14, 14d
    KG runtime status CLI MVP                    :done,    b1a, 2026-05-15, 1d
    Project voice and active-build docs cleanup  :done,    b1b, 2026-05-15, 1d
    START_HERE operational entry cleanup         :done,    b1c, 2026-05-15, 1d
    Documentation folder taxonomy cleanup        :done,    b1d, 2026-05-15, 1d
    Clickable documentation links rule           :done,    b1e, 2026-05-15, 1d
    Manual-only PDF export during development    :done,    b1f, 2026-05-15, 1d
    Main-merge completion reporting rule         :done,    b1g, 2026-05-15, 1d
    Repo-wide German-leading language rule       :done,    b1h, 2026-05-15, 1d
    Root README language-pair link cleanup       :done,    b1i, 2026-05-15, 1d
    Skill plus Python workflow contracts         :active,  b2, 2026-05-15, 28d
    Deterministic workflow runner MVP            :active,  b3, 2026-05-15, 35d
    Day2 evidence and drift operations           :         b4, after b3, 28d

    section C: Notary usecases
    GitHub usecase intake                        :done,    c1, 2026-05-14, 1d
    Top-10 notarial KG baseline                  :done,    c2, 2026-05-15, 1d
    Next-10 notarial KG baseline                 :done,    c3, 2026-05-15, 1d
    Case-local KG folder migration               :done,    c3a, 2026-05-15, 1d
    German-leading usecase language rule         :done,    c3b, 2026-05-15, 1d
    GmbH formation canonicalization              :active,  c4, 2026-05-14, 21d
    AO52 nonprofit formation intake              :active,  c5, 2026-05-14, 21d
    Steuer-aaS tax usecase intake                :active,  c6, 2026-05-14, 21d
    Static KG-fed workflow state model           :active,  c7, 2026-05-15, 28d
    Pilot-ready usecase packages                 :         c8, after c7, 35d
```

## Progress Snapshot

| Track | Scope | Status | Progress | Current gate |
| --- | --- | --- | --- | --- |
| A | Installable plugins for notary offices | Active | 67% | `noc-cyberjack-rfid` now detects REINER SCT DriverPackage, morris browser middleware and the optional morris loopback API/PCSC path locally; `noc-pkcs7-certbundle` adds a separate local certificate-bundle evidence track without signing; OpenAI-backed processing has an AVV/DPA governance section; and SBOM for AI now has a repo-wide baseline, minimum-requirements inventory and strict validator. |
| B | Installable skills and deterministic Python workflows | Active | 35% | First executable KG runtime package and CLI are implemented with unit tests; `START_HERE` is now the operational entry path distinct from the README overview, startup verification has environment profiles for base, plugin-dev and notary-workstation setups, docs are grouped into `eventstream/`, `issues/`, `operations/` and `service-model/`, README/index references now have clickable-link validation, PDF export is manual-only during active development, `fertig` means merged to `main` plus clean local `main`, and the GitHub root README follows the repo-wide German-leading language rule with paired de/en links. |
| C | Notarial usecases such as property, register, company, association, estate, family and power-of-attorney matters | Active | 54% | Every usecase now owns a case-local static KG; German is explicit as the leading and legally binding language for German-law notarial usecases. |

## Rule

The strict quality gate includes `scripts/validate_gantt_progress.py`. A change
set that does not update `roadmap/GANTT.md` is not push-ready. A change set that
touches `plugins/`, `workflows/`, or `usecases/` must update the matching area
Gantt as well.
