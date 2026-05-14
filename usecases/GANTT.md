# Usecase Gantt

Last update: 2026-05-14

```mermaid
gantt
    title Notary usecase delivery plan
    dateFormat  YYYY-MM-DD
    axisFormat  %Y-%m

    section Intake
    GitHub repository scan                      :done,   u1, 2026-05-14, 1d
    Create canonical usecase root              :done,   u2, 2026-05-14, 1d

    section Priority usecases
    Online GmbH formation                       :active, u3, 2026-05-14, 28d
    Real-estate purchase contract              :        u4, after u3, 28d
    Testament                                  :        u5, after u4, 21d

    section Pilot readiness
    Bind usecases to plugin dependencies        :        u6, 2026-06-15, 28d
    Bind usecases to workflow contracts         :        u7, after u6, 28d
    Pilot package review                        :        u8, after u7, 21d
```

## Status

| Usecase | Folder | Status | Source |
| --- | --- | --- | --- |
| Online GmbH formation | `usecases/online-gmbh-gruendung/` | Active | Canonicalized from the empty GitHub repo `ofunk/Online-GmbH-Gruendung`. |
| Real-estate purchase contract | `usecases/grundstueckskaufvertrag/` | Planned | New canonical starter in this repository. |
| Testament | `usecases/testament/` | Planned | New canonical starter in this repository. |
