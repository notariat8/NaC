# Geschaeftsanteilsuebertragung GmbH Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `next10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.geschaeftsanteilsuebertragung_gmbh`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `company.identity` | Gesellschaft Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gesellschaft Identitaet benoetigt? |
| `share.identity` | Geschaeftsanteil Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Geschaeftsanteil Identitaet benoetigt? |
| `seller.identity` | Verkaeufer Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Verkaeufer Identitaet benoetigt? |
| `buyer.identity` | Kaeufer Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Kaeufer Identitaet benoetigt? |
| `consents.restrictions` | Zustimmungen Beschraenkungen | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Zustimmungen Beschraenkungen benoetigt? |
| `consideration.tax` | Gegenleistung Steuer | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gegenleistung Steuer benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.transfer_agreement` | Dokument: Uebertragung Vereinbarung | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.shareholder_list` | Dokument: Gesellschafterliste | `offen` | per Workflow erzeugt und geprueft |
| `doc.consent_evidence` | Dokument: Zustimmung Nachweis | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.transfer_type` | Entscheidung: Uebertragung Art | `offen` |
| `decision.consent_needed` | Entscheidung: Zustimmung erforderlich | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.chain_of_title_review` | Pruefgate: Kette von Titel Pruefung | `offen` |
| `gate.shareholder_list_ready` | Pruefgate: Gesellschafter Liste bereit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.transfer_review` | Nachweis: Uebertragung Pruefung | `offen` |
| `evidence.shareholder_list_submission` | Nachweis: Gesellschafter Liste Einreichung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
