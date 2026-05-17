# Bautraegervertrag Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `next10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.bautraegervertrag`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `developer.identity` | Bautraeger Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Bautraeger Identitaet benoetigt? |
| `buyer.identity` | Kaeufer Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Kaeufer Identitaet benoetigt? |
| `object.identity` | Objekt Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Objekt Identitaet benoetigt? |
| `construction.specification` | Bauleistung Spezifikation | `offen` | Bautraeger | Welche Angaben, Nachweise und Pruefpunkte werden fuer Bauleistung Spezifikation benoetigt? |
| `installment.plan` | Ratenplan Plan | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Ratenplan Plan benoetigt? |
| `defects.acceptance` | Maengel acceptance | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Maengel acceptance benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.developer_contract_draft` | Dokument: Bautraeger Vertrag Entwurf | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.specification_package` | Dokument: Spezifikation Paket | `offen` | freigegebener Nachweisspeicher |
| `doc.land_register_state` | Dokument: Grundbuch Register Stand | `offen` | noc-grundbuch-portal oder manuell gepruefter Upload |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.payment_model` | Entscheidung: Zahlung Modell | `offen` |
| `decision.object_state` | Entscheidung: Objekt Stand | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.consumer_draft_period` | Pruefgate: Verbraucher-Entwurfsfrist | `offen` |
| `gate.installment_review` | Pruefgate: Ratenplan Pruefung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.consumer_release` | Nachweis: Verbraucher Freigabe | `offen` |
| `evidence.construction_package` | Nachweis: Bauleistung Paket | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
