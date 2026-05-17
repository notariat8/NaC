# Steuer-aaS Steuer-Readiness

Status: aktive Aufnahme  
Reifegrad: aktive Aufnahmequelle, P1  
KG-Knoten: `case.steuer_aas`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Steuer-Readiness-Usecase fuer deterministische Aufnahme, ELSTER-nahe Vorbereitung und pruefbare Nachweise ohne echte Steuerdaten in Git.

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
| `tax.subject` | Steuer Subjekt | Steuerfachkraft | intake, routing |
| `tax.type` | Steuer Art | Steuerfachkraft | routing, drafting |
| `period.scope` | Zeitraum Umfang | Steuerfachkraft | deadline_control |
| `elster.identity` | ELSTER Identitaet | Systembetreuung | technical_readiness |
| `documents.package` | Dokumente Paket | Steuerfachkraft | evidence, review |
| `audit.evidence` | Pruefung Nachweis | Compliance | evidence, audit |

## Grenzen Fuer Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehoert in einen privaten Fork mit Rollen, Freigaben und geprueftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primaere Plugins:

- `noc-regulated-core`
- `noc-elster-eric`

Workflow-Bezug:

- `workflow.tax_readiness_intake`

Fachliche Anker im KG-Modell:

- `src.beurkg`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case steuer-aas
python scripts/notary_kg.py --repo-root . editor-view steuer-aas
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
