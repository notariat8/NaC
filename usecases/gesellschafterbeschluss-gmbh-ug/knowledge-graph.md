# Gesellschafterbeschluss bei GmbH/UG Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `next10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.gesellschafterbeschluss_gmbh_ug`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `company.identity` | Gesellschaft Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gesellschaft Identitaet benoetigt? |
| `resolution.type` | Beschluss Art | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Beschluss Art benoetigt? |
| `shareholders.present` | Gesellschafter anwesend | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gesellschafter anwesend benoetigt? |
| `majority.requirement` | Mehrheit Anforderung | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Mehrheit Anforderung benoetigt? |
| `articles.wording` | Satzung Wortlaut | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Satzung Wortlaut benoetigt? |
| `register.filing` | Register Einreichung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Register Einreichung benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.resolution_minutes` | Dokument: Beschluss Protokoll | `offen` | notarielle Urkunde oder beglaubigtes Protokoll |
| `doc.current_articles` | Dokument: Aktueller Stand Satzung | `offen` | Nachweispaket der Gesellschaft |
| `doc.register_application` | Dokument: Register Antrag | `offen` | noc-bnotk-xnp und noc-handelsregister |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.notarial_form` | Entscheidung: Notariell Form | `offen` |
| `decision.register_relevance` | Entscheidung: Register Relevanz | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.quorum_majority_review` | Pruefgate: Beschlussfaehigkeit Mehrheit Pruefung | `offen` |
| `gate.register_package_ready` | Pruefgate: Register Paket bereit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.resolution_review` | Nachweis: Beschluss Pruefung | `offen` |
| `evidence.register_trace` | Nachweis: Register Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
