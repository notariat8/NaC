# Grundschuld / Hypothekenbestellung Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `top10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.grundschuld_hypothek`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `property.identity` | Grundstueck Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Grundstueck Identitaet benoetigt? |
| `owner.identity` | Eigentuemer Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Eigentuemer Identitaet benoetigt? |
| `debtor.identity` | Schuldner Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Schuldner Identitaet benoetigt? |
| `lender.identity` | Darlehensgeber Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Darlehensgeber Identitaet benoetigt? |
| `charge.amount` | Grundschuld amount | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Grundschuld amount benoetigt? |
| `security.purpose` | Sicherung Zweck | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Sicherung Zweck benoetigt? |
| `ranking.requirement` | Rang Anforderung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Rang Anforderung benoetigt? |
| `enforcement.clause` | Vollstreckung Klausel | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Vollstreckung Klausel benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.bank_instruction` | Dokument: Bank Anweisung | `offen` | von der Bank bereitgestelltes Weisungspaket |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | noc-grundbuch-portal oder manuell gepruefter Upload |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.charge_type` | Entscheidung: Grundschuld Art | `offen` |
| `decision.execution_clause_scope` | Entscheidung: Vollzug Klausel Umfang | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.bank_instruction_review` | Pruefgate: Bank Anweisung Pruefung | `offen` |
| `gate.rank_review` | Pruefgate: Rang Pruefung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.bank_instruction_hash` | Nachweis: Bank Anweisung Hash | `offen` |
| `evidence.land_register_application` | Nachweis: Grundbuch Register Antrag | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
