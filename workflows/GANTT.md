# Workflow Gantt

Letzte Aktualisierung: 2026-05-17

```mermaid
gantt
    title Workflow-Lieferplan
    dateFormat  YYYY-MM-DD
    axisFormat  %Y-%m

    section Architektur
    Workflow-Root von Plugins trennen          :done,   w1, 2026-05-14, 1d
    Skill- und Python-Workflow-Grenze klaeren  :done,   w2, 2026-05-14, 14d
    KG-Runtime-Status-CLI-MVP                  :done,   w3, 2026-05-15, 1d
    Usecase-lokale KG-Runtime-Bindung          :done,   w3a, 2026-05-15, 1d
    No-code-KG-Editor-View-Vertrag             :done,   w4a, 2026-05-15, 1d
    Deutsche Workflow-MD-Sprachfuehrung        :done,   w4b, 2026-05-17, 1d
    Skill-Sprachregel und EN-Summary            :done,   w4c, 2026-05-17, 1d
    Workflow-Vertragsformat ergaenzen          :active, w4, 2026-05-15, 21d

    section Ausfuehrung
    Skill-Scaffolds fuer Notariatsworkflows    :        w5, 2026-06-01, 28d
    Deterministisches Python-Workflow-MVP      :active, w6, 2026-05-15, 35d
    Nachweis- und Replay-Pruefungen            :        w7, after w6, 28d

    section Betrieb
    Review- und Freigabe-Gates                 :        w8, 2026-06-15, 28d
    Day2-Drift-Behandlung                      :        w9, after w8, 28d
```

## Status

| Schicht | Root | Status | Grenze |
| --- | --- | --- | --- |
| Installierbare Skills | `workflows/skills/` | Geplant / Sprachregel bereit | Deutsche fachliche Anweisung fuehrt; englische Summary dient technischer Anschlussfaehigkeit, keine finale rechtliche Wahrheit. |
| Python-Workflows | `workflows/python/` plus `src/notary_kg/` | Aktiv | Die deterministische KG-Status-Runtime liest usecase-lokale KG-Dateien und stellt die sichere No-code-Editor-View bereit. |
| Workflow-Vertraege | `workflows/contracts/` | Aktiv | Eingaben, Ausgaben, Freigaben, Datenklassen, Plugin-Abhaengigkeiten und der implementierte KG-Editor-Vertrag. |
