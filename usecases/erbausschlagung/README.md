# Erbausschlagung

Status: offen
Reifegrad: Nächste-10-Usecase, P0
KG-Knoten: `case.erbausschlagung`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Erbausschlagungserklärung gegenüber dem Nachlassgericht mit Frist, Identität, Vertretung, Minderjährigen- oder Betreuungsbezug und Zustellnachweis.

Diese Datei ist die fachliche Vorderseite für Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht für offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 6 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 5 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Prüfgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `decedent.identity` | Erblasser Identität | Antragstellende Person | court_route |
| `renouncer.identity` | Ausschlagende Person Identität | Notariat | identity_gate, declaration |
| `deadline.status` | Frist Status | Notariat | deadline_review |
| `heirship.basis` | Erbenstellung Grundlage | Antragstellende Person | legal_review |
| `representation.minors` | Representation Minderjährige | Notariat | approval_review |
| `delivery.route` | Zustellung Route | Notariatsfachkraft | submission |

## Grenzen Für Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehört in einen privaten Fork mit Rollen, Freigaben und geprüftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primäre Plugins:

- `nac-regulated-core`
- `nac-idaas`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.bgb.1945`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case erbausschlagung
python scripts/notary_kg.py --repo-root . editor-view erbausschlagung
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
