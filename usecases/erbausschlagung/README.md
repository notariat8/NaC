# Erbausschlagung

Status: offen  
Reifegrad: Naechste-10-Usecase, P0  
KG-Knoten: `case.erbausschlagung`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Erbausschlagungserklaerung gegenueber dem Nachlassgericht mit Frist, Identitaet, Vertretung, Minderjaehrigen- oder Betreuungsbezug und Zustellnachweis.

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
| `decedent.identity` | Erblasser Identitaet | Antragstellende Person | court_route |
| `renouncer.identity` | Ausschlagende Person Identitaet | Notariat | identity_gate, declaration |
| `deadline.status` | Frist Status | Notariat | deadline_review |
| `heirship.basis` | Erbenstellung Grundlage | Antragstellende Person | legal_review |
| `representation.minors` | Representation Minderjaehrige | Notariat | approval_review |
| `delivery.route` | Zustellung Route | Notariatsfachkraft | submission |

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
- `src.bgb.1945`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case erbausschlagung
python scripts/notary_kg.py --repo-root . editor-view erbausschlagung
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
