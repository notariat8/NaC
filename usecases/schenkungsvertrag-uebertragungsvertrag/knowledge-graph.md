# Schenkungsvertrag / Uebertragungsvertrag Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `top10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.schenkungsvertrag_uebertragung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `transferor.identity` | Uebertragender Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Uebertragender Identitaet benoetigt? |
| `transferee.identity` | Erwerber Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Erwerber Identitaet benoetigt? |
| `asset.identity` | Vermoegen Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Vermoegen Identitaet benoetigt? |
| `reserved.rights` | Vorbehaltsrechte Rechte | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Vorbehaltsrechte Rechte benoetigt? |
| `reversion.rights` | Rueckforderungsrechte Rechte | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Rueckforderungsrechte Rechte benoetigt? |
| `consideration.obligations` | Gegenleistung Pflichten | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gegenleistung Pflichten benoetigt? |
| `consents.approvals` | Zustimmungen Genehmigungen | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Zustimmungen Genehmigungen benoetigt? |
| `tax.family.flags` | Steuer Familie Pruefflaggen | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Steuer Familie Pruefflaggen benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.transfer_draft` | Dokument: Uebertragung Entwurf | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | noc-grundbuch-portal oder manuell gepruefter Upload |
| `doc.approvals` | Dokument: Genehmigungen | `offen` | manuell gepruefter Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.transfer_type` | Entscheidung: Uebertragung Art | `offen` |
| `decision.reserved_rights` | Entscheidung: Vorbehaltsrechte Rechte | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.asset_review` | Pruefgate: Vermoegen Pruefung | `offen` |
| `gate.family_tax_review` | Pruefgate: Familie Steuer Pruefung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.review_trace` | Nachweis: Pruefung Nachverfolgung | `offen` |
| `evidence.execution_trace` | Nachweis: Vollzug Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
