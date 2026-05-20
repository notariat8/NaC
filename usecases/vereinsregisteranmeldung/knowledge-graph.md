# Vereinsregisteranmeldung Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `next10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.vereinsregisteranmeldung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `association.identity` | Verein Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Verein Identität benötigt? |
| `filing.type` | Einreichung Art | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Einreichung Art benötigt? |
| `board.identity` | Vorstand Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Vorstand Identität benötigt? |
| `resolution.evidence` | Beschluss Nachweis | `offen` | Verein | Welche Angaben, Nachweise und Prüfpunkte werden für Beschluss Nachweis benötigt? |
| `articles.current` | Satzung aktueller Stand | `offen` | Verein | Welche Angaben, Nachweise und Prüfpunkte werden für Satzung aktueller Stand benötigt? |
| `filing.route` | Einreichung Route | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Einreichung Route benötigt? |

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
| `decision.attachment_complete` | Entscheidung: Anlage Vollständigkeit | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.signer_authority` | Prüfgate: Unterzeichner Berechtigung | `offen` |
| `gate.register_package_ready` | Prüfgate: Register Paket bereit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.certification_trace` | Nachweis: Beglaubigung Nachverfolgung | `offen` |
| `evidence.court_submission` | Nachweis: Gericht Einreichung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
