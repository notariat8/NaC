# Schenkungsvertrag / Uebertragungsvertrag

Status: offen  
Reifegrad: Top-10-Usecase, P0  
KG-Knoten: `case.schenkungsvertrag_uebertragung`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Schenkung oder Uebertragungsvertrag, haeufig innerhalb der Familie und oft grundstuecksbezogen, mit Vorbehaltsrechten, Rueckforderung, Pflegepflichten, Steuer- und Grundbuchvollzug.

Diese Datei ist die fachliche Vorderseite fuer Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht fuer offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 8 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 5 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Pruefgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `transferor.identity` | Uebertragender Identitaet | Notariatsfachkraft | identity_gate, drafting |
| `transferee.identity` | Erwerber Identitaet | Notariatsfachkraft | drafting, tax_notifications |
| `asset.identity` | Vermoegen Identitaet | Notariatsfachkraft | land_register_review, drafting |
| `reserved.rights` | Vorbehaltsrechte Rechte | Notariat | drafting, legal_review |
| `reversion.rights` | Rueckforderungsrechte Rechte | Notariat | drafting, land_register_filing |
| `consideration.obligations` | Gegenleistung Pflichten | Notariat | tax_review, drafting |
| `consents.approvals` | Zustimmungen Genehmigungen | Notariatsfachkraft | execution |
| `tax.family.flags` | Steuer Familie Pruefflaggen | Notariat | legal_review |

## Grenzen Fuer Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehoert in einen privaten Fork mit Rollen, Freigaben und geprueftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primaere Plugins:

- `noc-regulated-core`
- `noc-grundbuch-portal`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.bgb.518`
- `src.bgb.311b`
- `src.gbo`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case schenkungsvertrag-uebertragungsvertrag
python scripts/notary_kg.py --repo-root . editor-view schenkungsvertrag-uebertragungsvertrag
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
