# Steuer-aaS Steuer-Readiness Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `active-intake`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.steuer_aas`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `tax.subject` | Steuer Subjekt | `offen` | Steuer-Sachbearbeitung | Welche Angaben, Nachweise und Prüfpunkte werden für Steuer Subjekt benötigt? |
| `tax.type` | Steuer Art | `offen` | Steuer-Sachbearbeitung | Welche Angaben, Nachweise und Prüfpunkte werden für Steuer Art benötigt? |
| `period.scope` | Zeitraum Umfang | `offen` | Steuer-Sachbearbeitung | Welche Angaben, Nachweise und Prüfpunkte werden für Zeitraum Umfang benötigt? |
| `elster.identity` | ELSTER Identität | `offen` | Systembetreuung | Welche Angaben, Nachweise und Prüfpunkte werden für ELSTER Identität benötigt? |
| `documents.package` | Dokumente Paket | `offen` | Steuer-Sachbearbeitung | Welche Angaben, Nachweise und Prüfpunkte werden für Dokumente Paket benötigt? |
| `audit.evidence` | Prüfung Nachweis | `offen` | Compliance | Welche Angaben, Nachweise und Prüfpunkte werden für Prüfung Nachweis benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.intake_package` | Dokument: Intake Paket | `offen` |  |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.workflow_route` | Entscheidung: Workflow Route | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.identity` | Prüfgate: Identität | `offen` |
| `gate.notarial_review` | Prüfgate: Notariell Prüfung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.git_review` | Nachweis: Git Prüfung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
