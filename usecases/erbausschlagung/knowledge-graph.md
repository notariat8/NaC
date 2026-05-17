# Erbausschlagung Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `next10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.erbausschlagung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `decedent.identity` | Erblasser Identitaet | `offen` | Antragsteller | Welche Angaben, Nachweise und Pruefpunkte werden fuer Erblasser Identitaet benoetigt? |
| `renouncer.identity` | Ausschlagende Person Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Ausschlagende Person Identitaet benoetigt? |
| `deadline.status` | Frist Status | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Frist Status benoetigt? |
| `heirship.basis` | Erbenstellung Grundlage | `offen` | Antragsteller | Welche Angaben, Nachweise und Pruefpunkte werden fuer Erbenstellung Grundlage benoetigt? |
| `representation.minors` | Representation Minderjaehrige | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Representation Minderjaehrige benoetigt? |
| `delivery.route` | Zustellung Route | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Zustellung Route benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.renunciation_declaration` | Dokument: Ausschlagung Erklaerung | `offen` | notarielles Erklaerungspaket |
| `doc.death_or_court_reference` | Dokument: Sterbefall oder Gericht Referenz | `offen` | freigegebener Nachweisspeicher |
| `doc.approval_evidence` | Dokument: Genehmigung Nachweis | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.deadline_risk` | Entscheidung: Frist Risiko | `offen` |
| `decision.approval_needed` | Entscheidung: Genehmigung erforderlich | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.deadline_review` | Pruefgate: Frist Pruefung | `offen` |
| `gate.court_delivery` | Pruefgate: Gericht Zustellung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.deadline_review` | Nachweis: Frist Pruefung | `offen` |
| `evidence.delivery_trace` | Nachweis: Zustellung Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
