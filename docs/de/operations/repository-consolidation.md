# Repository-Konsolidierung nach NaC

Stand: 2026-05-19

## Zweck

Dieses Dokument trennt drei Zustände, die in GitHub leicht verwechselt werden:

1. `kanonisiert`: Inhalt oder fachlicher Platz ist im NaC-Repo angelegt.
2. `gemerged`: der NaC-Zielstand ist in `main`.
3. `stillgelegt`: das alte Quellrepo ist archiviert, gelöscht oder hat ein
   klares Redirect-README.

Ein Repo verschwindet in GitHub nicht dadurch, dass sein Inhalt in NaC
übernommen wurde. Dafür ist ein separater Stilllegungsschritt nötig.

## Aktueller Status

| Quellrepo | NaC-Ziel | Status in NaC | Quellrepo-Status | Nächste Aktion |
| --- | --- | --- | --- | --- |
| `ofunk/NaC` | Zielrepo | Zielsystem | offen | PR #6 mergen. |
| `ofunk/Online-GmbH-Gruendung` | `usecases/online-gmbh-gruendung/` | kanonisiert in PR #6 | altes Repo sichtbar, leer | Nach Merge Redirect-README setzen oder archivieren. |
| `ofunk/Steuer-aaS` | keine NaC-Usecase-Zielstruktur | aus dem NaC-Usecase-Katalog entfernt | altes Repo sichtbar, leer | Extern belassen oder später als Plugin-/Workflow-Idee neu bewerten. |
| `ofunk/IDaaS` | `plugins/nac-idaas/` | migriert in PR #6 | altes Repo sichtbar | Nach Merge Redirect-README setzen oder archivieren. |
| `ofunk/NaaS` | `usecases/` und `workflows/` | noch nicht migriert | altes Repo sichtbar | Zerlegen statt 1:1 verschieben: Usecases, Workflow-Kontrakte und ggf. Backlog getrennt übernehmen. |
| `ofunk/oci-landing-zone` | `plugins/nac-oci-evidence/` und Cloud-/Evidence-Doku | teilweise fachlich abgedeckt | altes Repo sichtbar | Prüfen, ob Runbooks/Infra-Verträge in NaC fehlen; dann migrieren oder als externe Infrastrukturquelle belassen. |
| `ofunk/PaaS` | ggf. `workflows/` oder Editor-/Workspace-Doku | nicht migriert | altes Repo sichtbar | Prüfen, ob Inhalte zu NaC gehören oder als separates VS-Code-Orchestrator-Repo bleiben. |
| `ofunk/1gem8` | ggf. Startup-Doku | nicht migriert | altes Repo sichtbar | Prüfen, ob Inhalte zu NaC gehören oder extern bleiben. |
| `ofunk/machine-setup` | keine fachliche NaC-Domäne | extern | altes Repo sichtbar | Nicht in NaC verschieben, außer es wird bewusst als Tooling-Runbook übernommen. |

## Stilllegungsregel

Nach erfolgreichem Merge von PR #6:

1. Quellrepo mit NaC-Zielpfad abgleichen.
2. Falls vollständig übernommen: Redirect-README im Quellrepo setzen.
3. Falls kein weiterer Stand benötigt wird: Repo archivieren oder löschen.
4. Falls nur teilweise übernommen: offenen Rest in diesem Dokument und im
   Gantt sichtbar halten.

## Berechtigungsrealitaet

Die GitHub-App zeigt für mehrere `ofunk/*`-Repos Schreibrechte, aber keine
Adminrechte. Ohne Adminrechte kann ich Repos nicht verlaesslich archivieren oder
löschen. Ich kann aber, wenn gewünscht, Redirect-READMEs per Git-Push setzen.

## Redirect-README-Muster

```markdown
# Moved to NaC

This repository has been consolidated into `ofunk/NaC`.

Canonical location:
`<target-path>`

Do not create new work here. Open issues and changes in `ofunk/NaC`.
```
