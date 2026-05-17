# Erbscheinsantrag / Nachlassangelegenheiten Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `top10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.erbscheinsantrag_nachlass`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `decedent.identity` | Erblasser Identitaet | `offen` | Antragsteller | Welche Angaben, Nachweise und Pruefpunkte werden fuer Erblasser Identitaet benoetigt? |
| `residence.jurisdiction` | Wohnsitz Zustaendigkeit | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Wohnsitz Zustaendigkeit benoetigt? |
| `applicants.identity` | Antragsteller Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Antragsteller Identitaet benoetigt? |
| `heirship.basis` | Erbenstellung Grundlage | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Erbenstellung Grundlage benoetigt? |
| `family.evidence` | Familie Nachweis | `offen` | Antragsteller | Welche Angaben, Nachweise und Pruefpunkte werden fuer Familie Nachweis benoetigt? |
| `dispositions.evidence` | Verfuegungen Nachweis | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Verfuegungen Nachweis benoetigt? |
| `renunciations.disclaimers` | Ausschlagungen Ausschlagungen | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Ausschlagungen Ausschlagungen benoetigt? |
| `oath.statement` | Eidesstattliche Versicherung Erklaerung | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Eidesstattliche Versicherung Erklaerung benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.death_certificate_reference` | Dokument: Sterbefall Bescheinigung Referenz | `offen` | manuell gepruefter Nachweisspeicher |
| `doc.application_draft` | Dokument: Antrag Entwurf | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.family_evidence` | Dokument: Familie Nachweis | `offen` | manuell gepruefter Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.certificate_type` | Entscheidung: Bescheinigung Art | `offen` |
| `decision.oath_required` | Entscheidung: Eidesstattliche Versicherung erforderlich | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.heirship_review` | Pruefgate: Erbenstellung Pruefung | `offen` |
| `gate.oath_readiness` | Pruefgate: Eidesstattliche Versicherung Bereitschaft | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.evidence_package` | Nachweis: Nachweis Paket | `offen` |
| `evidence.court_submission` | Nachweis: Gericht Einreichung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
