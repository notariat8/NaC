# Bauträgervertrag

Status: offen
Reifegrad: Nächste-10-Usecase, P0
KG-Knoten: `case.bautraegervertrag`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Kauf einer Immobilie oder Einheit vom Bauträger mit Bauverpflichtungen, Ratenplan, Fertigstellungsstand, Sicherheiten und Verbraucherschutz-Gates.

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
| `developer.identity` | Bauträger Identität | Notariatsfachkraft | identity_gate, drafting |
| `buyer.identity` | Käufer Identität | Notariat | consumer_gate, appointment |
| `object.identity` | Objekt Identität | Notariatsfachkraft | drafting, land_register_review |
| `construction.specification` | Bauleistung Spezifikation | Entwicklung | drafting, technical_attachments |
| `installment.plan` | Ratenplan Plan | Notariat | legal_review, execution |
| `defects.acceptance` | Mängel acceptance | Notariat | drafting, closing |

## Grenzen Für Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehört in einen privaten Fork mit Rollen, Freigaben und geprüftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primäre Plugins:

- `nac-regulated-core`
- `nac-grundbuch-portal`
- `nac-bnotk-xnp`
- `nac-idaas`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.bgb.311b`
- `src.bgb.650u`
- `src.abschlagsv`
- `src.gbo.19_29_46`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case bautraegervertrag
python scripts/notary_kg.py --repo-root . editor-view bautraegervertrag
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
