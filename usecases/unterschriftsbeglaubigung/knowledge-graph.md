# Beglaubigung von Unterschriften Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `top10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.unterschriftsbeglaubigung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `signer.identity` | Unterzeichner Identitaet | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Unterzeichner Identitaet benoetigt? |
| `document.purpose` | Dokument Zweck | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Dokument Zweck benoetigt? |
| `signature.mode` | Unterschrift Modus | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Unterschrift Modus benoetigt? |
| `language.understanding` | Sprache Verstaendnis | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Sprache Verstaendnis benoetigt? |
| `representation.context` | Representation Kontext | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Representation Kontext benoetigt? |
| `copies.routing` | Ausfertigungen Weiterleitung | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Ausfertigungen Weiterleitung benoetigt? |
| `special.form` | Sonderfall Form | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Sonderfall Form benoetigt? |
| `fee.metadata` | Gebuehr Metadaten | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Gebuehr Metadaten benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.signed_document` | Dokument: Unterzeichnet Dokument | `offen` | manuell gepruefter Upload oder Papieroriginal |
| `doc.certification_note` | Dokument: Beglaubigung Vermerk | `offen` | Notarsystem |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.certification_scope` | Entscheidung: Beglaubigung Umfang | `offen` |
| `decision.routing` | Entscheidung: Weiterleitung | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.identity_and_signature` | Pruefgate: Identitaet and Unterschrift | `offen` |
| `gate.form_route` | Pruefgate: Form Route | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.identity_check` | Nachweis: Identitaet Pruefung | `offen` |
| `evidence.delivery_trace` | Nachweis: Zustellung Nachverfolgung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
