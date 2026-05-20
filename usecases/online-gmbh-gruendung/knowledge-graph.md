# GmbH-Gründung / UG-Gründung Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `top10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.online_gmbh_gruendung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `company.name` | Gesellschaft Name | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Gesellschaft Name benötigt? |
| `company.seat` | Gesellschaft Sitz | `offen` | Gründerkreis | Welche Angaben, Nachweise und Prüfpunkte werden für Gesellschaft Sitz benötigt? |
| `company.object` | Gesellschaft Objekt | `offen` | Gründerkreis | Welche Angaben, Nachweise und Prüfpunkte werden für Gesellschaft Objekt benötigt? |
| `founders.identity` | Gründer Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Gründer Identität benötigt? |
| `capital.structure` | Kapital Struktur | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Kapital Struktur benötigt? |
| `management.appointment` | Bestellung und Vertretung der Geschäftsführung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Bestellung und Vertretung der Geschäftsführung benötigt? |
| `register.route` | Register Route | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Register Route benötigt? |
| `beneficial.owner.flags` | Wirtschaftlich Berechtigte und GwG-Prüfflaggen | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Wirtschaftlich Berechtigte und GwG-Prüfflaggen benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.articles` | Dokument: Satzung | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.shareholder_list` | Dokument: Gesellschafterliste | `offen` | per Workflow erzeugt und geprüft |
| `doc.register_application` | Dokument: Register Antrag | `offen` | Route über nac-bnotk-xnp und nac-handelsregister |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.model_protocol` | Entscheidung: Musterprotokoll oder individuelle Satzung | `offen` |
| `decision.online_route` | Entscheidung: Online-Beurkundungsroute | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.card_xnp_readiness` | Prüfgate: Karten-, XNP- und Signaturbereitschaft | `offen` |
| `gate.register_filing_ready` | Prüfgate: Register Einreichung bereit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.technical_readiness` | Nachweis: Technische Bereitschaftsnachweise | `offen` |
| `evidence.register_submission` | Nachweis: Registereinreichungsnachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
