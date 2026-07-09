# Deep-Process-Kandidatenrouting

Dieses Routing leitet aus dem Geschäftsvorfall-Inventar und dem
Ontologie-Sizing-/Storage-Vertrag ab, welche Vorgangsarten als Nächstes tief
in BPMN und Ontologie-Projektion modelliert werden sollten.

## Entscheidung

Alle vorhandenen Geschäftsvorfälle werden für Sizing berücksichtigt. Tiefe
Modellierung wird aber nicht für alle Fälle gleichzeitig erzwungen. Das
Routing bildet stattdessen Lanes:

| Lane | Bedeutung |
| --- | --- |
| `first_wave_deep_process` | sofort sinnvoller Kandidat für BPMN-Outline, Ontologie-Projektionsplan und Verification Contract |
| `archetype_review` | repräsentativer Fall, zuerst gegen First-Wave-Archetypen vergleichen |
| `candidate_backlog` | fachlicher Kandidat, nach Domäne bündeln |
| `legacy_alias_dedupe` | historischer Alias, vor tiefer Modellierung auf kanonischen Slug abbilden |
| `thin_catalog_only` | zunächst nur im dünnen Katalog halten |

Der maschinenlesbare Nachweis kommt aus
`nac kg deep-process-candidates --format json`.

## Grenzen

Das Routing ist offline-only:

- keine Microsoft-Graph-Requests
- keine SharePoint-Schreiboperationen
- keine SharePoint-Schemaänderung
- keine Dokumentinhaltslesung
- keine Mandatswerte in Git oder Ontologie
- keine Runtime-Reasoning-Pflicht im Nutzerpfad

SharePoint bleibt operative M365-MVP-Datenhaltung. Die Ontologie bleibt ein
versionierter Projektionsvertrag über den usecase-lokalen Knowledge Graphs.
BPMN bleibt Prozessmodell und Review-Oberfläche, keine Workflow-Engine.

## Validierung

Der Validator
[scripts/validate_notarial_deep_process_candidate_routing.py](../../../scripts/validate_notarial_deep_process_candidate_routing.py)
prüft, dass High-/Medium-Komplexitätsfälle als Kandidaten erkannt werden,
First-Wave-Fälle begrenzt bleiben und Legacy-Aliase zuerst dedupliziert werden.
Der Check läuft im strikten Quality Gate als
`notarial_deep_process_candidate_routing`.
