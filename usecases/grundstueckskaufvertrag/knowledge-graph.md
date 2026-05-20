# Grundstückskaufvertrag Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `legacy-alias`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.grundstueckskaufvertrag`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `property.identity` | Grundstück Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Grundstück Identität benötigt? |
| `seller.identity` | Verkäufer Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Verkäufer Identität benötigt? |
| `buyer.identity` | Käufer Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Käufer Identität benötigt? |
| `purchase.price` | Kaufpreis und Faelligkeitsmodell | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Kaufpreis und Faelligkeitsmodell benötigt? |
| `encumbrances.current` | Belastungen aktueller Stand | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Belastungen aktueller Stand benötigt? |
| `financing.required` | Finanzierung erforderlich | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Finanzierung erforderlich benötigt? |
| `possession.transfer` | Besitz Übertragung | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Besitz Übertragung benötigt? |
| `public.approvals` | Öffentlich Genehmigungen | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Öffentlich Genehmigungen benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | nac-grundbuch-portal oder manuell geprüfter Upload |
| `doc.contract_draft` | Dokument: Vertragsentwurf | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.approvals` | Dokument: Genehmigungen | `offen` | Metadaten der Behördenkorrespondenz |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.financing_route` | Entscheidung: Finanzierung Route | `offen` |
| `decision.encumbrance_handling` | Entscheidung: Belastung Behandlung | `offen` |

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
