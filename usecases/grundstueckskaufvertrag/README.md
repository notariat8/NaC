# Grundstueckskaufvertrag

Status: legacy_alias  
Reifegrad: Legacy-Starteralias, P2  
KG-Knoten: `case.grundstueckskaufvertrag`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Legacy-Starter-Alias fuer usecases/immobilienkaufvertrag; bleibt aus Kompatibilitaetsgruenden bestehen, waehrend neue Workflow-Arbeit den kanonischen Usecase nutzt.

Diese Datei ist die fachliche Vorderseite fuer Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht fuer offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 8 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 5 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Pruefgates | 3 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `property.identity` | Grundstueck Identitaet | Notariatsfachkraft | land_register_review, drafting, execution |
| `seller.identity` | Verkaeufer Identitaet | Notariatsfachkraft | identity_gate, drafting, appointment |
| `buyer.identity` | Kaeufer Identitaet | Notariatsfachkraft | identity_gate, drafting, tax_notifications |
| `purchase.price` | Kaufpreis und Faelligkeitsmodell | Notariat | drafting, maturity_tracking, execution |
| `encumbrances.current` | Belastungen aktueller Stand | Notariatsfachkraft | land_register_review, bank_coordination, drafting |
| `financing.required` | Finanzierung erforderlich | Notariatsfachkraft | bank_coordination, appointment_planning |
| `possession.transfer` | Besitz Uebertragung | Notariat | drafting, closing |
| `public.approvals` | Oeffentlich Genehmigungen | Notariatsfachkraft | execution, land_register_filing |

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
- `src.bgb.311b`
- `src.gbo`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case grundstueckskaufvertrag
python scripts/notary_kg.py --repo-root . editor-view grundstueckskaufvertrag
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
