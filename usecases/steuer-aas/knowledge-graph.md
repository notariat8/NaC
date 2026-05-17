# Steuer-aaS Steuer-Readiness Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `active-intake`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.steuer_aas`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `tax.subject` | Steuer Subjekt | `offen` | Steuer-Sachbearbeitung | Welche Angaben, Nachweise und Pruefpunkte werden fuer Steuer Subjekt benoetigt? |
| `tax.type` | Steuer Art | `offen` | Steuer-Sachbearbeitung | Welche Angaben, Nachweise und Pruefpunkte werden fuer Steuer Art benoetigt? |
| `period.scope` | Zeitraum Umfang | `offen` | Steuer-Sachbearbeitung | Welche Angaben, Nachweise und Pruefpunkte werden fuer Zeitraum Umfang benoetigt? |
| `elster.identity` | ELSTER Identitaet | `offen` | Systembetreuung | Welche Angaben, Nachweise und Pruefpunkte werden fuer ELSTER Identitaet benoetigt? |
| `documents.package` | Dokumente Paket | `offen` | Steuer-Sachbearbeitung | Welche Angaben, Nachweise und Pruefpunkte werden fuer Dokumente Paket benoetigt? |
| `audit.evidence` | Pruefung Nachweis | `offen` | Compliance | Welche Angaben, Nachweise und Pruefpunkte werden fuer Pruefung Nachweis benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.intake_package` | Dokument: Intake Paket | `offen` |  |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.workflow_route` | Entscheidung: Workflow Route | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.identity` | Pruefgate: Identitaet | `offen` |
| `gate.notarial_review` | Pruefgate: Notariell Pruefung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.git_review` | Nachweis: Git Pruefung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
