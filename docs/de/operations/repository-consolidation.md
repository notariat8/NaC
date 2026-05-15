# Repository-Konsolidierung nach NoC

Stand: 2026-05-14

## Zweck

Dieses Dokument trennt drei Zustaende, die in GitHub leicht verwechselt werden:

1. `kanonisiert`: Inhalt oder fachlicher Platz ist im NoC-Repo angelegt.
2. `gemerged`: der NoC-Zielstand ist in `main`.
3. `stillgelegt`: das alte Quellrepo ist archiviert, geloescht oder hat ein
   klares Redirect-README.

Ein Repo verschwindet in GitHub nicht dadurch, dass sein Inhalt in NoC
uebernommen wurde. Dafuer ist ein separater Stilllegungsschritt noetig.

## Aktueller Status

| Quellrepo | NoC-Ziel | Status in NoC | Quellrepo-Status | Naechste Aktion |
| --- | --- | --- | --- | --- |
| `ofunk/NaC` | Zielrepo | Zielsystem | offen | PR #6 mergen. |
| `ofunk/Online-GmbH-Gruendung` | `usecases/online-gmbh-gruendung/` | kanonisiert in PR #6 | altes Repo sichtbar, leer | Nach Merge Redirect-README setzen oder archivieren. |
| `ofunk/AO52aaS` | `usecases/ao52aas-gemeinnuetzigkeit/` | migriert in PR #6 | altes Repo sichtbar | Nach Merge Redirect-README setzen oder archivieren. |
| `ofunk/Steuer-aaS` | `usecases/steuer-aas/` | kanonisiert in PR #6 | altes Repo sichtbar, leer | Nach Merge Redirect-README setzen oder archivieren. |
| `ofunk/IDaaS` | `plugins/noc-idaas/` | migriert in PR #6 | altes Repo sichtbar | Nach Merge Redirect-README setzen oder archivieren. |
| `ofunk/NaaS` | `usecases/` und `workflows/` | noch nicht migriert | altes Repo sichtbar | Zerlegen statt 1:1 verschieben: Usecases, Workflow-Kontrakte und ggf. Backlog getrennt uebernehmen. |
| `ofunk/oci-landing-zone` | `plugins/noc-oci-evidence/` und Cloud-/Evidence-Doku | teilweise fachlich abgedeckt | altes Repo sichtbar | Pruefen, ob Runbooks/Infra-Vertraege in NoC fehlen; dann migrieren oder als externe Infrastrukturquelle belassen. |
| `ofunk/PaaS` | ggf. `workflows/` oder Editor-/Workspace-Doku | nicht migriert | altes Repo sichtbar | Pruefen, ob Inhalte zu NoC gehoeren oder als separates VS-Code-Orchestrator-Repo bleiben. |
| `ofunk/1gem8` | ggf. `usecases/ao52aas-gemeinnuetzigkeit/` oder Startup-Doku | nicht migriert | altes Repo sichtbar | Pruefen, ob Restinhalte die AO52-/Gemeinnuetzigkeits-Usecase-Sicht ergaenzen. |
| `ofunk/machine-setup` | keine fachliche NoC-Domaene | extern | altes Repo sichtbar | Nicht in NoC verschieben, ausser es wird bewusst als Tooling-Runbook uebernommen. |

## Stilllegungsregel

Nach erfolgreichem Merge von PR #6:

1. Quellrepo mit NoC-Zielpfad abgleichen.
2. Falls vollstaendig uebernommen: Redirect-README im Quellrepo setzen.
3. Falls kein weiterer Stand benoetigt wird: Repo archivieren oder loeschen.
4. Falls nur teilweise uebernommen: offenen Rest in diesem Dokument und im
   Gantt sichtbar halten.

## Berechtigungsrealitaet

Die GitHub-App zeigt fuer mehrere `ofunk/*`-Repos Schreibrechte, aber keine
Adminrechte. Ohne Adminrechte kann ich Repos nicht verlaesslich archivieren oder
loeschen. Ich kann aber, wenn gewuenscht, Redirect-READMEs per Git-Push setzen.

## Redirect-README-Muster

```markdown
# Moved to NoC

This repository has been consolidated into `ofunk/NaC`.

Canonical location:
`<target-path>`

Do not create new work here. Open issues and changes in `ofunk/NaC`.
```
