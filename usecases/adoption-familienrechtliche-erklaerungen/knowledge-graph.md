# Adoption / familienrechtliche Erklaerungen Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `next10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.adoption_familienrechtliche_erklaerungen`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `case.type` | Fall Art | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Fall Art benoetigt? |
| `child.identity_context` | Kind Identitaet Kontext | `offen` | Mandantschaft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Kind Identitaet Kontext benoetigt? |
| `consenting_party.identity` | Zustimmende Beteiligter Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Zustimmende Beteiligter Identitaet benoetigt? |
| `court.destination` | Gericht Zielgericht | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gericht Zielgericht benoetigt? |
| `irrevocability.warning` | Unwiderruflichkeit Belehrung | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Unwiderruflichkeit Belehrung benoetigt? |
| `additional.approvals` | Weitere Genehmigungen | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Weitere Genehmigungen benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.consent_declaration` | Dokument: Zustimmung Erklaerung | `offen` | notarielles Erklaerungspaket |
| `doc.court_reference` | Dokument: Gericht Referenz | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.declaration_route` | Entscheidung: Erklaerung Route | `offen` |
| `decision.approval_status` | Entscheidung: Genehmigung Status | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.capacity_and_warning` | Pruefgate: Geschaeftsfaehigkeit and Belehrung | `offen` |
| `gate.court_delivery` | Pruefgate: Gericht Zustellung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.warning_notes` | Nachweis: Belehrung Vermerke | `offen` |
| `evidence.family_court_delivery` | Nachweis: Familie Gericht Zustellung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
