# Erbscheinsantrag / Nachlassangelegenheiten Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `top10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.erbscheinsantrag_nachlass`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `decedent.identity` | Erblasser Identität | `offen` | Antragsteller | Welche Angaben, Nachweise und Prüfpunkte werden für Erblasser Identität benötigt? |
| `residence.jurisdiction` | Wohnsitz Zuständigkeit | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Wohnsitz Zuständigkeit benötigt? |
| `applicants.identity` | Antragsteller Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Antragsteller Identität benötigt? |
| `heirship.basis` | Erbenstellung Grundlage | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Erbenstellung Grundlage benötigt? |
| `family.evidence` | Familie Nachweis | `offen` | Antragsteller | Welche Angaben, Nachweise und Prüfpunkte werden für Familie Nachweis benötigt? |
| `dispositions.evidence` | Verfügungen Nachweis | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Verfügungen Nachweis benötigt? |
| `renunciations.disclaimers` | Ausschlagungen Ausschlagungen | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Ausschlagungen Ausschlagungen benötigt? |
| `oath.statement` | Eidesstattliche Versicherung Erklärung | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Eidesstattliche Versicherung Erklärung benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.death_certificate_reference` | Dokument: Sterbefall Bescheinigung Referenz | `offen` | manuell geprüfter Nachweisspeicher |
| `doc.application_draft` | Dokument: Antrag Entwurf | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.family_evidence` | Dokument: Familie Nachweis | `offen` | manuell geprüfter Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.certificate_type` | Entscheidung: Bescheinigung Art | `offen` |
| `decision.oath_required` | Entscheidung: Eidesstattliche Versicherung erforderlich | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.heirship_review` | Prüfgate: Erbenstellung Prüfung | `offen` |
| `gate.oath_readiness` | Prüfgate: Eidesstattliche Versicherung Bereitschaft | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.evidence_package` | Nachweis: Nachweis Paket | `offen` |
| `evidence.court_submission` | Nachweis: Gericht Einreichung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
