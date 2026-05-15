# Usecase Gantt

Last update: 2026-05-15

```mermaid
gantt
    title Notary usecase delivery plan
    dateFormat  YYYY-MM-DD
    axisFormat  %Y-%m

    section Intake
    GitHub repository scan                      :done,   u1, 2026-05-14, 1d
    Create canonical usecase root              :done,   u2, 2026-05-14, 1d

    section Priority usecases
    Top-10 notarial usecase baseline           :done,   u3, 2026-05-15, 1d
    Static KG binding for Top-10 cases         :done,   u4, 2026-05-15, 1d
    Online GmbH formation                      :active, u5, 2026-05-14, 28d
    AO52 nonprofit software company            :active, u6, 2026-05-14, 28d
    Steuer-aaS tax readiness                   :active, u7, 2026-05-14, 28d
    Immobilienkaufvertrag and Grundschuld      :active, u8, 2026-05-15, 28d
    Testament and Nachlass cases               :active, u9, 2026-05-15, 28d
    Vorsorge, Schenkung and Ehevertrag cases   :active, u10, 2026-05-15, 35d

    section Pilot readiness
    Bind usecases to plugin dependencies        :        u11, 2026-06-15, 28d
    Bind usecases to workflow contracts         :        u12, after u11, 28d
    KG-fed workflow state updates               :        u13, after u12, 28d
    Pilot package review                        :        u14, after u13, 21d
```

## Status

| Usecase | Folder | Status | Source |
| --- | --- | --- | --- |
| Top-10 notarial usecase baseline | `usecases/*/` plus `knowledge-graph/notarial-top10.graph.json` | Done | Created canonical usecase folders and KG nodes for the ten most important notarial case types. |
| Online GmbH-/UG-Gruendung | `usecases/online-gmbh-gruendung/` | Active | Canonicalized from the empty GitHub repo `ofunk/Online-GmbH-Gruendung`; now part of the Top-10 KG. |
| AO52 nonprofit software company | `usecases/ao52aas-gemeinnuetzigkeit/` | Active | Migrated from `ofunk/AO52aaS`. |
| Steuer-aaS tax readiness | `usecases/steuer-aas/` | Active | Canonicalized from the empty GitHub repo `ofunk/Steuer-aaS`. |
| Immobilienkaufvertrag | `usecases/immobilienkaufvertrag/` | KG baseline | New canonical Top-10 usecase in this repository. |
| Grundschuld / Hypothekenbestellung | `usecases/grundschuld-hypothekenbestellung/` | KG baseline | New canonical Top-10 usecase in this repository. |
| Handelsregisteranmeldung | `usecases/handelsregisteranmeldung/` | KG baseline | New canonical Top-10 usecase in this repository. |
| Beglaubigung von Unterschriften | `usecases/unterschriftsbeglaubigung/` | KG baseline | New canonical Top-10 usecase in this repository. |
| Testament / Erbvertrag | `usecases/testament-erbvertrag/` | KG baseline | New canonical Top-10 usecase in this repository. |
| Erbscheinsantrag / Nachlass | `usecases/erbscheinsantrag-nachlass/` | KG baseline | New canonical Top-10 usecase in this repository. |
| Vorsorgevollmacht und Patientenverfuegung | `usecases/vorsorgevollmacht-patientenverfuegung/` | KG baseline | New canonical Top-10 usecase in this repository. |
| Schenkungsvertrag / Uebertragungsvertrag | `usecases/schenkungsvertrag-uebertragungsvertrag/` | KG baseline | New canonical Top-10 usecase in this repository. |
| Ehevertrag / Scheidungsfolgenvereinbarung | `usecases/ehevertrag-scheidungsfolgenvereinbarung/` | KG baseline | New canonical Top-10 usecase in this repository. |

## Plugin-Classified Sources

| Source | Decision |
| --- | --- |
| `ofunk/IDaaS` | Migrated as `plugins/noc-idaas/`, not as a usecase. |

## KG Rule

The Top-10 KG is now a required strict quality-gate artifact. Every KG update
must keep all case `value` fields empty in Git and must update this Gantt plus
the global Gantt when pushed.
