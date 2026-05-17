# Vollmacht fuer Immobilien- oder Gesellschaftsgeschaefte Wissensgraph

Status: usecase-lokale statische KG-Basis  
Letzte Aktualisierung: 2026-05-17  
Kataloggruppe: `next10`  
Usecase: [README.md](README.md)  
Maschinenlesbare KG: [knowledge-graph.graph.json](knowledge-graph.graph.json)  
KG-Knoten: `case.vollmacht_immobilien_gesellschaft`

## Betriebsmodell

Diese Datei ist die menschliche Review-Sicht fuer den usecase-lokalen statischen Wissensgraphen. Die danebenliegende JSON-Datei ist der maschinenlesbare Workflow-Stand. Workflows duerfen Status und Nachweisreferenzen nur ueber gepruefte Git-Aenderungen aktualisieren; echte Mandatswerte bleiben ausserhalb des Repository.

## Offene Angabenknoten

| ID | Bezeichnung | Status | Verantwortliche Rolle | Offene Frage |
| --- | --- | --- | --- | --- |
| `principal.identity` | Vollmachtgeber Identitaet | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Vollmachtgeber Identitaet benoetigt? |
| `agent.identity` | Bevollmaechtigter Identitaet | `offen` | Vollmachtgeber | Welche Angaben, Nachweise und Pruefpunkte werden fuer Bevollmaechtigter Identitaet benoetigt? |
| `transaction.scope` | Geschaeft Umfang | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Geschaeft Umfang benoetigt? |
| `form.requirement` | Form Anforderung | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Form Anforderung benoetigt? |
| `limitations.expiry` | Beschraenkungen Ablauf | `offen` | Notariat | Welche Angaben, Nachweise und Pruefpunkte werden fuer Beschraenkungen Ablauf benoetigt? |
| `delivery.evidence` | Zustellung Nachweis | `offen` | Notariatsfachkraft | Welche Angaben, Nachweise und Pruefpunkte werden fuer Zustellung Nachweis benoetigt? |

## Dokumente

| ID | Bezeichnung | Status | Quelle |
| --- | --- | --- | --- |
| `doc.power_of_attorney` | Dokument: Vollmacht von Vollmacht | `offen` | nach Pruefung erzeugter Workflow-Entwurf |
| `doc.scope_reference` | Dokument: Umfang Referenz | `offen` | freigegebener Nachweisspeicher |

## Entscheidungen

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `decision.form_route` | Entscheidung: Form Route | `offen` |
| `decision.scope_type` | Entscheidung: Umfang Art | `offen` |

## Pruefgates

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `gate.form_review` | Pruefgate: Form Pruefung | `offen` |
| `gate.delivery_control` | Pruefgate: Zustellung Kontrolle | `offen` |

## Nachweise

| ID | Bezeichnung | Status |
| --- | --- | --- |
| `evidence.form_review` | Nachweis: Form Pruefung | `offen` |
| `evidence.copy_delivery` | Nachweis: Ausfertigung Zustellung | `offen` |

## Datenschutzregel

Alle `value`-Felder bleiben in Git leer. Die KG speichert nur Workflow-Stand, offene Fragen und Nachweisreferenzen; sie speichert keine echten Mandatsdaten, keine Secrets und keine personenbezogenen Daten.
