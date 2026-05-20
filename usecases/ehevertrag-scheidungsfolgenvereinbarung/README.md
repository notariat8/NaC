# Ehevertrag / Scheidungsfolgenvereinbarung

Status: offen
Reifegrad: Top-10-Usecase, P1
KG-Knoten: `case.ehevertrag_scheidungsfolgen`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Ehevertrag oder Scheidungsfolgenvereinbarung mit Gueterstand, Ausgleich, Versorgungsausgleich, Unterhalt, Vermögenszuordnung und Fairness-Prüfung.

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
| `spouses.identity` | Ehegatten Identität | Notariatsfachkraft | identity_gate, appointment |
| `marriage.context` | Ehe Kontext | Notariat | legal_review |
| `property.regime` | Grundstück Regime | Notariat | drafting, fairness_review |
| `asset.disclosure` | Vermögen Offenlegung | spouses | fairness_review, drafting |
| `maintenance.rules` | Unterhalt Regeln | Notariat | fairness_review, drafting |
| `pension.equalization` | Versorgungsausgleich equalization | Notariat | legal_review, drafting |
| `child.family.flags` | Kind Familie Prüfflaggen | Notariat | fairness_review |
| `asset.transfer` | Vermögen Übertragung | Notariatsfachkraft | attachments, execution |

## Grenzen Für Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehört in einen privaten Fork mit Rollen, Freigaben und geprüftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primäre Plugins:

- `nac-regulated-core`
- `nac-idaas`
- `nac-grundbuch-portal`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.bgb.1410`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case ehevertrag-scheidungsfolgenvereinbarung
python scripts/notary_kg.py --repo-root . editor-view ehevertrag-scheidungsfolgenvereinbarung
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
