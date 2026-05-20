# Handelsregisteranmeldung

Status: offen
Reifegrad: Top-10-Usecase, P0
KG-Knoten: `case.handelsregisteranmeldung`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Registeranmeldung für Änderungen wie Geschäftsführerwechsel, Sitzverlegung, Kapitalmaßnahmen, Firma, Unternehmensgegenstand oder Prokura.

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
| `entity.identity` | Rechtsträger Identität | Notariatsfachkraft | register_review, application_draft |
| `event.type` | Vorgang Art | Notariat | application_draft, legal_review |
| `signers.identity` | Unterzeichner Identität | Notariatsfachkraft | identity_gate, public_certification |
| `corporate.resolution` | Gesellschaftsrecht Beschluss | Notariat | legal_review, attachments |
| `attachments.required` | Anlagen erforderlich | Notariatsfachkraft | filing_package |
| `effective.date` | Wirksamkeit Datum | Notariat | application_draft, legal_review |
| `xnp.route` | XNP Route | Notariatsfachkraft | technical_readiness, submission |
| `fees.costs` | Gebühren Kosten | Notariatsfachkraft | closing |

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
- `src.hgb.12`
- `src.gmbhg`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case handelsregisteranmeldung
python scripts/notary_kg.py --repo-root . editor-view handelsregisteranmeldung
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
