# Workflow Gantt

Letzte Aktualisierung: 2026-06-12

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
    Legal-Research-Kandidatenvertrag           :done,   w4k, 2026-05-22, 1d
    GNotKG-Kostenvertrag und Reviewgraph        :done,   w4l, 2026-05-28, 1d
    Legal-Graph-MVP-Domänenpilot              :active, w4m, 2026-06-12, 7d
    Legal-Nemotron-Readiness-Vertrag            :done,   w4s, 2026-06-28, 1d
    On-Prem-Connector-Grenzvertrag            :done,   w4n, 2026-06-28, 1d
    Mandatsdaten-Redaktionsvertrag             :done,   w4o, 2026-06-28, 1d
    Privater Betriebsrahmen-Gatevertrag        :done,   w4p, 2026-06-28, 1d
    Private-Payload-Zielarchitektur            :done,   w4q, 2026-06-28, 1d
    Private-Payload-Zugriffsmatrix             :done,   w4r, 2026-06-28, 1d

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
| Python-Workflows | `workflows/python/` plus `src/notary_kg/`, `src/nac_legal_graph/` und `src/nac_cli/` | Aktiv | Die deterministische KG-Status-Runtime liest usecase-lokale KG-Dateien; der Legal-Graph-Pilot erzeugt nur Review-Patches aus metadata-only Primärquellenmanifesten für Erbrecht, Familienrecht und Gesellschaftsrecht ohne Kommentarzugriff. Beides ist über die zentrale `nac`-CLI zusammen mit Prozess-, BPMN-, Plugin-Fachprüfungs-, Konfigurations-, Webserver- und Quality-Gate-Befehlen erreichbar. |
| BPMN-js Business Layer | `bpmn/` plus `workflows/contracts/bpmn-js-editor.contract.json` | Nutzbarer MVP | BPMN ist fachliche Prozessquelle; alle Usecases haben bpmn-js-taugliche Basismodelle mit `nac:channel`, Python validiert NaC-Properties, Sequenzflüsse und Diagrammflächen. |
| GNotKG-Kostenmodul | `src/nac_gnotkg/` plus `workflows/contracts/gnotkg-cost-review.contract.json` | Nutzbarer MVP | Zentrale Wertgebührenlogik mit GNotKG § 35-Höchstwerten, mandatsdatenfreier Reviewgraph und `xyflow` als reine Visualisierungsschicht. |
| Lokaler Webserver | `src/nac_web/` plus `scripts/nac_web.py` | Heute nutzbar | Zeigt BPMN-SVG, BPMN-JSON, BPMN-XML/Editierfläche, KG-Editor-Views, GNotKG-Kostenansichten und KG-JSON lokal im Browser; BPMN-Speichern nutzt SHA-256-Konfliktprüfung, GNotKG-Quotes laufen per POST. |
| Workflow-Verträge | `workflows/contracts/` | Aktiv | Eingaben, Ausgaben, Freigaben, Datenklassen, Plugin-Abhängigkeiten sowie KG-Editor-, BPMN-js-Editor-, GNotKG-Kosten-, lokaler Webpreview-, Secure-Document-Link-, Legal-Research-Connector-Kandidaten-, Legal-Graph-, Legal-Nemotron-Readiness-, Kommentar-Connector-, NaC-On-Prem-Agent-Runtime-, On-Prem-Connector-Grenz-, Mandatsdaten-Redaktions-, privater Betriebsrahmen-Gate-, Private-Payload-Ziel- und Zugriffsmatrixvertrag. Kommentar-, Legal-Nemotron-, On-Prem-Connector-, Mandatsdaten- und Private-Payload-Verträge bleiben vor produktivem Zugriff durch Lizenzbasis-, AVV-/DPA-, Berufsgeheimnis-, AI-SBOM-, Sicherheitsgrenzen-, Credential-, Testmodus-, Privacy-, Benchmark-, Evaluation-, Model-Card-, Rollen-, Zweck-, Speicher-, Retention-, Verschlüsselungs- und Owner-Gates blockiert. |

Der repo-weite Marken- und ID-Standard heißt `NaC` für `Notariat as Code`;
alte Schreibweisen sind in Workflow-Dokumenten nicht mehr
zulässig.
Deutsche Menschentexte nutzen echte Umlaute; technische IDs, Pfade und Befehle
bleiben ASCII-stabil.
