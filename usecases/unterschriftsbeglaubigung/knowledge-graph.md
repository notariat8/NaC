# Beglaubigung von Unterschriften Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `top10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.unterschriftsbeglaubigung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `signer.identity` | Unterzeichner Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Unterzeichner Identität benötigt? |
| `document.purpose` | Dokument Zweck | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Dokument Zweck benötigt? |
| `signature.mode` | Unterschrift Modus | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Unterschrift Modus benötigt? |
| `language.understanding` | Sprache Verständnis | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Sprache Verständnis benötigt? |
| `representation.context` | Representation Kontext | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Representation Kontext benötigt? |
| `copies.routing` | Ausfertigungen Weiterleitung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Ausfertigungen Weiterleitung benötigt? |
| `special.form` | Sonderfall Form | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Sonderfall Form benötigt? |
| `fee.metadata` | Gebühr Metadaten | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Gebühr Metadaten benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.signed_document` | Dokument: Unterzeichnet Dokument | `offen` | manuell geprüfter Upload oder Papieroriginal |
| `doc.certification_note` | Dokument: Beglaubigung Vermerk | `offen` | Notarsystem |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.certification_scope` | Entscheidung: Beglaubigung Umfang | `offen` |
| `decision.routing` | Entscheidung: Weiterleitung | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.identity_and_signature` | Prüfgate: Identität and Unterschrift | `offen` |
| `gate.form_route` | Prüfgate: Form Route | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.identity_check` | Nachweis: Identität Prüfung | `offen` |
| `evidence.delivery_trace` | Nachweis: Zustellung Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
