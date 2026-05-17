# AO52 gemeinnuetziges Softwareunternehmen Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `active-intake`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.ao52aas_gemeinnuetzigkeit`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `purpose.model` | Zweck Modell | `offen` | Gruenderkreis | Welche Angaben, Nachweise und Pruefpunkte werden fuer Zweck Modell benoetigt? |
| `entity.form` | Rechtstraeger Form | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Rechtstraeger Form benoetigt? |
| `funding.model` | Finanzierung Modell | `offen` | Gruenderkreis | Welche Angaben, Nachweise und Pruefpunkte werden fuer Finanzierung Modell benoetigt? |
| `governance.rules` | Governance Regeln | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Governance Regeln benoetigt? |
| `tax.precheck` | Steuer Vorpruefung | `offen` | Steuerfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Steuer Vorpruefung benoetigt? |
| `software.scope` | Software Umfang | `offen` | Gruenderkreis | Welche Angaben, Nachweise und Pruefpunkte werden fuer Software Umfang benoetigt? |

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
