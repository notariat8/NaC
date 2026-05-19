# NaC-QMS Für ISO 9001

Dieser Ordner ist die QMS-Schicht für Notariate, die NaC-Prozesse als Grundlage
für ein Qualitätsmanagementsystem nutzen wollen.

Ziel ist nicht, eine Zertifizierung zu behaupten. Ziel ist, die NaC-Artefakte so
zu ordnen, dass ein Notariat daraus ein internes QMS, interne Audits und später
ein externes ISO-9001-Audit vorbereiten kann.

## Abgrenzung

- ISO 9000 liefert Begriffe und Grundlagen.
- ISO 9001 ist der typische Anforderungskatalog für ein auditierbares QMS.
- NaC liefert Prozess-, Nachweis-, Rollen- und Datenartefakte.
- Das Notariat bleibt verantwortlich für Freigaben, Qualitätspolitik,
  Managementbewertung und die tatsächliche Anwendung im Büro.

## QMS-Artefakte

| Datei | Zweck |
| --- | --- |
| [quality-policy.md](quality-policy.md) | Qualitätspolitik als Notariats-Entwurf. |
| [quality-objectives.json](quality-objectives.json) | Messbare Qualitätsziele und Kennzahlen. |
| [process-map.md](process-map.md) | Prozesslandkarte vom Auftrag bis Archiv. |
| [roles-raci.json](roles-raci.json) | Rollen und Verantwortlichkeiten. |
| [iso9001-mapping.md](iso9001-mapping.md) | Mapping von ISO-9001-Themen auf NaC-Nachweise. |
| [audit-program.md](audit-program.md) | Internes Auditprogramm und Prüffelder. |
| [nonconformities.schema.json](nonconformities.schema.json) | Schema für Abweichungen und Korrekturmaßnahmen. |
| [management-review.md](management-review.md) | Vorlage für Managementbewertung. |

## CLI

```bash
nac qms status
nac qms iso9001-map
nac qms audit-plan
nac qms evidence --repo ../demo8notariat
```

## NaC-Nachweisquellen

- Prozessmodelle: `bpmn/usecases/`
- Usecase-Wissensgraphen: `usecases/*/knowledge-graph.graph.json`
- Quality Gate: `nac doctor --profile strict`
- Akten- und Dokumentmodell: getrenntes Datenrepo, zum Beispiel
  `../demo8notariat`
- Reviews und Freigaben: Git, Pull Requests, Merge-Regeln
- Änderungen am QMS: versionierte Änderungen in diesem Ordner
