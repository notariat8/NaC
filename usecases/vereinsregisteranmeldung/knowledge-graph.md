# Vereinsregisteranmeldung Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `next10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.vereinsregisteranmeldung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `association.identity` | Verein Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Verein Identitaet benoetigt? |
| `filing.type` | Einreichung Art | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Einreichung Art benoetigt? |
| `board.identity` | Vorstand Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Vorstand Identitaet benoetigt? |
| `resolution.evidence` | Beschluss Nachweis | `offen` | Verein | Welche Angaben, Nachweise und Pruefpunkte werden fuer Beschluss Nachweis benoetigt? |
| `articles.current` | Satzung aktueller Stand | `offen` | Verein | Welche Angaben, Nachweise und Pruefpunkte werden fuer Satzung aktueller Stand benoetigt? |
| `filing.route` | Einreichung Route | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Einreichung Route benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.register_application` | Dokument: Register Antrag | `offen` | notarielles Beglaubigungspaket |
| `doc.minutes_resolution` | Dokument: Protokoll Beschluss | `offen` | Nachweispaket des Vereins |
| `doc.articles` | Dokument: Satzung | `offen` | Nachweispaket des Vereins |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.certification_route` | Entscheidung: Beglaubigung Route | `offen` |
| `decision.attachment_complete` | Entscheidung: Anlage Vollstaendigkeit | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.signer_authority` | Pruefgate: Unterzeichner Berechtigung | `offen` |
| `gate.register_package_ready` | Pruefgate: Register Paket bereit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.certification_trace` | Nachweis: Beglaubigung Nachverfolgung | `offen` |
| `evidence.court_submission` | Nachweis: Gericht Einreichung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
