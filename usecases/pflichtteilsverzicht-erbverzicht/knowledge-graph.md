# Pflichtteilsverzicht / Erbverzicht Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `next10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.pflichtteilsverzicht_erbverzicht`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `future_decedent.identity` | Künftiger Erblasser Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Künftiger Erblasser Identität benötigt? |
| `waiver_party.identity` | Verzicht Beteiligter Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Verzicht Beteiligter Identität benötigt? |
| `waiver.scope` | Verzicht Umfang | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Verzicht Umfang benötigt? |
| `descendant.effect` | Abkoemmlinge Wirkung | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Abkoemmlinge Wirkung benötigt? |
| `compensation.model` | Abfindung Modell | `offen` | Mandantschaft | Welche Angaben, Nachweise und Prüfpunkte werden für Abfindung Modell benötigt? |
| `family.fairness_flags` | Familie Fairness Prüfflaggen | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Familie Fairness Prüfflaggen benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.waiver_contract` | Dokument: Verzicht Vertrag | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.compensation_evidence` | Dokument: Abfindung Nachweis | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.waiver_type` | Entscheidung: Verzicht Art | `offen` |
| `decision.compensation` | Entscheidung: Abfindung | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.personal_presence_review` | Prüfgate: Persoenlich Anwesenheit Prüfung | `offen` |
| `gate.fairness_review` | Prüfgate: Fairness Prüfung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.fairness_notes` | Nachweis: Fairness Vermerke | `offen` |
| `evidence.execution_trace` | Nachweis: Vollzug Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
