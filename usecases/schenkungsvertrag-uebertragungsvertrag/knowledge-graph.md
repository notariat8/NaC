# Schenkungsvertrag / Übertragungsvertrag Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `top10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.schenkungsvertrag_uebertragung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `transferor.identity` | Übertragender Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Übertragender Identität benötigt? |
| `transferee.identity` | Erwerber Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Erwerber Identität benötigt? |
| `asset.identity` | Vermögen Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Vermögen Identität benötigt? |
| `reserved.rights` | Vorbehaltsrechte Rechte | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Vorbehaltsrechte Rechte benötigt? |
| `reversion.rights` | Rückforderungsrechte Rechte | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Rückforderungsrechte Rechte benötigt? |
| `consideration.obligations` | Gegenleistung Pflichten | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Gegenleistung Pflichten benötigt? |
| `consents.approvals` | Zustimmungen Genehmigungen | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Zustimmungen Genehmigungen benötigt? |
| `tax.family.flags` | Steuer Familie Prüfflaggen | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Steuer Familie Prüfflaggen benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.transfer_draft` | Dokument: Übertragung Entwurf | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | nac-grundbuch-portal oder manuell geprüfter Upload |
| `doc.approvals` | Dokument: Genehmigungen | `offen` | manuell geprüfter Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.transfer_type` | Entscheidung: Übertragung Art | `offen` |
| `decision.reserved_rights` | Entscheidung: Vorbehaltsrechte Rechte | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.asset_review` | Prüfgate: Vermögen Prüfung | `offen` |
| `gate.family_tax_review` | Prüfgate: Familie Steuer Prüfung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.review_trace` | Nachweis: Prüfung Nachverfolgung | `offen` |
| `evidence.execution_trace` | Nachweis: Vollzug Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
