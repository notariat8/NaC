# Pflichtteilsverzicht / Erbverzicht Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `next10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.pflichtteilsverzicht_erbverzicht`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `future_decedent.identity` | Kuenftiger Erblasser Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Kuenftiger Erblasser Identitaet benoetigt? |
| `waiver_party.identity` | Verzicht Beteiligter Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Verzicht Beteiligter Identitaet benoetigt? |
| `waiver.scope` | Verzicht Umfang | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Verzicht Umfang benoetigt? |
| `descendant.effect` | Abkoemmlinge Wirkung | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Abkoemmlinge Wirkung benoetigt? |
| `compensation.model` | Abfindung Modell | `offen` | Mandantschaft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Abfindung Modell benoetigt? |
| `family.fairness_flags` | Familie Fairness Pruefflaggen | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Familie Fairness Pruefflaggen benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.waiver_contract` | Dokument: Verzicht Vertrag | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.compensation_evidence` | Dokument: Abfindung Nachweis | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.waiver_type` | Entscheidung: Verzicht Art | `offen` |
| `decision.compensation` | Entscheidung: Abfindung | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.personal_presence_review` | Pruefgate: Persoenlich Anwesenheit Pruefung | `offen` |
| `gate.fairness_review` | Pruefgate: Fairness Pruefung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.fairness_notes` | Nachweis: Fairness Vermerke | `offen` |
| `evidence.execution_trace` | Nachweis: Vollzug Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
