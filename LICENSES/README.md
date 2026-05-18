# Lizenzmodell

NaC ist maximal offen nutzbar und zugleich schützend für Urheber,
Weiterentwicklung und öffentliche Betreiberpflichten.

## Kurzfassung

- Software, Skripte, Plugins, Workflow-Runtime, Schemas, Verträge,
  Validatoren und ausführbare Beispiele stehen unter `AGPL-3.0-or-later`.
- Dokumentation, Diagramme, Roadmap-Texte, Policies, fachliche Usecase-
  Beschreibungen und Knowledge-Graph-Reviewtexte stehen unter `CC-BY-4.0`,
  sofern eine Datei nichts Abweichendes sagt.
- Attribution ist gewünscht und erforderlich: "NaC: Notariat as Code by
  funktion8 / ofunk (https://github.com/ofunk/NaC)".
- Die Open-Source-Lizenzen gewähren keine Markenrechte. Details stehen in
  [TRADEMARK.md](../TRADEMARK.md).

## Warum Diese Trennung

`AGPL-3.0-or-later` schützt den ausführbaren Kern auch dann, wenn er als
Netzwerkdienst betrieben wird. Wer den Code verändert und Dritten über ein
Netzwerk zugänglich macht, muss die korrespondierenden Quellen dieser
veränderten Version zugänglich machen.

`CC-BY-4.0` macht fachliche Texte, Diagramme und Usecase-Beschreibungen breit
zitier- und weiterverwendbar. Die zentrale Pflicht ist Namensnennung.

## Zuordnung

| Bereich | Lizenz |
| --- | --- |
| [src/](../src), [scripts/](../scripts), [schemas/](../schemas), [bpmn/](../bpmn), [processes/](../processes) | `AGPL-3.0-or-later` |
| [plugins/](../plugins), inklusive Plugin-Manifeste, Verträge, lokale Prüfroutinen und Assets | `AGPL-3.0-or-later` |
| [workflows/](../workflows), inklusive ausführbarer Workflow-Verträge und Runtime-Anteile | `AGPL-3.0-or-later` |
| [docs/](../docs), [prompts/](../prompts), [roadmap/](../roadmap), [policies/](../policies) | `CC-BY-4.0` |
| [usecases/](../usecases), inklusive fachlicher Beschreibungen und statischer Knowledge Graphs | `CC-BY-4.0` |

## Lizenztexte

- [AGPL-3.0-or-later](AGPL-3.0-or-later.txt)
- [CC-BY-4.0](CC-BY-4.0.txt)

## Attribution

Bitte in Forks, Veröffentlichungen, Präsentationen, Produktunterlagen und
öffentlichen Deployments sichtbar nennen:

> Based on NaC: Notariat as Code by funktion8 / ofunk (https://github.com/ofunk/NaC).

Maschinenlesbare Zitierdaten stehen in [CITATION.cff](../CITATION.cff). Die
Herausgeber- und Urheberhinweise stehen in [AUTHORS.md](../AUTHORS.md) und
[NOTICE](../NOTICE).
