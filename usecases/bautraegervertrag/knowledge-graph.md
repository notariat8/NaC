# Bauträgervertrag Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `next10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.bautraegervertrag`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `developer.identity` | Bauträger Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Bauträger Identität benötigt? |
| `buyer.identity` | Käufer Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Käufer Identität benötigt? |
| `object.identity` | Objekt Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Objekt Identität benötigt? |
| `construction.specification` | Bauleistung Spezifikation | `offen` | Bauträger | Welche Angaben, Nachweise und Prüfpunkte werden für Bauleistung Spezifikation benötigt? |
| `installment.plan` | Ratenplan Plan | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Ratenplan Plan benötigt? |
| `defects.acceptance` | Mängel acceptance | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Mängel acceptance benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.developer_contract_draft` | Dokument: Bauträger Vertrag Entwurf | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.specification_package` | Dokument: Spezifikation Paket | `offen` | freigegebener Nachweisspeicher |
| `doc.land_register_state` | Dokument: Grundbuch Register Stand | `offen` | nac-grundbuch-portal oder manuell geprüfter Upload |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.payment_model` | Entscheidung: Zahlung Modell | `offen` |
| `decision.object_state` | Entscheidung: Objekt Stand | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.consumer_draft_period` | Prüfgate: Verbraucher-Entwurfsfrist | `offen` |
| `gate.installment_review` | Prüfgate: Ratenplan Prüfung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.consumer_release` | Nachweis: Verbraucher Freigabe | `offen` |
| `evidence.construction_package` | Nachweis: Bauleistung Paket | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
