# Löschungsbewilligung / Grundbuchlöschung

Status: offen
Reifegrad: Nächste-10-Usecase, P0
KG-Knoten: `case.loeschungsbewilligung_grundbuchloeschung`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Löschung eingetragener Rechte im Grundbuch, häufig alter Grundschulden nach Darlehensrückzahlung, mit Bewilligung, Eigentümerzustimmung, Urkundenform und Einreichungsnachweis.

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
| `property.identity` | Grundstück Identität | Notariatsfachkraft | land_register_review, filing |
| `right.identity` | Recht Identität | Notariatsfachkraft | drafting, filing |
| `creditor.authorization` | Glaeubiger Berechtigung | Notariat | authority_review |
| `owner.consent` | Eigentümer Zustimmung | Notariatsfachkraft | identity_gate, filing |
| `brief.status` | Brief Status | Notariatsfachkraft | evidence_package |
| `filing.route` | Einreichung Route | Notariatsfachkraft | submission, closing |

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
- `src.gbo.19_29_46`
- `src.bgb.875`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case loeschungsbewilligung-grundbuchloeschung
python scripts/notary_kg.py --repo-root . editor-view loeschungsbewilligung-grundbuchloeschung
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
