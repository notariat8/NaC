# Ehevertrag / Scheidungsfolgenvereinbarung Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `top10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.ehevertrag_scheidungsfolgen`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `spouses.identity` | Ehegatten Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Ehegatten Identitaet benoetigt? |
| `marriage.context` | Ehe Kontext | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Ehe Kontext benoetigt? |
| `property.regime` | Grundstueck Regime | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Grundstueck Regime benoetigt? |
| `asset.disclosure` | Vermoegen Offenlegung | `offen` | Ehegatten | Welche Angaben, Nachweise und Pruefpunkte werden fuer Vermoegen Offenlegung benoetigt? |
| `maintenance.rules` | Unterhalt Regeln | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Unterhalt Regeln benoetigt? |
| `pension.equalization` | Versorgungsausgleich equalization | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Versorgungsausgleich equalization benoetigt? |
| `child.family.flags` | Kind Familie Pruefflaggen | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Kind Familie Pruefflaggen benoetigt? |
| `asset.transfer` | Vermoegen Uebertragung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Vermoegen Uebertragung benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.agreement_draft` | Dokument: Vereinbarung Entwurf | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.asset_schedule_reference` | Dokument: Vermoegen Plan Referenz | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.instrument_type` | Entscheidung: Instrument Art | `offen` |
| `decision.fairness_risk` | Entscheidung: Fairness Risiko | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.fairness_review` | Pruefgate: Fairness Pruefung | `offen` |
| `gate.simultaneous_presence` | Pruefgate: Gleichzeitig Anwesenheit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.fairness_notes` | Nachweis: Fairness Vermerke | `offen` |
| `evidence.execution_and_followup` | Nachweis: Vollzug and Nachbereitung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
