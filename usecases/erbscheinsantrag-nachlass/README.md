# Erbscheinsantrag / Nachlassangelegenheiten

Status: offen
Reifegrad: Top-10-Usecase, P0
KG-Knoten: `case.erbscheinsantrag_nachlass`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Antrag und Erklärungen für Erbschein, Nachlassgericht, Ausschlagung, eidesstattliche Versicherung und erbrechtliche Nachweisführung.

Diese Datei ist die fachliche Vorderseite für Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht für offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 8 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 5 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Prüfgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `decedent.identity` | Erblasser Identität | Antragstellende Person | application, court_route |
| `residence.jurisdiction` | Wohnsitz Zuständigkeit | Notariatsfachkraft | court_route |
| `applicants.identity` | Antragsteller Identität | Notariatsfachkraft | identity_gate, application |
| `heirship.basis` | Erbenstellung Grundlage | Notariat | legal_review, application |
| `family.evidence` | Familie Nachweis | Antragstellende Person | evidence_package |
| `dispositions.evidence` | Verfügungen Nachweis | Notariatsfachkraft | legal_review, evidence_package |
| `renunciations.disclaimers` | Ausschlagungen Ausschlagungen | Notariat | legal_review |
| `oath.statement` | Eidesstattliche Versicherung Erklärung | Notariat | application, appointment |

## Grenzen Für Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehört in einen privaten Fork mit Rollen, Freigaben und geprüftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primäre Plugins:

- `nac-regulated-core`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.bgb.2353`
- `src.gbo`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case erbscheinsantrag-nachlass
python scripts/notary_kg.py --repo-root . editor-view erbscheinsantrag-nachlass
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
