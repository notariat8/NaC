# Vollmacht für Immobilien- oder Gesellschaftsgeschäfte Wissensgraph

Status: usecase-lokale statische KG-Basis
Letzte Aktualisierung: 2026-05-17
Kataloggruppe: `next10`
Usecase: [README.md](README.md)
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)
KG-Knoten: `case.vollmacht_immobilien_gesellschaft`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht für den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows dürfen Status und Nachweisreferenzen nur über geprüfte Git-Änderungen aktualisieren; echte Mandatswerte bleiben außerhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `principal.identity` | Vollmachtgeber Identität | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Vollmachtgeber Identität benötigt? |
| `agent.identity` | Bevollmaechtigter Identität | `offen` | Vollmachtgeber | Welche Angaben, Nachweise und Prüfpunkte werden für Bevollmaechtigter Identität benötigt? |
| `transaction.scope` | Geschäft Umfang | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Geschäft Umfang benötigt? |
| `form.requirement` | Form Anforderung | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Form Anforderung benötigt? |
| `limitations.expiry` | Beschraenkungen Ablauf | `offen` | Notariat | Welche Angaben, Nachweise und Prüfpunkte werden für Beschraenkungen Ablauf benötigt? |
| `delivery.evidence` | Zustellung Nachweis | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Prüfpunkte werden für Zustellung Nachweis benötigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.power_of_attorney` | Dokument: Vollmacht von Vollmacht | `offen` | nach Prüfung erzeugter Workflow-Entwurf |
| `doc.scope_reference` | Dokument: Umfang Referenz | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.form_route` | Entscheidung: Form Route | `offen` |
| `decision.scope_type` | Entscheidung: Umfang Art | `offen` |

## Prüfgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.form_review` | Prüfgate: Form Prüfung | `offen` |
| `gate.delivery_control` | Prüfgate: Zustellung Kontrolle | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.form_review` | Nachweis: Form Prüfung | `offen` |
| `evidence.copy_delivery` | Nachweis: Ausfertigung Zustellung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
