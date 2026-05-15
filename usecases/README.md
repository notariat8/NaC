# Notarielle Usecases

Dieser Ordner enthaelt konkrete notarielle Vorgangsarten nach deutschem Recht.
Deutsch ist fuer diese Usecases die fuehrende und rechtlich bindende Sprache.
Englische Fassungen koennen Orientierung oder Uebersetzung sein, ersetzen aber
nicht die deutsche fachliche Quelle.

Usecases sind getrennt von installierbaren Plugins und wiederverwendbarer
Workflow-Ausfuehrungslogik. Der statische Knowledge Graph ist usecase-lokal und
liegt im jeweils passenden Usecase-Ordner.

## Abgrenzung

- [plugins/](../plugins) stellt installierbare Begleitfaehigkeiten bereit.
- [workflows/](../workflows) stellt wiederverwendbare Skills und deterministische
  Python-Workflowlogik bereit.
- [usecases/](.) beschreibt konkrete notarielle Vorgangsarten und deren
  Plugin-/Workflow-Bindung.
- Jeder Ordner `usecases/<slug>/` fuehrt seine eigene statische KG/DB:
  `knowledge-graph.graph.json` fuer maschinenlesbaren Zustand und
  `knowledge-graph.md` fuer die menschliche Review-Sicht.

## Kanonischer Top-10-Katalog

| Usecase | Ordner | Status | Primaere Plugin-Abhaengigkeiten |
| --- | --- | --- | --- |
| Immobilienkaufvertrag | [immobilienkaufvertrag/](immobilienkaufvertrag) | KG-Basis | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |
| Grundschuld / Hypothekenbestellung | [grundschuld-hypothekenbestellung/](grundschuld-hypothekenbestellung) | KG-Basis | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |
| GmbH-/UG-Gruendung | [online-gmbh-gruendung/](online-gmbh-gruendung) | KG-Basis, aktive Aufnahme | `noc-regulated-core`, `noc-cyberjack-rfid`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-idaas` |
| Handelsregisteranmeldung | [handelsregisteranmeldung/](handelsregisteranmeldung) | KG-Basis | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-cyberjack-rfid` |
| Beglaubigung von Unterschriften | [unterschriftsbeglaubigung/](unterschriftsbeglaubigung) | KG-Basis | `noc-regulated-core`, `noc-idaas`, `noc-bnotk-xnp` |
| Testament / Erbvertrag | [testament-erbvertrag/](testament-erbvertrag) | KG-Basis | `noc-regulated-core` |
| Erbscheinsantrag / Nachlassangelegenheiten | [erbscheinsantrag-nachlass/](erbscheinsantrag-nachlass) | KG-Basis | `noc-regulated-core` |
| Vorsorgevollmacht und Patientenverfuegung | [vorsorgevollmacht-patientenverfuegung/](vorsorgevollmacht-patientenverfuegung) | KG-Basis | `noc-regulated-core`, `noc-idaas` |
| Schenkungsvertrag / Uebertragungsvertrag | [schenkungsvertrag-uebertragungsvertrag/](schenkungsvertrag-uebertragungsvertrag) | KG-Basis | `noc-regulated-core`, `noc-grundbuch-portal` |
| Ehevertrag / Scheidungsfolgenvereinbarung | [ehevertrag-scheidungsfolgenvereinbarung/](ehevertrag-scheidungsfolgenvereinbarung) | KG-Basis | `noc-regulated-core`, `noc-idaas`, `noc-grundbuch-portal` |

## Zusaetzliche aktive Aufnahmequellen

