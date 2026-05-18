# Grundstueckskaufvertrag Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `legacy-alias`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.grundstueckskaufvertrag`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `property.identity` | Grundstueck Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Grundstueck Identitaet benoetigt? |
| `seller.identity` | Verkaeufer Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Verkaeufer Identitaet benoetigt? |
| `buyer.identity` | Kaeufer Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Kaeufer Identitaet benoetigt? |
| `purchase.price` | Kaufpreis und Faelligkeitsmodell | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Kaufpreis und Faelligkeitsmodell benoetigt? |
| `encumbrances.current` | Belastungen aktueller Stand | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Belastungen aktueller Stand benoetigt? |
| `financing.required` | Finanzierung erforderlich | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Finanzierung erforderlich benoetigt? |
| `possession.transfer` | Besitz Uebertragung | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Besitz Uebertragung benoetigt? |
| `public.approvals` | Oeffentlich Genehmigungen | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Oeffentlich Genehmigungen benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | nac-grundbuch-portal oder manuell gepruefter Upload |
| `doc.contract_draft` | Dokument: Vertragsentwurf | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.approvals` | Dokument: Genehmigungen | `offen` | Metadaten der Behoerdenkorrespondenz |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.financing_route` | Entscheidung: Finanzierung Route | `offen` |
| `decision.encumbrance_handling` | Entscheidung: Belastung Behandlung | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.land_register_review` | Pruefgate: Grundbuchpruefung | `offen` |
| `gate.consumer_draft_period` | Pruefgate: Verbraucher-Entwurfsfrist | `offen` |
| `gate.execution_readiness` | Pruefgate: Vollzugsbereitschaft | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.intake_review` | Nachweis: Aufnahmepruefung und Entwurfsfreigabe | `offen` |
| `evidence.filing_trace` | Nachweis: Einreichungs- und Vollzugsnachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
