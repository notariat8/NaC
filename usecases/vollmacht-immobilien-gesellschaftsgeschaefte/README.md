# Vollmacht fuer Immobilien- oder Gesellschaftsgeschaefte

Status: offen  
Reifegrad: Naechste-10-Usecase, P0  
KG-Knoten: `case.vollmacht_immobilien_gesellschaft`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Notarielle oder oeffentlich beglaubigte Vollmachten fuer Immobilienvertraege, Registeranmeldungen, Gesellschafterversammlungen oder Anteilsuebertragungen mit Umfang, Form und Nachweisen.

Diese Datei ist die fachliche Vorderseite fuer Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht fuer offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 6 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 4 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Pruefgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `principal.identity` | Vollmachtgeber Identitaet | Notariat | identity_gate |
| `agent.identity` | Bevollmaechtigter Identitaet | Vollmachtgebende Person | drafting |
| `transaction.scope` | Geschaeft Umfang | Notariat | legal_review, drafting |
| `form.requirement` | Form Anforderung | Notariat | form_review |
| `limitations.expiry` | Beschraenkungen Ablauf | Notariat | drafting |
| `delivery.evidence` | Zustellung Nachweis | Notariatsfachkraft | closing |

## Grenzen Fuer Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehoert in einen privaten Fork mit Rollen, Freigaben und geprueftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primaere Plugins:

- `noc-regulated-core`
- `noc-idaas`
- `noc-grundbuch-portal`
- `noc-bnotk-xnp`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.bgb.167_129`
- `src.bgb.311b`
- `src.hgb.12`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case vollmacht-immobilien-gesellschaftsgeschaefte
python scripts/notary_kg.py --repo-root . editor-view vollmacht-immobilien-gesellschaftsgeschaefte
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