| Usecase | Ordner | Status | Primaere Plugin-Abhaengigkeiten |
| --- | --- | --- | --- |
| AO52 gemeinnuetziges Softwareunternehmen | [ao52aas-gemeinnuetzigkeit/](ao52aas-gemeinnuetzigkeit) | Aktive Aufnahme | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-elster-eric` |
| Steuer-aaS Steuer-Readiness | [steuer-aas/](steuer-aas) | Aktive Aufnahme | `noc-regulated-core`, `noc-elster-eric` |

## Kanonischer Next-10-Katalog

| Usecase | Ordner | Status | Primaere Plugin-Abhaengigkeiten |
| --- | --- | --- | --- |
| Loeschungsbewilligung / Grundbuchloeschung | [loeschungsbewilligung-grundbuchloeschung/](loeschungsbewilligung-grundbuchloeschung) | KG-Basis | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |
| Teilungserklaerung nach WEG | [teilungserklaerung-weg/](teilungserklaerung-weg) | KG-Basis | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |
| Bautraegervertrag | [bautraegervertrag/](bautraegervertrag) | KG-Basis | `noc-regulated-core`, `noc-grundbuch-portal`, `noc-bnotk-xnp`, `noc-idaas` |
| Gesellschafterbeschluss bei GmbH/UG | [gesellschafterbeschluss-gmbh-ug/](gesellschafterbeschluss-gmbh-ug) | KG-Basis | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-cyberjack-rfid` |
| Geschaeftsanteilsuebertragung GmbH | [geschaeftsanteilsuebertragung-gmbh/](geschaeftsanteilsuebertragung-gmbh) | KG-Basis | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-handelsregister`, `noc-idaas` |
| Vereinsregisteranmeldung | [vereinsregisteranmeldung/](vereinsregisteranmeldung) | KG-Basis | `noc-regulated-core`, `noc-bnotk-xnp`, `noc-idaas` |
| Erbausschlagung | [erbausschlagung/](erbausschlagung) | KG-Basis | `noc-regulated-core`, `noc-idaas` |
| Pflichtteilsverzicht / Erbverzicht | [pflichtteilsverzicht-erbverzicht/](pflichtteilsverzicht-erbverzicht) | KG-Basis | `noc-regulated-core`, `noc-idaas` |
| Adoption / familienrechtliche Erklaerungen | [adoption-familienrechtliche-erklaerungen/](adoption-familienrechtliche-erklaerungen) | KG-Basis | `noc-regulated-core`, `noc-idaas` |
| Vollmacht fuer Immobilien- oder Gesellschaftsgeschaefte | [vollmacht-immobilien-gesellschaftsgeschaefte/](vollmacht-immobilien-gesellschaftsgeschaefte) | KG-Basis | `noc-regulated-core`, `noc-idaas`, `noc-grundbuch-portal`, `noc-bnotk-xnp` |

## Knowledge-Graph-Bindung

Der statische KG wird im jeweiligen Usecase-Ordner gepflegt:

- [immobilienkaufvertrag/knowledge-graph.graph.json](immobilienkaufvertrag/knowledge-graph.graph.json)
- [online-gmbh-gruendung/knowledge-graph.graph.json](online-gmbh-gruendung/knowledge-graph.graph.json)
- [bautraegervertrag/knowledge-graph.graph.json](bautraegervertrag/knowledge-graph.graph.json)
- [ao52aas-gemeinnuetzigkeit/knowledge-graph.graph.json](ao52aas-gemeinnuetzigkeit/knowledge-graph.graph.json)
- [steuer-aas/knowledge-graph.graph.json](steuer-aas/knowledge-graph.graph.json)

Jeder Usecase-Ordner muss genau einen lokalen KG-Graph und eine Markdown-
Review-Sicht enthalten. Workflows lesen diesen lokalen KG als Status offener
Fragen und schreiben Aenderungen nur ueber reviewte Git-Aenderungen zurueck.
Echte Mandatswerte bleiben ausserhalb des Repository.

## Weitere Backlog-Kandidaten

Die folgenden Kandidaten haben noch keinen kanonischen Usecase-Ordner. Sobald
ein Kandidat als Usecase angelegt wird, braucht er sofort eigene Dateien
`knowledge-graph.graph.json` und `knowledge-graph.md`:

- Genehmigungserklaerungen
- Rangruecktritt/Rangaenderung im Grundbuch
- Dienstbarkeiten
- Baulasten-bezogene Erklaerungen
- Niessbrauchsbestellungen
- Wohnrechte
- Auseinandersetzungsvertraege zwischen Erben
- Scheidungsimmobilien-Uebertragungen

## Aufnahme-Regel

Externe GitHub-Repositories, die tatsaechlich notarielle Usecases sind, werden
hier kanonisiert. Wenn ein externes Repository leer ist, werden nur der
kanonische Ordner und die Quellenreferenz angelegt; eine leere Historie wird
nicht importiert.

Siehe [github-repo-intake.md](github-repo-intake.md) fuer den letzten
GitHub-Scan.

## Legacy-Starter-Aliase

[grundstueckskaufvertrag/](grundstueckskaufvertrag) und
[testament/](testament) bleiben als aeltere Starterordner erhalten. Die
kanonischen Top-10-Eintraege sind [immobilienkaufvertrag/](immobilienkaufvertrag)
und [testament-erbvertrag/](testament-erbvertrag).
