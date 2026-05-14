# Workflow Gantt

Last update: 2026-05-14

```mermaid
gantt
    title Workflow delivery plan
    dateFormat  YYYY-MM-DD
    axisFormat  %Y-%m

    section Architecture
    Separate workflow root from plugins         :done,   w1, 2026-05-14, 1d
    Define skill and Python workflow boundary   :active, w2, 2026-05-14, 14d
    Add workflow contract format                :        w3, after w2, 21d

    section Execution
    Skill scaffolds for notary workflows        :        w4, 2026-06-01, 28d
    Python deterministic workflow MVP           :        w5, after w4, 35d
    Evidence and replay checks                  :        w6, after w5, 28d

    section Operations
    Review and approval gates                   :        w7, 2026-06-15, 28d
    Day2 drift handling                         :        w8, after w7, 28d
```

## Status

| Layer | Root | Status | Boundary |
| --- | --- | --- | --- |
| Installable skills | `workflows/skills/` | Planned | LLM-facing operational guidance, no final legal truth. |
| Python workflows | `workflows/python/` | Planned | Deterministic execution, validation, idempotency, evidence metadata. |
| Workflow contracts | `workflows/contracts/` | Planned | Inputs, outputs, approvals, data classes, and plugin dependencies. |
