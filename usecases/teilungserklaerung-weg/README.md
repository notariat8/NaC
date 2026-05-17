# Teilungserklaerung nach WEG

Status: offen  
Reifegrad: Naechste-10-Usecase, P0  
KG-Knoten: `case.teilungserklaerung_weg`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Aufteilung eines Gebaeudes in Wohnungs- oder Teileigentum mit Teilungserklaerung, Gemeinschaftsordnung, Plaenen, Bescheinigungen und Grundbuchumsetzung.

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
| `property.identity` | Grundstueck Identitaet | Notariatsfachkraft | land_register_review |
| `owner.identity` | Eigentuemer Identitaet | Notariat | identity_gate, drafting |
| `unit.structure` | Einheit Struktur | Mandantschaft | drafting, plans |
| `ownership.shares` | Eigentum Anteile | Mandantschaft | declaration |
| `plans.certificates` | Plaene Bescheinigungen | Mandantschaft | evidence_package, filing |
| `encumbrance.handling` | Belastung Behandlung | Notariat | legal_review, filing |

## Grenzen Fuer Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehoert in einen privaten Fork mit Rollen, Freigaben und geprueftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primaere Plugins:

- `noc-regulated-core`
- `noc-grundbuch-portal`
- `noc-bnotk-xnp`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.gbo.19_29_46`
- `src.weg.8`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case teilungserklaerung-weg
python scripts/notary_kg.py --repo-root . editor-view teilungserklaerung-weg
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
