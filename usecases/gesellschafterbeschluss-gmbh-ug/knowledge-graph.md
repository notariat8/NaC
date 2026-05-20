# Gesellschafterbeschluss bei GmbH/UG Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `next10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.gesellschafterbeschluss_gmbh_ug`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `company.identity` | Gesellschaft Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Gesellschaft Identität benötigt? |
| `resolution.type` | Beschluss Art | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Beschluss Art benötigt? |
| `shareholders.present` | Gesellschafter anwesend | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Gesellschafter anwesend benötigt? |
| `majority.requirement` | Mehrheit Anforderung | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Mehrheit Anforderung benötigt? |
| `articles.wording` | Satzung Wortlaut | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Satzung Wortlaut benötigt? |
| `register.filing` | Register Einreichung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Register Einreichung benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.resolution_minutes` | Dokument: Beschluss Protokoll | `offen` | notarielle Urkunde oder beglaubigtes Protokoll |
| `doc.current_articles` | Dokument: Aktueller Stand Satzung | `offen` | Nachweispaket der Gesellschaft |
| `doc.register_application` | Dokument: Register Antrag | `offen` | nac-bnotk-xnp und nac-handelsregister |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.notarial_form` | Entscheidung: Notariell Form | `offen` |
| `decision.register_relevance` | Entscheidung: Register Relevanz | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.quorum_majority_review` | Prüfgate: Beschlussfähigkeit Mehrheit Prüfung | `offen` |
| `gate.register_package_ready` | Prüfgate: Register Paket bereit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.resolution_review` | Nachweis: Beschluss Prüfung | `offen` |
| `evidence.register_trace` | Nachweis: Register Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
