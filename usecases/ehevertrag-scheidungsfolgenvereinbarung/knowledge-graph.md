# Ehevertrag / Scheidungsfolgenvereinbarung Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `top10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.ehevertrag_scheidungsfolgen`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `spouses.identity` | Ehegatten Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Ehegatten Identität benötigt? |
| `marriage.context` | Ehe Kontext | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Ehe Kontext benötigt? |
| `property.regime` | Grundstück Regime | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Grundstück Regime benötigt? |
| `asset.disclosure` | Vermögen Offenlegung | `offen` | Ehegatten | Welche Angaben, Nachweise und Prüfpunkte werden für Vermögen Offenlegung benötigt? |
| `maintenance.rules` | Unterhalt Regeln | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Unterhalt Regeln benötigt? |
| `pension.equalization` | Versorgungsausgleich equalization | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Versorgungsausgleich equalization benötigt? |
| `child.family.flags` | Kind Familie Prüfflaggen | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Kind Familie Prüfflaggen benötigt? |
| `asset.transfer` | Vermögen Übertragung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Vermögen Übertragung benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.agreement_draft` | Dokument: Vereinbarung Entwurf | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.asset_schedule_reference` | Dokument: Vermögen Plan Referenz | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.instrument_type` | Entscheidung: Instrument Art | `offen` |
| `decision.fairness_risk` | Entscheidung: Fairness Risiko | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.fairness_review` | Prüfgate: Fairness Prüfung | `offen` |
| `gate.simultaneous_presence` | Prüfgate: Gleichzeitig Anwesenheit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.fairness_notes` | Nachweis: Fairness Vermerke | `offen` |
| `evidence.execution_and_followup` | Nachweis: Vollzug and Nachbereitung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
