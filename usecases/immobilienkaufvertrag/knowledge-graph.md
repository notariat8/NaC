# Immobilienkaufvertrag Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `top10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.immobilienkaufvertrag`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `property.identity` | Grundstücksidentität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für die Grundstücksidentität benötigt? |
| `seller.identity` | Identität Verkäufer | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für die Identität des Verkäufers benötigt? |
| `buyer.identity` | Identität Käufer | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für die Identität des Käufers benötigt? |
| `purchase.price` | Kaufpreis und Fälligkeitsmodell | `offen` | Notarin/Notar | Welche Angaben, Nachweise und Prüfpunkte werden für Kaufpreis und Fälligkeitsmodell benötigt? |
| `encumbrances.current` | Aktueller Belastungsstand | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für den aktuellen Belastungsstand benötigt? |
| `financing.required` | Finanzierung erforderlich | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für die erforderliche Finanzierung benötigt? |
| `possession.transfer` | Besitzübergang | `offen` | Notarin/Notar | Welche Angaben, Nachweise und Prüfpunkte werden für den Besitzübergang benötigt? |
| `public.approvals` | Öffentlich-rechtliche Genehmigungen | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für öffentlich-rechtliche Genehmigungen benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | nac-grundbuch-portal oder manuell geprüfter Upload |
| `doc.contract_draft` | Dokument: Vertragsentwurf | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.approvals` | Dokument: Genehmigungen | `offen` | Metadaten der Behördenkorrespondenz |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.financing_route` | Entscheidung: Finanzierungsweg | `offen` |
| `decision.encumbrance_handling` | Entscheidung: Umgang mit Belastungen | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.land_register_review` | Prüfgate: Grundbuchprüfung | `offen` |
| `gate.consumer_draft_period` | Prüfgate: Verbraucher-Entwurfsfrist | `offen` |
| `gate.execution_readiness` | Prüfgate: Vollzugsbereitschaft | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.intake_review` | Nachweis: Aufnahmeprüfung und Entwurfsfreigabe | `offen` |
| `evidence.filing_trace` | Nachweis: Einreichungs- und Vollzugsnachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
