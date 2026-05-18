# Testament / Erbvertrag

Status: offen
Reifegrad: Top-10-Usecase, P0
KG-Knoten: `case.testament_erbvertrag`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Vorbereitung und Beurkundung testamentarischer Verfügungen oder Erbverträge mit Geschäftsfähigkeit, Familienlage, Vermögen, Vorverfügungen und Verwahrungsgates.

Diese Datei ist die fachliche Vorderseite für Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht für offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 8 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 4 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Prüfgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `testator.identity` | Testierende Person Identität | Notariat | identity_gate, capacity_review |
| `capacity.flags` | Geschäftsfähigkeit Prüfflaggen | Notariat | legal_review, appointment |
| `family.structure` | Familie Struktur | testator | drafting, mandatory_share_review |
| `assets.categories` | Vermögen Kategorien | testator | drafting, tax_or_business_flags |
| `dispositions.wishes` | Verfügungen Wünsche | testator | drafting, legal_review |
| `prior.dispositions` | Vorverfügungen Verfügungen | Notariat | legal_review, custody |
| `executor.choice` | Testamentsvollstrecker Auswahl | testator | drafting |
| `custody.register` | Verwahrung Register | Notariatsfachkraft | closing |

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

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case testament-erbvertrag
python scripts/notary_kg.py --repo-root . editor-view testament-erbvertrag
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
