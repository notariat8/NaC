# Immobilienkaufvertrag

Status: offen
Reifegrad: Top-10-Usecase, P0
KG-Knoten: `case.immobilienkaufvertrag`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Kauf oder Verkauf von Grundstück, Wohnungseigentum, Haus oder Teileigentum mit Grundbuch, Kaufpreisfaelligkeit, Finanzierung und Vollzugsgates.

Diese Datei ist die fachliche Vorderseite für Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht für offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 8 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 5 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Prüfgates | 3 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `property.identity` | Grundstück Identität | Notariatsfachkraft | land_register_review, drafting, execution |
| `seller.identity` | Verkäufer Identität | Notariatsfachkraft | identity_gate, drafting, appointment |
| `buyer.identity` | Käufer Identität | Notariatsfachkraft | identity_gate, drafting, tax_notifications |
| `purchase.price` | Kaufpreis und Faelligkeitsmodell | Notariat | drafting, maturity_tracking, execution |
| `encumbrances.current` | Belastungen aktueller Stand | Notariatsfachkraft | land_register_review, bank_coordination, drafting |
| `financing.required` | Finanzierung erforderlich | Notariatsfachkraft | bank_coordination, appointment_planning |
| `possession.transfer` | Besitz Übertragung | Notariat | drafting, closing |
| `public.approvals` | Öffentlich Genehmigungen | Notariatsfachkraft | execution, land_register_filing |

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
- `src.bgb.311b`
- `src.gbo`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case immobilienkaufvertrag
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
