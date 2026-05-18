# GmbH-Gruendung / UG-Gruendung Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `top10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.online_gmbh_gruendung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `company.name` | Gesellschaft Name | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gesellschaft Name benoetigt? |
| `company.seat` | Gesellschaft Sitz | `offen` | Gruenderkreis | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gesellschaft Sitz benoetigt? |
| `company.object` | Gesellschaft Objekt | `offen` | Gruenderkreis | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gesellschaft Objekt benoetigt? |
| `founders.identity` | Gruender Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gruender Identitaet benoetigt? |
| `capital.structure` | Kapital Struktur | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Kapital Struktur benoetigt? |
| `management.appointment` | Bestellung und Vertretung der Geschaeftsfuehrung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Bestellung und Vertretung der Geschaeftsfuehrung benoetigt? |
| `register.route` | Register Route | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Register Route benoetigt? |
| `beneficial.owner.flags` | Wirtschaftlich Berechtigte und GwG-Pruefflaggen | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Wirtschaftlich Berechtigte und GwG-Pruefflaggen benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.articles` | Dokument: Satzung | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.shareholder_list` | Dokument: Gesellschafterliste | `offen` | per Workflow erzeugt und geprueft |
| `doc.register_application` | Dokument: Register Antrag | `offen` | Route ueber nac-bnotk-xnp und nac-handelsregister |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.model_protocol` | Entscheidung: Musterprotokoll oder individuelle Satzung | `offen` |
| `decision.online_route` | Entscheidung: Online-Beurkundungsroute | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.card_xnp_readiness` | Pruefgate: Karten-, XNP- und Signaturbereitschaft | `offen` |
| `gate.register_filing_ready` | Pruefgate: Register Einreichung bereit | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.technical_readiness` | Nachweis: Technische Bereitschaftsnachweise | `offen` |
| `evidence.register_submission` | Nachweis: Registereinreichungsnachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
