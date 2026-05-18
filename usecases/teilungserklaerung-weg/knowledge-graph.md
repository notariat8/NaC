# Teilungserklärung nach WEG Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `next10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.teilungserklaerung_weg`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `property.identity` | Grundstück Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Grundstück Identität benötigt? |
| `owner.identity` | Eigentümer Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Eigentümer Identität benötigt? |
| `unit.structure` | Einheit Struktur | `offen` | Mandantschaft | Welche Angaben, Nachweise und Prüfpunkte werden für Einheit Struktur benötigt? |
| `ownership.shares` | Eigentum Anteile | `offen` | Mandantschaft | Welche Angaben, Nachweise und Prüfpunkte werden für Eigentum Anteile benötigt? |
| `plans.certificates` | Pläne Bescheinigungen | `offen` | Mandantschaft | Welche Angaben, Nachweise und Prüfpunkte werden für Pläne Bescheinigungen benötigt? |
| `encumbrance.handling` | Belastung Behandlung | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Belastung Behandlung benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.division_declaration` | Dokument: Teilung Erklärung | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.plans_certificate` | Dokument: Pläne Bescheinigung | `offen` | freigegebener Nachweisspeicher |
| `doc.land_register_excerpt` | Dokument: aktueller Grundbuchauszug | `offen` | nac-grundbuch-portal oder manuell geprüfter Upload |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.use_case` | Entscheidung: Nutzung Fall | `offen` |
| `decision.special_use_rights` | Entscheidung: Sonderfall Nutzung Rechte | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.plan_certificate_review` | Prüfgate: Plan Bescheinigung Prüfung | `offen` |
| `gate.land_register_implementation` | Prüfgate: Grundbuch Register Umsetzung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.plan_package` | Nachweis: Plan Paket | `offen` |
| `evidence.unit_register_trace` | Nachweis: Einheit Register Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
