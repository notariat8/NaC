# Governance mit Git und GitHub

## Repository-Regeln Und Auslieferungsmodi

Empfohlenes Zielbild für produktive Forks und sensible Prozessänderungen:

- Pushes direkt auf `main` verbieten
- Pull Requests verpflichtend machen
- Status-Checks aus `Validate Business Processes` verlangen
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

## Environment-Mapping

- `business-operations`: sensible manuelle Ausführung einzelner Prozesse
- `month-close`: Monatsabschluss und periodische Aggregation
- optional `tax-submission`: letzte Freigabestufe vor externer Steuerabgabe

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

### Gründung

- Schritte können in einem Sammelvorgang oder als einzelne Prozessdateien geführt werden.
- Status `needs_review` sollte mit manuellem Review gekoppelt werden.

### Rechnungsstellung

- `draft -> approved` nur über Pull Request.
- `approved -> issued` nur in einer gesicherten Runtime oder nach dokumentierter Freigabe.
- RVG-bezogene Rechnungen nur mit dokumentierter Qualifikation und Freigabe.

### Buchführung

- Buchungssätze müssen ausgeglichen sein.
- Idempotenzschlüssel und Belegreferenzen verhindern Doppelbuchungen.

### Steuer

- `prepared -> approved` immer mit Vier-Augen-Prinzip.
- `submitted` sollte nur nach manueller Freigabe und möglichem externen Filing gesetzt werden.

## Rollenbasierte Entscheidungslogik

- Jede Rolle darf Tickets eröffnen.
- `low impact` ohne Compliance-Effekt kann self-resolve sein.
- `medium/high impact` oder rechtlicher Effekt braucht Review/Approval.
- Qualifikationspflichten haben Vorrang vor allgemeinen Rollenrechten.

Referenz: [policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)

## Weiterführende Betriebsstandards

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
