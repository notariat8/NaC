# Löschungsbewilligung / Grundbuchlöschung Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `next10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.loeschungsbewilligung_grundbuchloeschung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `property.identity` | Grundstück Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Grundstück Identität benötigt? |
| `right.identity` | Recht Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Recht Identität benötigt? |
| `creditor.authorization` | Glaeubiger Berechtigung | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Glaeubiger Berechtigung benötigt? |
| `owner.consent` | Eigentümer Zustimmung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Eigentümer Zustimmung benötigt? |
| `brief.status` | Brief Status | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Brief Status benötigt? |
| `filing.route` | Einreichung Route | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Einreichung Route benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.deletion_consent` | Dokument: Löschung Zustimmung | `offen` | Dokument von Glaeubiger, Berechtigtem oder Eigentümer |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | nac-grundbuch-portal oder manuell geprüfter Upload |
| `doc.right_letter` | Dokument: Recht Brief | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.deletion_type` | Entscheidung: Löschung Art | `offen` |
| `decision.brief_handling` | Entscheidung: Brief Behandlung | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.authority_review` | Prüfgate: Berechtigung Prüfung | `offen` |
| `gate.filing_ready` | Prüfgate: Einreichung bereit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.authorization_trace` | Nachweis: Berechtigung Nachverfolgung | `offen` |
| `evidence.deletion_completion` | Nachweis: Löschung Abschluss | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
