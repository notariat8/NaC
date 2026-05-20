# Geschäftsanteilsübertragung GmbH Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `next10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.geschaeftsanteilsuebertragung_gmbh`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `company.identity` | Gesellschaft Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Gesellschaft Identität benötigt? |
| `share.identity` | Geschäftsanteil Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Geschäftsanteil Identität benötigt? |
| `seller.identity` | Verkäufer Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Verkäufer Identität benötigt? |
| `buyer.identity` | Käufer Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Käufer Identität benötigt? |
| `consents.restrictions` | Zustimmungen Beschraenkungen | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Zustimmungen Beschraenkungen benötigt? |
| `consideration.tax` | Gegenleistung Steuer | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Gegenleistung Steuer benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.transfer_agreement` | Dokument: Übertragung Vereinbarung | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.shareholder_list` | Dokument: Gesellschafterliste | `offen` | per Workflow erzeugt und geprüft |
| `doc.consent_evidence` | Dokument: Zustimmung Nachweis | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.transfer_type` | Entscheidung: Übertragung Art | `offen` |
| `decision.consent_needed` | Entscheidung: Zustimmung erforderlich | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.chain_of_title_review` | Prüfgate: Kette von Titel Prüfung | `offen` |
| `gate.shareholder_list_ready` | Prüfgate: Gesellschafter Liste bereit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.transfer_review` | Nachweis: Übertragung Prüfung | `offen` |
| `evidence.shareholder_list_submission` | Nachweis: Gesellschafter Liste Einreichung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
