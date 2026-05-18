# Grundschuld / Hypothekenbestellung

Status: offen
Reifegrad: Top-10-Usecase, P0
KG-Knoten: `case.grundschuld_hypothek`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Bestellung, Änderung oder Refinanzierung einer Grundschuld oder Hypothek mit Eigentümer, Darlehensnehmer, Glaeubiger, Rang und Vollstreckungsunterwerfung.

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
| `property.identity` | Grundstück Identität | Notariatsfachkraft | land_register_review, filing |
| `owner.identity` | Eigentümer Identität | Notariatsfachkraft | identity_gate, drafting |
| `debtor.identity` | Schuldner Identität | Notariat | drafting, consumer_review |
| `lender.identity` | Darlehensgeber Identität | Notariatsfachkraft | bank_instruction_review, filing |
| `charge.amount` | Grundschuld amount | Notariatsfachkraft | drafting, bank_instruction_review |
| `security.purpose` | Sicherung Zweck | Notariat | legal_review, consumer_review |
| `ranking.requirement` | Rang Anforderung | Notariatsfachkraft | land_register_review, filing |
| `enforcement.clause` | Vollstreckung Klausel | Notariat | drafting, legal_review |

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

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.gbo`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case grundschuld-hypothekenbestellung
python scripts/notary_kg.py --repo-root . editor-view grundschuld-hypothekenbestellung
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
