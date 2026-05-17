# AO52 gemeinnuetziges Softwareunternehmen

Status: aktive Aufnahme  
Reifegrad: aktive Aufnahmequelle, P1  
KG-Knoten: `case.ao52aas_gemeinnuetzigkeit`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Gruendungs- und Readiness-Paket fuer ein gemeinnuetzig ausgerichtetes Softwareunternehmen mit Zweckbild, Governance, Finanzierung sowie Register- und Steuer-Readiness.

Diese Datei ist die fachliche Vorderseite fuer Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht fuer offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 6 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 1 | [knowledge-graph.md](knowledge-graph.md) |
| Pruefgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `purpose.model` | Zweck Modell | Gruenderkreis | drafting, tax_readiness |
| `entity.form` | Rechtstraeger Form | Notariatsfachkraft | drafting, register_package |
| `funding.model` | Finanzierung Modell | Gruenderkreis | tax_readiness, governance_review |
| `governance.rules` | Governance Regeln | Notariat | drafting, legal_review |
| `tax.precheck` | Steuer Vorpruefung | Steuerfachkraft | tax_readiness |
| `software.scope` | Software Umfang | Gruenderkreis | drafting, risk_review |

## Grenzen Fuer Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehoert in einen privaten Fork mit Rollen, Freigaben und geprueftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primaere Plugins:

- `noc-regulated-core`
- `noc-bnotk-xnp`
- `noc-handelsregister`
- `noc-elster-eric`

Workflow-Bezug:

- `workflow.company_formation_intake`
- `workflow.tax_readiness_intake`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.gmbhg`
- `src.hgb.12`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case ao52aas-gemeinnuetzigkeit
python scripts/notary_kg.py --repo-root . editor-view ao52aas-gemeinnuetzigkeit
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
