# Vorsorgevollmacht und Patientenverfuegung

Status: offen  
Reifegrad: Top-10-Usecase, P0  
KG-Knoten: `case.vorsorgevollmacht_patientenverfuegung`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Vorsorgevollmacht, Gesundheitsvollmacht und Patientenverfuegung mit Umfang, Bevollmaechtigten, Wirksamkeit, Register und Ausfertigungsmanagement.

Diese Datei ist die fachliche Vorderseite fuer Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht fuer offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 8 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 4 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Pruefgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `principal.identity` | Vollmachtgeber Identitaet | Notariat | identity_gate, capacity_review |
| `agent.identities` | Bevollmaechtigter Identitaeten | Vollmachtgebende Person | drafting |
| `authority.financial` | Berechtigung Finanzen | Vollmachtgebende Person | drafting, legal_review |
| `authority.health` | Berechtigung Gesundheit | Vollmachtgebende Person | drafting, legal_review |
| `patient.directive` | Patientenverfuegung Verfuegung | Vollmachtgebende Person | drafting, appointment |
| `effectiveness.rules` | Wirksamkeit Regeln | Notariat | legal_review, closing |
| `self_dealing.release` | Befreiung von Selbstkontrahierung und Untervollmacht | Notariat | legal_review |
| `central_register` | Zentrales Vorsorgeregister | Notariatsfachkraft | closing |

## Grenzen Fuer Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehoert in einen privaten Fork mit Rollen, Freigaben und geprueftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primaere Plugins:

- `noc-regulated-core`
- `noc-idaas`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case vorsorgevollmacht-patientenverfuegung
python scripts/notary_kg.py --repo-root . editor-view vorsorgevollmacht-patientenverfuegung
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
