# Beglaubigung von Unterschriften

Status: offen  
Reifegrad: Top-10-Usecase, P1  
KG-Knoten: `case.unterschriftsbeglaubigung`  
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Oeffentliche Beglaubigung von Unterschriften oder Handzeichen fuer Registeranmeldungen, Vollmachten, Zustimmungen, Loeschungsbewilligungen oder Vertretungserklaerungen.

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
| `signer.identity` | Unterzeichner Identitaet | Notariatsfachkraft | identity_gate, certificate |
| `document.purpose` | Dokument Zweck | Notariatsfachkraft | certificate, routing |
| `signature.mode` | Unterschrift Modus | Notariat | certificate |
| `language.understanding` | Sprache Verstaendnis | Notariat | legal_review, appointment |
| `representation.context` | Representation Kontext | Notariatsfachkraft | authority_review |
| `copies.routing` | Ausfertigungen Weiterleitung | Notariatsfachkraft | closing |
| `special.form` | Sonderfall Form | Notariat | legal_review, routing |
| `fee.metadata` | Gebuehr Metadaten | Notariatsfachkraft | closing |

## Grenzen Fuer Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehoert in einen privaten Fork mit Rollen, Freigaben und geprueftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primaere Plugins:

- `noc-regulated-core`
- `noc-idaas`
- `noc-bnotk-xnp`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.hgb.12`

## Wie Man Diesen Usecase Prueft

```bash
python scripts/notary_kg.py --repo-root . case unterschriftsbeglaubigung
python scripts/notary_kg.py --repo-root . editor-view unterschriftsbeglaubigung
python scripts/validate_knowledge_graph.py
```

## Naechster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
