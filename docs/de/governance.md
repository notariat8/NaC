# Governance mit Git und GitHub

## Repository-Regeln Und Auslieferungsmodi

Empfohlenes Zielbild für produktive Forks und sensible Prozessänderungen:

- Pushes direkt auf `main` verbieten
- Pull Requests verpflichtend machen
- Status-Checks aus `Validate NaC Runtime Fixtures` und `NaC Quality Gate` verlangen
- Review durch mindestens eine fachlich verantwortliche Person verlangen
- Signierte Tags für Abschlüsse wie `close/2026-03` verwenden

Im aktiven Referenzrepo kann der Owner direkte Lieferung auf `main`
ausdrücklich beauftragen. Dann ist ein Stand erst fertig, wenn der strikte
Quality Gate bestanden hat, `main` zu GitHub gepusht wurde, `HEAD` dem
GitHub-Zielstand entspricht und der Arbeitsbaum sauber ist. Dieser
Owner-Direct-Modus ersetzt nicht den geschützten PR-Modus für produktive Forks,
sensible Fachänderungen oder externe Mitwirkung.

Empfehlung für Unternehmens-Forks:

- technische Prozessreleases als `v*` markieren
- Upstream-Übernahme nur über dokumentierte Sync-PRs
- laufende Vorgänge auf Startversion belassen (Version-Binding)

## Agentische Änderungsdisziplin

Nichttriviale agentische Arbeit wird nicht direkt im Code ausgehandelt. Zuerst
werden Scope, Risiko, Akzeptanzkriterien und relevante Schichten im Plan
geklärt. Danach prüft ein Review den Plan, bevor umgesetzt wird.

Nach der Umsetzung prüft ein Code-Review mindestens:

- ob die Änderung dem Plan und den bestehenden Repo-Mustern folgt
- ob Daten-, Controller-/Logik- und View-Schicht konsistent bleiben
- ob Fehlerfälle, Tests und Sicherheitsaspekte angemessen abgedeckt sind
- ob keine unnötige neue Technik, Doppelstruktur oder Überkomplexität entsteht

Vor einem Merge, auch bei Owner-Freigabe, wird immer die vollständige PR-Diff
gegen den Zielbranch geprüft. Maßgeblich ist nicht nur der letzte Commit,
sondern `base...head` mit Datei- und Commitliste. Wenn ein PR-Branch von einem
anderen Feature-Branch statt vom Zielbranch abzweigt, wird der PR vor dem Merge
gestoppt, neu geschnitten oder ausdrücklich als kombinierter Scope dokumentiert.

Bei hartnäckigen oder unklaren Fehlern gilt: erst Diagnose, dann Fix. Ein
Agent darf in dieser Situation nicht weiterprobieren, bis die Ursache
benannt und der kleinste sinnvolle Fix-Pfad beschrieben ist.

Governance-Abweichung vom 15.06.2026: PR #139 wurde akzeptiert, obwohl der
Observability-Branch irrtümlich auf dem Q2D-Branch basierte und dadurch Q2D
zusammen mit dem Time-Ledger nach `main` brachte. PR #138 wurde als
superseded geschlossen. Die dauerhafte Korrektur ist die Pflicht zur
vollständigen PR-Diff-Prüfung vor jedem Merge.

## Environment-Mapping

- `nac-operations`: sensible manuelle Ausführung einzelner NaC-Prozessfixtures
- `month-close`: Monatsabschluss und periodische Aggregation
- optionale Notariats-Umgebungen für freigegebene Fachsystem- oder Registergates

## Fachliches Mapping

| Git/GitHub-Mechanismus | Fachliche Bedeutung |
| --- | --- |
| Branch | in Arbeit befindlicher Geschäftsvorgang |
| Pull Request | formaler Antrag mit Freigabebedarf |
| Review | fachliche Freigabe |
| Action Run | dokumentierte maschinelle Ausführung |
| Artifact | exportierter Nachweis oder Bericht |
| Tag | Abschlussstand |
| Release | publizierter, versionierter Nachweis |

## Praktische Regeln pro Domäne

### Notarielle Gründungsvorgänge

- Schritte können in einem Sammelvorgang oder als einzelne Prozessdateien geführt werden.
- Status `needs_review` sollte mit manuellem Review gekoppelt werden.

### Notarielle Kostenrechnung

- `draft -> approved` nur über Pull Request.
- `approved -> issued` nur in einer gesicherten Runtime oder nach dokumentierter Freigabe.
- notarielle Kostenprüfungen nur mit dokumentierter Qualifikation und Freigabe.

### Buchführung

- Buchungssätze müssen ausgeglichen sein.
- Idempotenzschlüssel und Belegreferenzen verhindern Doppelbuchungen.

### Notarielle Anzeigen Mit Steuerbezug

- `prepared -> approved` immer mit Vier-Augen-Prinzip.
- `submitted` sollte nur nach manueller Freigabe und möglicher externer Anzeige gesetzt werden.

## Rollenbasierte Entscheidungslogik

- Jede Rolle darf Tickets eröffnen.
- `low impact` ohne Compliance-Effekt kann self-resolve sein.
- `medium/high impact` oder rechtlicher Effekt braucht Review/Approval.
- Qualifikationspflichten haben Vorrang vor allgemeinen Rollenrechten.

Referenz: [policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)

## Weiterführende Betriebsstandards

- NemoClaw-Zielbetrieb und Agenten-Arbeitsteilung:
  [docs/de/architecture/nemoclaw-operating-model.md](architecture/nemoclaw-operating-model.md)
- NaC-On-Prem-Agent-Runtime auf `notoclaw01`:
  [docs/de/architecture/nac-onprem-agent-runtime.md](architecture/nac-onprem-agent-runtime.md)
- Fork-Modell und Verantwortungen:
  [docs/de/operations/fork-and-release-operating-model.md](operations/fork-and-release-operating-model.md)
- Sync-Zyklus und PR-Gates:
  [docs/de/operations/release-sync-playbook.md](operations/release-sync-playbook.md)
- Mischbetrieb und Audit-Nachweis:
  [docs/de/operations/parallelbetrieb-version-binding.md](operations/parallelbetrieb-version-binding.md)
- Repo-übergreifende Issue-Führung:
  [docs/de/issues/taxonomy.md](issues/taxonomy.md)
- Rollen, Zugriffe und zentrale Task-Übersicht:
  [docs/de/issues/operations.md](issues/operations.md)
- Revisionssicherheit über Event-Journal:
  [docs/de/eventstream/revisionssicherheit.md](eventstream/revisionssicherheit.md)
- Konkrete Plattformvorlagen:
  [docs/de/eventstream/implementation-templates.md](eventstream/implementation-templates.md)
- Azure Runbook:
  [docs/de/eventstream/runbook-azure.md](eventstream/runbook-azure.md)
- AWS Runbook:
  [docs/de/eventstream/runbook-aws.md](eventstream/runbook-aws.md)
- GCP Runbook:
  [docs/de/eventstream/runbook-gcp.md](eventstream/runbook-gcp.md)
- OCI Runbook:
  [docs/de/eventstream/runbook-oci.md](eventstream/runbook-oci.md)
- Tenant-Owner- und Service-Modell:
  [docs/de/service-model/tenant-ownership-and-eventlock-service.md](service-model/tenant-ownership-and-eventlock-service.md)
- Function8 Leistungskatalog:
  [docs/de/service-model/function8-service-catalog.md](service-model/function8-service-catalog.md)
- Drittbetrieb und Exit ohne Lock-in:
  [docs/de/service-model/third-party-operations-and-exit.md](service-model/third-party-operations-and-exit.md)
