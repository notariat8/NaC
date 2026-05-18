# Testament Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `legacy-alias`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.testament`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `testator.identity` | Testierende Person Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Testierende Person Identität benötigt? |
| `capacity.flags` | Geschäftsfähigkeit Prüfflaggen | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Geschäftsfähigkeit Prüfflaggen benötigt? |
| `family.structure` | Familie Struktur | `offen` | Testierende Person | Welche Angaben, Nachweise und Prüfpunkte werden für Familie Struktur benötigt? |
| `assets.categories` | Vermögen Kategorien | `offen` | Testierende Person | Welche Angaben, Nachweise und Prüfpunkte werden für Vermögen Kategorien benötigt? |
| `dispositions.wishes` | Verfügungen Wünsche | `offen` | Testierende Person | Welche Angaben, Nachweise und Prüfpunkte werden für Verfügungen Wünsche benötigt? |
| `prior.dispositions` | Vorverfügungen Verfügungen | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Vorverfügungen Verfügungen benötigt? |
| `executor.choice` | Testamentsvollstrecker Auswahl | `offen` | Testierende Person | Welche Angaben, Nachweise und Prüfpunkte werden für Testamentsvollstrecker Auswahl benötigt? |
| `custody.register` | Verwahrung Register | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Verwahrung Register benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.disposition_draft` | Dokument: Disposition Entwurf | `offen` | nach notarieller Prüfung erzeugter Workflow-Entwurf |
| `doc.prior_dispositions` | Dokument: Vorverfügungen Verfügungen | `offen` | manuell geprüfter Upload oder vorgelegtes Original |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.instrument_type` | Entscheidung: Instrument Art | `offen` |
| `decision.executor` | Entscheidung: Testamentsvollstrecker | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.capacity_review` | Prüfgate: Geschäftsfähigkeit Prüfung | `offen` |
| `gate.binding_effect_review` | Prüfgate: Bindungswirkung Wirkung Prüfung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.capacity_notes` | Nachweis: Geschäftsfähigkeit Vermerke | `offen` |
| `evidence.custody_registration` | Nachweis: Verwahrung Registrierung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
