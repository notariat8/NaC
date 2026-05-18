# Loeschungsbewilligung / Grundbuchloeschung Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `next10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.loeschungsbewilligung_grundbuchloeschung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `property.identity` | Grundstueck Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Grundstueck Identitaet benoetigt? |
| `right.identity` | Recht Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Recht Identitaet benoetigt? |
| `creditor.authorization` | Glaeubiger Berechtigung | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Glaeubiger Berechtigung benoetigt? |
| `owner.consent` | Eigentuemer Zustimmung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Eigentuemer Zustimmung benoetigt? |
| `brief.status` | Brief Status | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Brief Status benoetigt? |
| `filing.route` | Einreichung Route | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Einreichung Route benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.deletion_consent` | Dokument: Loeschung Zustimmung | `offen` | Dokument von Glaeubiger, Berechtigtem oder Eigentuemer |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | nac-grundbuch-portal oder manuell gepruefter Upload |
| `doc.right_letter` | Dokument: Recht Brief | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.deletion_type` | Entscheidung: Loeschung Art | `offen` |
| `decision.brief_handling` | Entscheidung: Brief Behandlung | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.authority_review` | Pruefgate: Berechtigung Pruefung | `offen` |
| `gate.filing_ready` | Pruefgate: Einreichung bereit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.authorization_trace` | Nachweis: Berechtigung Nachverfolgung | `offen` |
| `evidence.deletion_completion` | Nachweis: Loeschung Abschluss | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
