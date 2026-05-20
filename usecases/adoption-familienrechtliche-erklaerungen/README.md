# Adoption / familienrechtliche Erklärungen

Status: offen
Reifegrad: Nächste-10-Usecase, P1
KG-Knoten: `case.adoption_familienrechtliche_erklaerungen`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Notarielle Adoptionszustimmungen und familienrechtliche Erklärungen mit Identität, Zustimmungspersonen, Gerichtsziel, Geschäftsfähigkeit, Unwiderruflichkeit und Schutz sensibler Daten.

Diese Datei ist die fachliche Vorderseite für Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht für offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 6 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 4 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Prüfgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `case.type` | Fall Art | Notariat | legal_review |
| `child.identity_context` | Kind Identität Kontext | Mandantschaft | drafting |
| `consenting_party.identity` | Zustimmende Beteiligter Identität | Notariat | identity_gate, capacity_review |
| `court.destination` | Gericht Zielgericht | Notariatsfachkraft | submission |
| `irrevocability.warning` | Unwiderruflichkeit Belehrung | Notariat | legal_review, appointment |
| `additional.approvals` | Weitere Genehmigungen | Notariat | approval_review |

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
- `src.bgb.1750`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case adoption-familienrechtliche-erklaerungen
python scripts/notary_kg.py --repo-root . editor-view adoption-familienrechtliche-erklaerungen
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
