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
    AO52 nonprofit software company            :active, u4, 2026-05-14, 28d
    Steuer-aaS tax readiness                    :active, u5, 2026-05-14, 28d
    Real-estate purchase contract              :        u6, after u5, 28d
    Testament                                  :        u7, after u6, 21d

    section Pilot readiness
    Bind usecases to plugin dependencies        :        u8, 2026-06-15, 28d
    Bind usecases to workflow contracts         :        u9, after u8, 28d
    Pilot package review                        :        u10, after u9, 21d
```

## Status

| Usecase | Folder | Status | Source |
| --- | --- | --- | --- |
| Online GmbH formation | `usecases/online-gmbh-gruendung/` | Active | Canonicalized from the empty GitHub repo `ofunk/Online-GmbH-Gruendung`. |
| AO52 nonprofit software company | `usecases/ao52aas-gemeinnuetzigkeit/` | Active | Migrated from `ofunk/AO52aaS`. |
| Steuer-aaS tax readiness | `usecases/steuer-aas/` | Active | Canonicalized from the empty GitHub repo `ofunk/Steuer-aaS`. |
| Real-estate purchase contract | `usecases/grundstueckskaufvertrag/` | Planned | New canonical starter in this repository. |
| Testament | `usecases/testament/` | Planned | New canonical starter in this repository. |
