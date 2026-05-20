# Vereinsregisteranmeldung

Status: offen
Reifegrad: Nächste-10-Usecase, P1
KG-Knoten: `case.vereinsregisteranmeldung`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Vereinsregisteranmeldungen für Vorstandswechsel, Satzungsänderungen, Gründung oder Aufloesung mit öffentlicher Beglaubigung, Beschlüssen und Anlagen.

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
| `association.identity` | Verein Identität | Notariatsfachkraft | register_review |
| `filing.type` | Einreichung Art | Notariat | drafting |
| `board.identity` | Vorstand Identität | Notariatsfachkraft | identity_gate, certification |
| `resolution.evidence` | Beschluss Nachweis | association | attachments |
| `articles.current` | Satzung aktueller Stand | association | legal_review |
| `filing.route` | Einreichung Route | Notariatsfachkraft | submission |

## Grenzen Für Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehört in einen privaten Fork mit Rollen, Freigaben und geprüftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primäre Plugins:

- `nac-regulated-core`
- `nac-bnotk-xnp`
- `nac-idaas`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.bgb.77`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case vereinsregisteranmeldung
python scripts/notary_kg.py --repo-root . editor-view vereinsregisteranmeldung
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
