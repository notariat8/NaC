# Geschäftsanteilsübertragung GmbH

Status: offen
Reifegrad: Nächste-10-Usecase, P0
KG-Knoten: `case.geschaeftsanteilsuebertragung_gmbh`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Kauf, Schenkung oder sonstige Übertragung von GmbH-Geschäftsanteilen mit Beteiligten, Anteilskette, Zustimmungsvorbehalten, Kaufpreis, Gesellschafterliste und Register-Nachweisen.

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
| `company.identity` | Gesellschaft Identität | Notariatsfachkraft | register_review |
| `share.identity` | Geschäftsanteil Identität | Notariat | legal_review, shareholder_list |
| `seller.identity` | Verkäufer Identität | Notariatsfachkraft | identity_gate, drafting |
| `buyer.identity` | Käufer Identität | Notariat | aml_review, shareholder_list |
| `consents.restrictions` | Zustimmungen Beschraenkungen | Notariat | legal_review |
| `consideration.tax` | Gegenleistung Steuer | Notariat | drafting, closing |

## Grenzen Für Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehört in einen privaten Fork mit Rollen, Freigaben und geprüftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primäre Plugins:

- `nac-regulated-core`
- `nac-bnotk-xnp`
- `nac-handelsregister`
- `nac-idaas`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.gmbhg.15`
- `src.hgb.12`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case geschaeftsanteilsuebertragung-gmbh
python scripts/notary_kg.py --repo-root . editor-view geschaeftsanteilsuebertragung-gmbh
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
