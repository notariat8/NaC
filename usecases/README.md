# Notarielle Usecases

Dieser Ordner enthält konkrete notarielle Vorgangsarten nach deutschem Recht.
Deutsch ist für diese Usecases die führende und rechtlich bindende Sprache.
Englische Fassungen können Orientierung oder Übersetzung sein, ersetzen aber
nicht die deutsche fachliche Quelle.

Usecases sind getrennt von installierbaren Plugins und wiederverwendbarer
Workflow-Ausführungslogik. Der statische Knowledge Graph ist usecase-lokal und
liegt im jeweils passenden Usecase-Ordner.

Jeder Usecase-Ordner hat jetzt zwei Leseebenen:

- `README.md` als kurze fachliche Vorderseite für Menschen.
- `knowledge-graph.md` und `knowledge-graph.graph.json` als Review- und
  Maschinenstand für offene Knoten, Dokumente, Entscheidungen und Gates.

Für Nicht-Technik-Leser helfen zusätzlich
[docs/de/reifegrad.md](../docs/de/reifegrad.md),
[docs/de/glossar.md](../docs/de/glossar.md) und
[docs/de/beispiel-immobilienkaufvertrag.md](../docs/de/beispiel-immobilienkaufvertrag.md).

## Abgrenzung

- [plugins/](../plugins) stellt installierbare Begleitfähigkeiten bereit.
- [workflows/](../workflows) stellt wiederverwendbare Skills und deterministische
  Python-Workflowlogik bereit.
- [usecases/](.) beschreibt konkrete notarielle Vorgangsarten und deren
  Plugin-/Workflow-Bindung.
- Jeder Ordner `usecases/<slug>/` führt seine eigene statische KG/DB:
  `knowledge-graph.graph.json` für maschinenlesbaren Zustand und
  `knowledge-graph.md` für die menschliche Review-Sicht.

## Kanonischer Top-10-Katalog

| Usecase | Ordner | Status | Primäre Plugin-Abhängigkeiten |
| --- | --- | --- | --- |
| Immobilienkaufvertrag | [immobilienkaufvertrag/](immobilienkaufvertrag) | KG-Basis | `nac-regulated-core`, `nac-grundbuch-portal`, `nac-bnotk-xnp` |
| Grundschuld / Hypothekenbestellung | [grundschuld-hypothekenbestellung/](grundschuld-hypothekenbestellung) | KG-Basis | `nac-regulated-core`, `nac-grundbuch-portal`, `nac-bnotk-xnp` |
| GmbH-/UG-Gründung | [online-gmbh-gruendung/](online-gmbh-gruendung) | KG-Basis, aktive Aufnahme | `nac-regulated-core`, `nac-cyberjack-rfid`, `nac-bnotk-xnp`, `nac-handelsregister`, `nac-idaas` |
| Handelsregisteranmeldung | [handelsregisteranmeldung/](handelsregisteranmeldung) | KG-Basis | `nac-regulated-core`, `nac-bnotk-xnp`, `nac-handelsregister`, `nac-cyberjack-rfid` |
| Beglaubigung von Unterschriften | [unterschriftsbeglaubigung/](unterschriftsbeglaubigung) | KG-Basis | `nac-regulated-core`, `nac-idaas`, `nac-bnotk-xnp` |
| Testament / Erbvertrag | [testament-erbvertrag/](testament-erbvertrag) | KG-Basis | `nac-regulated-core` |
| Erbscheinsantrag / Nachlassangelegenheiten | [erbscheinsantrag-nachlass/](erbscheinsantrag-nachlass) | KG-Basis | `nac-regulated-core` |
| Vorsorgevollmacht und Patientenverfügung | [vorsorgevollmacht-patientenverfuegung/](vorsorgevollmacht-patientenverfuegung) | KG-Basis | `nac-regulated-core`, `nac-idaas` |
| Schenkungsvertrag / Übertragungsvertrag | [schenkungsvertrag-uebertragungsvertrag/](schenkungsvertrag-uebertragungsvertrag) | KG-Basis | `nac-regulated-core`, `nac-grundbuch-portal` |
| Ehevertrag / Scheidungsfolgenvereinbarung | [ehevertrag-scheidungsfolgenvereinbarung/](ehevertrag-scheidungsfolgenvereinbarung) | KG-Basis | `nac-regulated-core`, `nac-idaas`, `nac-grundbuch-portal` |

## Kanonischer Next-10-Katalog

