# Testament Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `legacy-alias`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.testament`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `testator.identity` | Testierende Person Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Testierende Person Identitaet benoetigt? |
| `capacity.flags` | Geschaeftsfaehigkeit Pruefflaggen | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Geschaeftsfaehigkeit Pruefflaggen benoetigt? |
| `family.structure` | Familie Struktur | `offen` | Testierende Person | Welche Angaben, Nachweise und Pruefpunkte werden fuer Familie Struktur benoetigt? |
| `assets.categories` | Vermoegen Kategorien | `offen` | Testierende Person | Welche Angaben, Nachweise und Pruefpunkte werden fuer Vermoegen Kategorien benoetigt? |
| `dispositions.wishes` | Verfuegungen Wuensche | `offen` | Testierende Person | Welche Angaben, Nachweise und Pruefpunkte werden fuer Verfuegungen Wuensche benoetigt? |
| `prior.dispositions` | Vorverfuegungen Verfuegungen | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Vorverfuegungen Verfuegungen benoetigt? |
| `executor.choice` | Testamentsvollstrecker Auswahl | `offen` | Testierende Person | Welche Angaben, Nachweise und Pruefpunkte werden fuer Testamentsvollstrecker Auswahl benoetigt? |
| `custody.register` | Verwahrung Register | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Verwahrung Register benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.disposition_draft` | Dokument: Disposition Entwurf | `offen` | nach notarieller Pruefung erzeugter Workflow-Entwurf |
| `doc.prior_dispositions` | Dokument: Vorverfuegungen Verfuegungen | `offen` | manuell gepruefter Upload oder vorgelegtes Original |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.instrument_type` | Entscheidung: Instrument Art | `offen` |
| `decision.executor` | Entscheidung: Testamentsvollstrecker | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.capacity_review` | Pruefgate: Geschaeftsfaehigkeit Pruefung | `offen` |
| `gate.binding_effect_review` | Pruefgate: Bindungswirkung Wirkung Pruefung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.capacity_notes` | Nachweis: Geschaeftsfaehigkeit Vermerke | `offen` |
| `evidence.custody_registration` | Nachweis: Verwahrung Registrierung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
