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
    Next-10 notarial usecase baseline          :done,   u5, 2026-05-15, 1d
    Static KG binding for Next-10 cases        :done,   u6, 2026-05-15, 1d
    Online GmbH formation                      :active, u7, 2026-05-14, 28d
    AO52 nonprofit software company            :active, u8, 2026-05-14, 28d
    Steuer-aaS tax readiness                   :active, u9, 2026-05-14, 28d
    Immobilienkaufvertrag and Grundschuld      :active, u10, 2026-05-15, 28d
    Register, association and company cases    :active, u11, 2026-05-15, 35d
    Family, estate and power cases             :active, u12, 2026-05-15, 35d

    section Pilot readiness
    Bind usecases to plugin dependencies        :        u13, 2026-06-15, 28d
    Bind usecases to workflow contracts         :        u14, after u13, 28d
    KG-fed workflow state updates               :        u15, after u14, 28d
    Pilot package review                        :        u16, after u15, 21d
```

## Status

| Usecase | Folder | Status | Source |
| --- | --- | --- | --- |
| Top-10 notarial usecase baseline | `usecases/*/` plus `knowledge-graph/notarial-top10.graph.json` | Done | Created canonical usecase folders and KG nodes for the ten most important notarial case types. |
| Next-10 notarial usecase baseline | `usecases/*/` plus `knowledge-graph/notarial-next10.graph.json` | Done | Created canonical usecase folders and KG nodes for the next ten frequent notarial case types. |
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
| Loeschungsbewilligung / Grundbuchloeschung | `usecases/loeschungsbewilligung-grundbuchloeschung/` | KG baseline | New canonical Next-10 usecase in this repository. |
| Teilungserklaerung nach WEG | `usecases/teilungserklaerung-weg/` | KG baseline | New canonical Next-10 usecase in this repository. |
| Bautraegervertrag | `usecases/bautraegervertrag/` | KG baseline | New canonical Next-10 usecase in this repository. |
| Gesellschafterbeschluss GmbH/UG | `usecases/gesellschafterbeschluss-gmbh-ug/` | KG baseline | New canonical Next-10 usecase in this repository. |
| Geschaeftsanteilsuebertragung GmbH | `usecases/geschaeftsanteilsuebertragung-gmbh/` | KG baseline | New canonical Next-10 usecase in this repository. |
| Vereinsregisteranmeldung | `usecases/vereinsregisteranmeldung/` | KG baseline | New canonical Next-10 usecase in this repository. |
| Erbausschlagung | `usecases/erbausschlagung/` | KG baseline | New canonical Next-10 usecase in this repository. |
| Pflichtteilsverzicht / Erbverzicht | `usecases/pflichtteilsverzicht-erbverzicht/` | KG baseline | New canonical Next-10 usecase in this repository. |
| Adoption / familienrechtliche Erklaerungen | `usecases/adoption-familienrechtliche-erklaerungen/` | KG baseline | New canonical Next-10 usecase in this repository. |
| Vollmacht fuer Immobilien- oder Gesellschaftsgeschaefte | `usecases/vollmacht-immobilien-gesellschaftsgeschaefte/` | KG baseline | New canonical Next-10 usecase in this repository. |

## Plugin-Classified Sources

| Source | Decision |
| --- | --- |
| `ofunk/IDaaS` | Migrated as `plugins/noc-idaas/`, not as a usecase. |

## KG Rule

The Top-10 and Next-10 KGs are now required strict quality-gate artifacts. Every
KG update must keep all case `value` fields empty in Git and must update this
Gantt plus the global Gantt when pushed.
