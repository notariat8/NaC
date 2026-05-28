# Vorsorgevollmacht und Patientenverfügung

Status: offen
Reifegrad: Top-10-Usecase, P0
KG-Knoten: `case.vorsorgevollmacht_patientenverfuegung`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Vorsorgevollmacht, Gesundheitsvollmacht und Patientenverfügung mit Umfang, Bevollmaechtigten, Wirksamkeit, Register und Ausfertigungsmanagement.

Diese Datei ist die fachliche Vorderseite für Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht für offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 9 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 5 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 3 | [knowledge-graph.md](knowledge-graph.md) |
| Prüfgates | 3 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `principal.identity` | Vollmachtgeber Identität | Notariat | identity_gate, capacity_review |
| `agent.identities` | Bevollmaechtigter Identitäten | Vollmachtgebende Person | drafting |
| `authority.financial` | Berechtigung Finanzen | Vollmachtgebende Person | drafting, legal_review |
| `authority.health` | Berechtigung Gesundheit | Vollmachtgebende Person | drafting, legal_review |
| `patient.directive` | Patientenverfügung Verfügung | Vollmachtgebende Person | drafting, appointment |
| `effectiveness.rules` | Wirksamkeit Regeln | Notariat | legal_review, closing |
| `self_dealing.release` | Befreiung von Selbstkontrahierung und Untervollmacht | Notariat | legal_review |
| `central_register` | Zentrales Vorsorgeregister | Notariatsfachkraft | closing |
| `cost.business_value` | Geschäftswert für GNotKG-Kostenprüfung | Notariat | gnotkg_cost_review, cost_note |

## Grenzen Für Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehört in einen privaten Fork mit Rollen, Freigaben und geprüftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primäre Plugins:

- `nac-regulated-core`
- `nac-idaas`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case vorsorgevollmacht-patientenverfuegung
python scripts/notary_kg.py --repo-root . editor-view vorsorgevollmacht-patientenverfuegung
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
