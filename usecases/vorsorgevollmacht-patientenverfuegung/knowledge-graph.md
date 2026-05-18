# Vorsorgevollmacht und Patientenverfügung Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `top10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.vorsorgevollmacht_patientenverfuegung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `principal.identity` | Vollmachtgeber Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Vollmachtgeber Identität benötigt? |
| `agent.identities` | Bevollmaechtigter Identitäten | `offen` | Vollmachtgeber | Welche Angaben, Nachweise und Prüfpunkte werden für Bevollmaechtigter Identitäten benötigt? |
| `authority.financial` | Berechtigung Finanzen | `offen` | Vollmachtgeber | Welche Angaben, Nachweise und Prüfpunkte werden für Berechtigung Finanzen benötigt? |
| `authority.health` | Berechtigung Gesundheit | `offen` | Vollmachtgeber | Welche Angaben, Nachweise und Prüfpunkte werden für Berechtigung Gesundheit benötigt? |
| `patient.directive` | Patientenverfügung Verfügung | `offen` | Vollmachtgeber | Welche Angaben, Nachweise und Prüfpunkte werden für Patientenverfügung Verfügung benötigt? |
| `effectiveness.rules` | Wirksamkeit Regeln | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Wirksamkeit Regeln benötigt? |
| `self_dealing.release` | Befreiung von Selbstkontrahierung und Untervollmacht | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Befreiung von Selbstkontrahierung und Untervollmacht benötigt? |
| `central_register` | Zentrales Vorsorgeregister | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Zentrales Vorsorgeregister benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.power_of_attorney_draft` | Dokument: Vollmacht von Vollmacht Entwurf | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.patient_directive_draft` | Dokument: Patientenverfügung Verfügung Entwurf | `offen` | nach Prüfung erzeugter Workflow-Entwurf |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.instrument_scope` | Entscheidung: Instrument Umfang | `offen` |
| `decision.register` | Entscheidung: Register | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.capacity_review` | Prüfgate: Geschäftsfähigkeit Prüfung | `offen` |
| `gate.health_scope_review` | Prüfgate: Gesundheit Umfang Prüfung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.capacity_and_instruction` | Nachweis: Geschäftsfähigkeit and Anweisung | `offen` |
| `evidence.copy_register_trace` | Nachweis: Ausfertigung Register Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
