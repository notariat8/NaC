# Workflow Gantt

Last update: 2026-05-15

```mermaid
gantt
    title Workflow delivery plan
    dateFormat  YYYY-MM-DD
    axisFormat  %Y-%m

    section Architecture
    Separate workflow root from plugins         :done,   w1, 2026-05-14, 1d
    Define skill and Python workflow boundary   :done,   w2, 2026-05-14, 14d
    KG runtime status CLI MVP                   :done,   w3, 2026-05-15, 1d
    Usecase-local KG runtime binding            :done,   w3a, 2026-05-15, 1d
    Add workflow contract format                :active, w4, 2026-05-15, 21d

    section Execution
    Skill scaffolds for notary workflows        :        w5, 2026-06-01, 28d
    Python deterministic workflow MVP           :active, w6, 2026-05-15, 35d
    Evidence and replay checks                  :        w7, after w6, 28d

    section Operations
    Review and approval gates                   :        w8, 2026-06-15, 28d
    Day2 drift handling                         :        w9, after w8, 28d
```

## Status

| Layer | Root | Status | Boundary |
| --- | --- | --- | --- |
| Installable skills | `workflows/skills/` | Planned | LLM-facing operational guidance, no final legal truth. |
| Python workflows | `workflows/python/` plus `src/notary_kg/` | Active | Deterministic KG status runtime now reads usecase-local KG files; next step is contract generation. |
| Workflow contracts | `workflows/contracts/` | Active next | Inputs, outputs, approvals, data classes, and plugin dependencies. |
