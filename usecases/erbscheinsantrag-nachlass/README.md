# Erbscheinsantrag / Nachlassangelegenheiten

Status: offen  
Reifegrad: Top-10-Usecase, P0  
KG-Knoten: `case.erbscheinsantrag_nachlass`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Antrag und Erklaerungen fuer Erbschein, Nachlassgericht, Ausschlagung, eidesstattliche Versicherung und erbrechtliche Nachweisfuehrung.

Diese Datei ist die fachliche Vorderseite fuer Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht fuer offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 8 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 5 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Pruefgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `decedent.identity` | Erblasser Identitaet | Antragstellende Person | application, court_route |
| `residence.jurisdiction` | Wohnsitz Zustaendigkeit | Notariatsfachkraft | court_route |
| `applicants.identity` | Antragsteller Identitaet | Notariatsfachkraft | identity_gate, application |
| `heirship.basis` | Erbenstellung Grundlage | Notariat | legal_review, application |
| `family.evidence` | Familie Nachweis | Antragstellende Person | evidence_package |
| `dispositions.evidence` | Verfuegungen Nachweis | Notariatsfachkraft | legal_review, evidence_package |
| `renunciations.disclaimers` | Ausschlagungen Ausschlagungen | Notariat | legal_review |
| `oath.statement` | Eidesstattliche Versicherung Erklaerung | Notariat | application, appointment |

## Grenzen Fuer Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehoert in einen privaten Fork mit Rollen, Freigaben und geprueftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primaere Plugins:

- `noc-regulated-core`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.bgb.2353`
- `src.gbo`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case erbscheinsantrag-nachlass
python scripts/notary_kg.py --repo-root . editor-view erbscheinsantrag-nachlass
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
