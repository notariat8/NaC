# Vorsorgevollmacht und Patientenverfuegung Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `top10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.vorsorgevollmacht_patientenverfuegung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `principal.identity` | Vollmachtgeber Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Vollmachtgeber Identitaet benoetigt? |
| `agent.identities` | Bevollmaechtigter Identitaeten | `offen` | Vollmachtgeber | Welche Angaben, Nachweise und Pruefpunkte werden fuer Bevollmaechtigter Identitaeten benoetigt? |
| `authority.financial` | Berechtigung Finanzen | `offen` | Vollmachtgeber | Welche Angaben, Nachweise und Pruefpunkte werden fuer Berechtigung Finanzen benoetigt? |
| `authority.health` | Berechtigung Gesundheit | `offen` | Vollmachtgeber | Welche Angaben, Nachweise und Pruefpunkte werden fuer Berechtigung Gesundheit benoetigt? |
| `patient.directive` | Patientenverfuegung Verfuegung | `offen` | Vollmachtgeber | Welche Angaben, Nachweise und Pruefpunkte werden fuer Patientenverfuegung Verfuegung benoetigt? |
| `effectiveness.rules` | Wirksamkeit Regeln | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Wirksamkeit Regeln benoetigt? |
| `self_dealing.release` | Befreiung von Selbstkontrahierung und Untervollmacht | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Befreiung von Selbstkontrahierung und Untervollmacht benoetigt? |
| `central_register` | Zentrales Vorsorgeregister | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Zentrales Vorsorgeregister benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.power_of_attorney_draft` | Dokument: Vollmacht von Vollmacht Entwurf | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.patient_directive_draft` | Dokument: Patientenverfuegung Verfuegung Entwurf | `offen` | nach Pruefung erzeugter Workflow-Entwurf |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.instrument_scope` | Entscheidung: Instrument Umfang | `offen` |
| `decision.register` | Entscheidung: Register | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.capacity_review` | Pruefgate: Geschaeftsfaehigkeit Pruefung | `offen` |
| `gate.health_scope_review` | Pruefgate: Gesundheit Umfang Pruefung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.capacity_and_instruction` | Nachweis: Geschaeftsfaehigkeit and Anweisung | `offen` |
| `evidence.copy_register_trace` | Nachweis: Ausfertigung Register Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
