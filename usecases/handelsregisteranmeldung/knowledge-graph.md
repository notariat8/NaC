# Handelsregisteranmeldung Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-28
Kataloggruppe: `top10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.handelsregisteranmeldung`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `entity.identity` | Rechtsträger Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Rechtsträger Identität benötigt? |
| `event.type` | Vorgang Art | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Vorgang Art benötigt? |
| `signers.identity` | Unterzeichner Identität | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Unterzeichner Identität benötigt? |
| `corporate.resolution` | Gesellschaftsrecht Beschluss | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Gesellschaftsrecht Beschluss benötigt? |
| `attachments.required` | Anlagen erforderlich | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Anlagen erforderlich benötigt? |
| `effective.date` | Wirksamkeit Datum | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Wirksamkeit Datum benötigt? |
| `xnp.route` | XNP Route | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für XNP Route benötigt? |
| `fees.costs` | Gebühren Kosten | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Gebühren Kosten benötigt? |
| `cost.business_value` | Geschäftswert für GNotKG-Kostenprüfung | `offen` | Notarin/Notar | Welche Geschäftswertangaben, Wertvorschriften und Nachweise werden für die GNotKG-Kostenprüfung benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.register_application` | Dokument: Register Antrag | `offen` | nac-bnotk-xnp und nac-handelsregister |
| `doc.corporate_evidence` | Dokument: Gesellschaftsrecht Nachweis | `offen` | manuell geprüfter Upload oder erzeugter Entwurf |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.event_route` | Entscheidung: Vorgang Route | `offen` |
| `decision.signature_method` | Entscheidung: Unterschrift Methode | `offen` |
| `decision.gnotkg_cost_path` | Entscheidung: GNotKG-Kostenweg | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.public_certification` | Prüfgate: Öffentlich Beglaubigung | `offen` |
| `gate.electronic_format` | Prüfgate: Elektronisch Format | `offen` |
| `gate.gnotkg_cost_review` | Prüfgate: GNotKG-Kostenprüfung | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.certification_trace` | Nachweis: Beglaubigung Nachverfolgung | `offen` |
| `evidence.register_response` | Nachweis: Register Rückmeldung | `offen` |
| `evidence.gnotkg_cost_note` | Nachweis: GNotKG-Kostenentwurf und Kostenprüfung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
