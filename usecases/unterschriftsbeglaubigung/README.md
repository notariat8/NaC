# Beglaubigung von Unterschriften

Status: offen
Reifegrad: Top-10-Usecase, P1
KG-Knoten: `case.unterschriftsbeglaubigung`
KG: [knowledge-graph.graph.json](knowledge-graph.graph.json) / [knowledge-graph.md](knowledge-graph.md)

## Worum Es Geht

Öffentliche Beglaubigung von Unterschriften oder Handzeichen für Registeranmeldungen, Vollmachten, Zustimmungen, Löschungsbewilligungen oder Vertretungserklärungen.

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
| `signer.identity` | Unterzeichner Identität | Notariatsfachkraft | identity_gate, certificate |
| `document.purpose` | Dokument Zweck | Notariatsfachkraft | certificate, routing |
| `signature.mode` | Unterschrift Modus | Notariat | certificate |
| `language.understanding` | Sprache Verständnis | Notariat | legal_review, appointment |
| `representation.context` | Representation Kontext | Notariatsfachkraft | authority_review |
| `copies.routing` | Ausfertigungen Weiterleitung | Notariatsfachkraft | closing |
| `special.form` | Sonderfall Form | Notariat | legal_review, routing |
| `fee.metadata` | Gebühr Metadaten | Notariatsfachkraft | closing |

## Grenzen Für Den Betrieb

- Keine echte Mandatsakte, keine echten personenbezogenen Daten und keine Secrets in Git.
- KI darf strukturieren und vorbereiten, aber keine finale notarielle Entscheidung ersetzen.
- Produktiver Betrieb gehört in einen privaten Fork mit Rollen, Freigaben und geprüftem Arbeitsplatz.
- Schreibende Portal-, Register- oder Fachsystemadapter brauchen gesonderte Freigabe.

## Plugin- Und Workflow-Bindung

Primäre Plugins:

- `nac-regulated-core`
- `nac-idaas`
- `nac-bnotk-xnp`

Workflow-Bezug:

- `workflows/contracts`
- `workflows/python`

Fachliche Anker im KG-Modell:

- `src.beurkg`
- `src.hgb.12`

## Wie Man Diesen Usecase Prüft

```bash
python scripts/notary_kg.py --repo-root . case unterschriftsbeglaubigung
python scripts/notary_kg.py --repo-root . editor-view unterschriftsbeglaubigung
python scripts/validate_knowledge_graph.py
```

## Nächster Lesepfad

- [docs/de/reifegrad.md](../../docs/de/reifegrad.md)
- [docs/de/glossar.md](../../docs/de/glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](../../docs/de/beispiel-immobilienkaufvertrag.md)
- [usecases/README.md](../README.md)
