# Workflow Gantt

Letzte Aktualisierung: 2026-05-19

```mermaid
gantt
    title Workflow-Lieferplan
    dateFormat  YYYY-MM-DD
    axisFormat  %Y-%m

    section Architektur
    Workflow-Root von Plugins trennen          :done,   w1, 2026-05-14, 1d
    Skill- und Python-Workflow-Grenze klären  :done,   w2, 2026-05-14, 14d
    KG-Runtime-Status-CLI-MVP                  :done,   w3, 2026-05-15, 1d
    Usecase-lokale KG-Runtime-Bindung          :done,   w3a, 2026-05-15, 1d
    No-code-KG-Editor-View-Vertrag             :done,   w4a, 2026-05-15, 1d
    Deutsche Workflow-MD-Sprachführung        :done,   w4b, 2026-05-17, 1d
    Skill-Sprachregel und EN-Summary            :done,   w4c, 2026-05-17, 1d
    NaC-Namenskonvention in Workflows           :done,   w4d, 2026-05-18, 1d
    Deutsche Umlautpflicht in Workflows         :done,   w4e, 2026-05-18, 1d
    BPMN-js Business-Layer-Profil               :done,   w4f, 2026-05-19, 1d
    Lokalen Webserver für Grafikflächen bauen  :done,   w4g, 2026-05-19, 1d
    Zentrale NaC-CLI-Bedienkante                :done,   w4h, 2026-05-19, 1d
    Plugin-Fachprüfungen in nac-CLI             :done,   w4i, 2026-05-19, 1d
    BPMN-Editor-Speichervertrag                 :done,   w4j, 2026-05-19, 1d
    Workflow-Vertragsformat ergänzen          :active, w4, 2026-05-15, 21d

    section Ausführung
    Skill-Scaffolds für Notariatsworkflows    :        w5, 2026-06-01, 28d
    Deterministisches Python-Workflow-MVP      :active, w6, 2026-05-15, 35d
    BPMN-Modellvalidierung im Quality Gate      :done,   w6a, 2026-05-19, 1d
    Nachweis- und Replay-Prüfungen            :        w7, after w6, 28d

    section Betrieb
    Review- und Freigabe-Gates                 :        w8, 2026-06-15, 28d
    Day2-Drift-Behandlung                      :        w9, after w8, 28d
```

## Status

| Schicht | Root | Status | Grenze |
| --- | --- | --- | --- |
| Installierbare Skills | `workflows/skills/` | Geplant / Sprachregel bereit | Deutsche fachliche Anweisung führt; englische Summary dient technischer Anschlussfähigkeit, keine finale rechtliche Wahrheit. |
| Python-Workflows | `workflows/python/` plus `src/notary_kg/` und `src/nac_cli/` | Aktiv | Die deterministische KG-Status-Runtime liest usecase-lokale KG-Dateien und ist über die zentrale `nac`-CLI zusammen mit Prozess-, BPMN-, Plugin-Fachprüfungs-, Konfigurations-, Webserver- und Quality-Gate-Befehlen erreichbar. |
| BPMN-js Business Layer | `bpmn/` plus `workflows/contracts/bpmn-js-editor.contract.json` | Nutzbarer MVP | BPMN ist fachliche Prozessquelle; alle Usecases haben bpmn-js-taugliche Basismodelle mit `nac:channel`, Python validiert NaC-Properties, Sequenzflüsse und Diagrammflächen. |
| Lokaler Webserver | `src/nac_web/` plus `scripts/nac_web.py` | Heute nutzbar | Zeigt BPMN-SVG, BPMN-JSON, BPMN-XML/Editierfläche, KG-Editor-Views und KG-JSON lokal im Browser; BPMN-Speichern nutzt SHA-256-Konfliktprüfung. |
| Workflow-Verträge | `workflows/contracts/` | Aktiv | Eingaben, Ausgaben, Freigaben, Datenklassen, Plugin-Abhängigkeiten sowie KG-Editor-, BPMN-js-Editor- und lokaler Webpreview-Vertrag. |

Der repo-weite Marken- und ID-Standard heißt `NaC` für `Notariat as Code`;
alte Schreibweisen sind in Workflow-Dokumenten nicht mehr
zulässig.
Deutsche Menschentexte nutzen echte Umlaute; technische IDs, Pfade und Befehle
bleiben ASCII-stabil.
