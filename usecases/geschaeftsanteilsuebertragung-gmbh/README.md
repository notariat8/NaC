# Geschaeftsanteilsuebertragung GmbH

Status: offen  
Reifegrad: Naechste-10-Usecase, P0  
KG-Knoten: `case.geschaeftsanteilsuebertragung_gmbh`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Kauf, Schenkung oder sonstige Uebertragung von GmbH-Geschaeftsanteilen mit Beteiligten, Anteilskette, Zustimmungsvorbehalten, Kaufpreis, Gesellschafterliste und Register-Nachweisen.

Diese Datei ist die fachliche Vorderseite fuer Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht fuer offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 6 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 5 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Pruefgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `company.identity` | Gesellschaft Identitaet | Notariatsfachkraft | register_review |
| `share.identity` | Geschaeftsanteil Identitaet | Notariat | legal_review, shareholder_list |
| `seller.identity` | Verkaeufer Identitaet | Notariatsfachkraft | identity_gate, drafting |
| `buyer.identity` | Kaeufer Identitaet | Notariat | aml_review, shareholder_list |
| `consents.restrictions` | Zustimmungen Beschraenkungen | Notariat | legal_review |
| `consideration.tax` | Gegenleistung Steuer | Notariat | drafting, closing |

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
- `noc-idaas`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.gmbhg.15`
- `src.hgb.12`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case geschaeftsanteilsuebertragung-gmbh
python scripts/notary_kg.py --repo-root . editor-view geschaeftsanteilsuebertragung-gmbh
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
