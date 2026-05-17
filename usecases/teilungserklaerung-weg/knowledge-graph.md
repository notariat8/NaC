# Teilungserklaerung nach WEG Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `next10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.teilungserklaerung_weg`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `property.identity` | Grundstueck Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Grundstueck Identitaet benoetigt? |
| `owner.identity` | Eigentuemer Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Eigentuemer Identitaet benoetigt? |
| `unit.structure` | Einheit Struktur | `offen` | Mandantschaft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Einheit Struktur benoetigt? |
| `ownership.shares` | Eigentum Anteile | `offen` | Mandantschaft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Eigentum Anteile benoetigt? |
| `plans.certificates` | Plaene Bescheinigungen | `offen` | Mandantschaft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Plaene Bescheinigungen benoetigt? |
| `encumbrance.handling` | Belastung Behandlung | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Belastung Behandlung benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.division_declaration` | Dokument: Teilung Erklaerung | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.plans_certificate` | Dokument: Plaene Bescheinigung | `offen` | freigegebener Nachweisspeicher |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | noc-grundbuch-portal oder manuell gepruefter Upload |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.use_case` | Entscheidung: Nutzung Fall | `offen` |
| `decision.special_use_rights` | Entscheidung: Sonderfall Nutzung Rechte | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.plan_certificate_review` | Pruefgate: Plan Bescheinigung Pruefung | `offen` |
| `gate.land_register_implementation` | Pruefgate: Grundbuch Register Umsetzung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.plan_package` | Nachweis: Plan Paket | `offen` |
| `evidence.unit_register_trace` | Nachweis: Einheit Register Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
