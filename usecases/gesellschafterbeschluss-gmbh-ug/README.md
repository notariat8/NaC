# Gesellschafterbeschluss bei GmbH/UG

Status: offen
Reifegrad: Nächste-10-Usecase, P0
KG-Knoten: `case.gesellschafterbeschluss_gmbh_ug`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Gesellschafterbeschlüsse bei GmbH/UG zu Satzungsänderungen, Kapitalmaßnahmen, Geschäftsführerbestellung, Anteilszustimmungen oder sonstigen Gesellschaftsentscheidungen.

Diese Datei ist die fachliche Vorderseite für Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht für offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 6 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 5 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Prüfgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `company.identity` | Gesellschaft Identität | Notariatsfachkraft | register_review |
| `resolution.type` | Beschluss Art | Notariat | drafting, legal_review |
| `shareholders.present` | Gesellschafter anwesend | Notariatsfachkraft | quorum_review, identity_gate |
| `majority.requirement` | Mehrheit Anforderung | Notariat | legal_review |
| `articles.wording` | Satzung Wortlaut | Notariat | drafting, register_application |
| `register.filing` | Register Einreichung | Notariatsfachkraft | submission |

## Grenzen Für Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehört in einen privaten Fork mit Rollen, Freigaben und geprüftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primäre Plugins:

- `nac-regulated-core`
- `nac-bnotk-xnp`
- `nac-handelsregister`
- `nac-cyberjack-rfid`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.gmbhg.53`
- `src.hgb.12`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case gesellschafterbeschluss-gmbh-ug
python scripts/notary_kg.py --repo-root . editor-view gesellschafterbeschluss-gmbh-ug
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
