# Adoption / familienrechtliche Erklärungen Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `next10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.adoption_familienrechtliche_erklaerungen`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `case.type` | Fall Art | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Fall Art benötigt? |
| `child.identity_context` | Kind Identität Kontext | `offen` | Mandantschaft | Welche Angaben, Nachweise und Prüfpunkte werden für Kind Identität Kontext benötigt? |
| `consenting_party.identity` | Zustimmende Beteiligter Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Zustimmende Beteiligter Identität benötigt? |
| `court.destination` | Gericht Zielgericht | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Gericht Zielgericht benötigt? |
| `irrevocability.warning` | Unwiderruflichkeit Belehrung | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Unwiderruflichkeit Belehrung benötigt? |
| `additional.approvals` | Weitere Genehmigungen | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Weitere Genehmigungen benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.consent_declaration` | Dokument: Zustimmung Erklärung | `offen` | notarielles Erklärungspaket |
| `doc.court_reference` | Dokument: Gericht Referenz | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.declaration_route` | Entscheidung: Erklärung Route | `offen` |
| `decision.approval_status` | Entscheidung: Genehmigung Status | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.capacity_and_warning` | Prüfgate: Geschäftsfähigkeit and Belehrung | `offen` |
| `gate.court_delivery` | Prüfgate: Gericht Zustellung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.warning_notes` | Nachweis: Belehrung Vermerke | `offen` |
| `evidence.family_court_delivery` | Nachweis: Familie Gericht Zustellung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
