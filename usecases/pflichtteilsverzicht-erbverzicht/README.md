# Pflichtteilsverzicht / Erbverzicht

Status: offen  
Reifegrad: Naechste-10-Usecase, P1  
KG-Knoten: `case.pflichtteilsverzicht_erbverzicht`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Vertraglicher Erb- oder Pflichtteilsverzicht, haeufig in der Familiennachfolge, mit Beteiligten, Umfang, Abfindung, Erstreckung auf Abkoemmlinge und Fairness-Pruefung.

Diese Datei ist die fachliche Vorderseite fuer Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht fuer offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 6 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 4 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Pruefgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `future_decedent.identity` | Kuenftiger Erblasser Identitaet | Notariat | identity_gate, legal_review |
| `waiver_party.identity` | Verzicht Beteiligter Identitaet | Notariat | identity_gate, approval_review |
| `waiver.scope` | Verzicht Umfang | Notariat | drafting |
| `descendant.effect` | Abkoemmlinge Wirkung | Notariat | legal_review |
| `compensation.model` | Abfindung Modell | Mandantschaft | drafting, tax_flags |
| `family.fairness_flags` | Familie Fairness Pruefflaggen | Notariat | fairness_review |

## Grenzen Fuer Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehoert in einen privaten Fork mit Rollen, Freigaben und geprueftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primaere Plugins:

- `noc-regulated-core`
- `noc-idaas`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.bgb.2346_2348`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case pflichtteilsverzicht-erbverzicht
python scripts/notary_kg.py --repo-root . editor-view pflichtteilsverzicht-erbverzicht
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
