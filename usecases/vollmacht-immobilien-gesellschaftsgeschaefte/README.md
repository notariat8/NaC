# Vollmacht für Immobilien- oder Gesellschaftsgeschäfte

Status: offen
Reifegrad: Nächste-10-Usecase, P0
KG-Knoten: `case.vollmacht_immobilien_gesellschaft`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Notarielle oder öffentlich beglaubigte Vollmachten für Immobilienverträge, Registeranmeldungen, Gesellschafterversammlungen oder Anteilsübertragungen mit Umfang, Form und Nachweisen.

Diese Datei ist die fachliche Vorderseite für Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht für offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 6 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 4 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Prüfgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `principal.identity` | Vollmachtgeber Identität | Notariat | identity_gate |
| `agent.identity` | Bevollmaechtigter Identität | Vollmachtgebende Person | drafting |
| `transaction.scope` | Geschäft Umfang | Notariat | legal_review, drafting |
| `form.requirement` | Form Anforderung | Notariat | form_review |
| `limitations.expiry` | Beschraenkungen Ablauf | Notariat | drafting |
| `delivery.evidence` | Zustellung Nachweis | Notariatsfachkraft | closing |

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
- `nac-bnotk-xnp`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.bgb.167_129`
- `src.bgb.311b`
- `src.hgb.12`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case vollmacht-immobilien-gesellschaftsgeschaefte
python scripts/notary_kg.py --repo-root . editor-view vollmacht-immobilien-gesellschaftsgeschaefte
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
