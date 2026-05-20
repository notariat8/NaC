# Teilungserklärung nach WEG

Status: offen
Reifegrad: Nächste-10-Usecase, P0
KG-Knoten: `case.teilungserklaerung_weg`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Aufteilung eines Gebaeudes in Wohnungs- oder Teileigentum mit Teilungserklärung, Gemeinschaftsordnung, Plänen, Bescheinigungen und Grundbuchumsetzung.

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
| `property.identity` | Grundstück Identität | Notariatsfachkraft | land_register_review |
| `owner.identity` | Eigentümer Identität | Notariat | identity_gate, drafting |
| `unit.structure` | Einheit Struktur | Mandantschaft | drafting, plans |
| `ownership.shares` | Eigentum Anteile | Mandantschaft | declaration |
| `plans.certificates` | Pläne Bescheinigungen | Mandantschaft | evidence_package, filing |
| `encumbrance.handling` | Belastung Behandlung | Notariat | legal_review, filing |

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
- `src.weg.8`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case teilungserklaerung-weg
python scripts/notary_kg.py --repo-root . editor-view teilungserklaerung-weg
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
