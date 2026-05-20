# Erbausschlagung Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `next10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.erbausschlagung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `decedent.identity` | Erblasser Identität | `offen` | Antragsteller | Welche Angaben, Nachweise und Prüfpunkte werden für Erblasser Identität benötigt? |
| `renouncer.identity` | Ausschlagende Person Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Ausschlagende Person Identität benötigt? |
| `deadline.status` | Frist Status | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Frist Status benötigt? |
| `heirship.basis` | Erbenstellung Grundlage | `offen` | Antragsteller | Welche Angaben, Nachweise und Prüfpunkte werden für Erbenstellung Grundlage benötigt? |
| `representation.minors` | Representation Minderjährige | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Representation Minderjährige benötigt? |
| `delivery.route` | Zustellung Route | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Zustellung Route benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.renunciation_declaration` | Dokument: Ausschlagung Erklärung | `offen` | notarielles Erklärungspaket |
| `doc.death_or_court_reference` | Dokument: Sterbefall oder Gericht Referenz | `offen` | freigegebener Nachweisspeicher |
| `doc.approval_evidence` | Dokument: Genehmigung Nachweis | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.deadline_risk` | Entscheidung: Frist Risiko | `offen` |
| `decision.approval_needed` | Entscheidung: Genehmigung erforderlich | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.deadline_review` | Prüfgate: Frist Prüfung | `offen` |
| `gate.court_delivery` | Prüfgate: Gericht Zustellung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.deadline_review` | Nachweis: Frist Prüfung | `offen` |
| `evidence.delivery_trace` | Nachweis: Zustellung Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
