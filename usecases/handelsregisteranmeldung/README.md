# Handelsregisteranmeldung

Status: offen  
Reifegrad: Top-10-Usecase, P0  
KG-Knoten: `case.handelsregisteranmeldung`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Registeranmeldung fuer Aenderungen wie Geschaeftsfuehrerwechsel, Sitzverlegung, Kapitalmassnahmen, Firma, Unternehmensgegenstand oder Prokura.

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
| `entity.identity` | Rechtstraeger Identitaet | Notariatsfachkraft | register_review, application_draft |
| `event.type` | Vorgang Art | Notariat | application_draft, legal_review |
| `signers.identity` | Unterzeichner Identitaet | Notariatsfachkraft | identity_gate, public_certification |
| `corporate.resolution` | Gesellschaftsrecht Beschluss | Notariat | legal_review, attachments |
| `attachments.required` | Anlagen erforderlich | Notariatsfachkraft | filing_package |
| `effective.date` | Wirksamkeit Datum | Notariat | application_draft, legal_review |
| `xnp.route` | XNP Route | Notariatsfachkraft | technical_readiness, submission |
| `fees.costs` | Gebuehren Kosten | Notariatsfachkraft | closing |

## Grenzen Fuer Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehoert in einen privaten Fork mit Rollen, Freigaben und geprueftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primaere Plugins:

- `noc-regulated-core`
- `noc-bnotk-xnp`
- `noc-handelsregister`
- `noc-cyberjack-rfid`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.hgb.12`
- `src.gmbhg`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case handelsregisteranmeldung
python scripts/notary_kg.py --repo-root . editor-view handelsregisteranmeldung
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