| Usecase | Ordner | Status | Primäre Plugin-Abhängigkeiten |
| --- | --- | --- | --- |
| Löschungsbewilligung / Grundbuchlöschung | [loeschungsbewilligung-grundbuchloeschung/](loeschungsbewilligung-grundbuchloeschung) | KG-Basis | `nac-regulated-core`, `nac-grundbuch-portal`, `nac-bnotk-xnp` |
| Teilungserklärung nach WEG | [teilungserklaerung-weg/](teilungserklaerung-weg) | KG-Basis | `nac-regulated-core`, `nac-grundbuch-portal`, `nac-bnotk-xnp` |
| Bauträgervertrag | [bautraegervertrag/](bautraegervertrag) | KG-Basis | `nac-regulated-core`, `nac-grundbuch-portal`, `nac-bnotk-xnp`, `nac-idaas` |
| Gesellschafterbeschluss bei GmbH/UG | [gesellschafterbeschluss-gmbh-ug/](gesellschafterbeschluss-gmbh-ug) | KG-Basis | `nac-regulated-core`, `nac-bnotk-xnp`, `nac-handelsregister`, `nac-cyberjack-rfid` |
| Geschäftsanteilsübertragung GmbH | [geschaeftsanteilsuebertragung-gmbh/](geschaeftsanteilsuebertragung-gmbh) | KG-Basis | `nac-regulated-core`, `nac-bnotk-xnp`, `nac-handelsregister`, `nac-idaas` |
| Vereinsregisteranmeldung | [vereinsregisteranmeldung/](vereinsregisteranmeldung) | KG-Basis | `nac-regulated-core`, `nac-bnotk-xnp`, `nac-idaas` |
| Erbausschlagung | [erbausschlagung/](erbausschlagung) | KG-Basis | `nac-regulated-core`, `nac-idaas` |
| Pflichtteilsverzicht / Erbverzicht | [pflichtteilsverzicht-erbverzicht/](pflichtteilsverzicht-erbverzicht) | KG-Basis | `nac-regulated-core`, `nac-idaas` |
| Adoption / familienrechtliche Erklärungen | [adoption-familienrechtliche-erklaerungen/](adoption-familienrechtliche-erklaerungen) | KG-Basis | `nac-regulated-core`, `nac-idaas` |
| Vollmacht für Immobilien- oder Gesellschaftsgeschäfte | [vollmacht-immobilien-gesellschaftsgeschaefte/](vollmacht-immobilien-gesellschaftsgeschaefte) | KG-Basis | `nac-regulated-core`, `nac-idaas`, `nac-grundbuch-portal`, `nac-bnotk-xnp` |

## Knowledge-Graph-Bindung

Der statische KG wird im jeweiligen Usecase-Ordner gepflegt:

- [immobilienkaufvertrag/knowledge-graph.graph.json](immobilienkaufvertrag/knowledge-graph.graph.json)
- [online-gmbh-gruendung/knowledge-graph.graph.json](online-gmbh-gruendung/knowledge-graph.graph.json)
- [bautraegervertrag/knowledge-graph.graph.json](bautraegervertrag/knowledge-graph.graph.json)

Jeder Usecase-Ordner muss genau einen lokalen KG-Graph und eine Markdown-
Review-Sicht enthalten. Workflows lesen diesen lokalen KG als Status offener
Fragen und schreiben Änderungen nur über reviewte Git-Änderungen zurück.
Echte Mandatswerte bleiben außerhalb des Repository.

Fachpersonal bearbeitet diese Graphen nicht direkt als JSON. Die sichere
Bearbeitungsschicht ist der KG-Editor-Workstream in
[docs/de/kg-editor-workstream.md](../docs/de/kg-editor-workstream.md). Die
ausführbare Editor-View kommt aus
[src/notary_kg/editor.py](../src/notary_kg/editor.py) und sperrt `value`-Felder
konsequent.

## Weitere Backlog-Kandidaten

Die folgenden Kandidaten haben noch keinen kanonischen Usecase-Ordner. Sobald
ein Kandidat als Usecase angelegt wird, braucht er sofort eigene Dateien
`knowledge-graph.graph.json` und `knowledge-graph.md`:

- Genehmigungserklärungen
- Rangrücktritt/Rangänderung im Grundbuch
- Dienstbarkeiten
- Baulasten-bezogene Erklärungen
- Niessbrauchsbestellungen
- Wohnrechte
- Auseinandersetzungsverträge zwischen Erben
- Scheidungsimmobilien-Übertragungen

## Aufnahme-Regel

Externe GitHub-Repositories, die tatsächlich notarielle Usecases sind, werden
hier kanonisiert. Wenn ein externes Repository leer ist, werden nur der
kanonische Ordner und die Quellenreferenz angelegt; eine leere Historie wird
nicht importiert.

Siehe [github-repo-intake.md](github-repo-intake.md) für den letzten
GitHub-Scan.

## Legacy-Starter-Aliase

[grundstueckskaufvertrag/](grundstueckskaufvertrag) und
[testament/](testament) bleiben als aeltere Starterordner erhalten. Die
kanonischen Top-10-Einträge sind [immobilienkaufvertrag/](immobilienkaufvertrag)
und [testament-erbvertrag/](testament-erbvertrag).
