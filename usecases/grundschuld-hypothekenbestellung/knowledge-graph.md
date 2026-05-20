# Grundschuld / Hypothekenbestellung Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `top10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.grundschuld_hypothek`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `property.identity` | Grundstück Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Grundstück Identität benötigt? |
| `owner.identity` | Eigentümer Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Eigentümer Identität benötigt? |
| `debtor.identity` | Schuldner Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Schuldner Identität benötigt? |
| `lender.identity` | Darlehensgeber Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Darlehensgeber Identität benötigt? |
| `charge.amount` | Grundschuld amount | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Grundschuld amount benötigt? |
| `security.purpose` | Sicherung Zweck | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Sicherung Zweck benötigt? |
| `ranking.requirement` | Rang Anforderung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Rang Anforderung benötigt? |
| `enforcement.clause` | Vollstreckung Klausel | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Vollstreckung Klausel benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.bank_instruction` | Dokument: Bank Anweisung | `offen` | von der Bank bereitgestelltes Weisungspaket |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | nac-grundbuch-portal oder manuell geprüfter Upload |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.charge_type` | Entscheidung: Grundschuld Art | `offen` |
| `decision.execution_clause_scope` | Entscheidung: Vollzug Klausel Umfang | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.bank_instruction_review` | Prüfgate: Bank Anweisung Prüfung | `offen` |
| `gate.rank_review` | Prüfgate: Rang Prüfung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.bank_instruction_hash` | Nachweis: Bank Anweisung Hash | `offen` |
| `evidence.land_register_application` | Nachweis: Grundbuch Register Antrag | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
