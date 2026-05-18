# GmbH-Gründung / UG-Gründung

Status: offen
Reifegrad: Top-10-Usecase, P0
KG-Knoten: `case.online_gmbh_gruendung`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Gründung einer GmbH oder UG mit Satzung, Gründern, Stammkapital, Geschäftsführung, Registeranmeldung sowie notarieller Identitäts- und Signatur-Readiness.

Diese Datei ist die fachliche Vorderseite für Menschen. Der genaue maschinenlesbare Stand liegt in [knowledge-graph.graph.json](knowledge-graph.graph.json); die Review-Sicht für offene Fragen, Dokumente, Entscheidungen und Gates liegt in [knowledge-graph.md](knowledge-graph.md).

## Was Heute Im Muster Enthalten Ist

| Bereich | Anzahl | Lesbarer Einstieg |
| --- | --- | --- |
| Offene Angaben | 8 | [knowledge-graph.md](knowledge-graph.md) |
| Dokument-/Nachweisreferenzen | 5 | [knowledge-graph.md](knowledge-graph.md) |
| Entscheidungen | 2 | [knowledge-graph.md](knowledge-graph.md) |
| Prüfgates | 2 | [knowledge-graph.md](knowledge-graph.md) |

## Offene Angaben

| Knoten | Bedeutung | Verantwortlich | Warum wichtig |
| --- | --- | --- | --- |
| `company.name` | Gesellschaft Name | Notariatsfachkraft | drafting, register_application |
| `company.seat` | Gesellschaft Sitz | Gründerkreis | articles, register_application |
| `company.object` | Gesellschaft Objekt | Gründerkreis | articles, legal_review |
| `founders.identity` | Gründer Identität | Notariatsfachkraft | identity_gate, shareholder_list |
| `capital.structure` | Kapital Struktur | Notariat | articles, register_application |
| `management.appointment` | Bestellung und Vertretung der Geschäftsführung | Notariatsfachkraft | register_application, identity_gate |
| `register.route` | Register Route | Notariatsfachkraft | technical_readiness, register_application |
| `beneficial.owner.flags` | Wirtschaftlich Berechtigte und GwG-Prüfflaggen | Notariat | aml_review, legal_review |

## Grenzen Für Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehört in einen privaten Fork mit Rollen, Freigaben und geprüftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primäre Plugins:

- `nac-regulated-core`
- `nac-cyberjack-rfid`
- `nac-bnotk-xnp`
- `nac-handelsregister`
- `nac-idaas`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.gmbhg`
- `src.hgb.12`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case online-gmbh-gruendung
python scripts/notary_kg.py --repo-root . editor-view online-gmbh-gruendung
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
