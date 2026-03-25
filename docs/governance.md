# Governance mit Git und GitHub

## Repository-Regeln

Empfohlenes Zielbild fuer `main`:

- Pushes direkt auf `main` verbieten
- Pull Requests verpflichtend machen
- Status-Checks aus `Validate Business Processes` verlangen
- Review durch mindestens eine fachlich verantwortliche Person verlangen
- Signierte Tags fuer Abschluesse wie `close/2026-03` verwenden

Empfehlung fuer Unternehmens-Forks:

- technische Prozessreleases als `v*` markieren
- Upstream-Uebernahme nur ueber dokumentierte Sync-PRs
- laufende Vorgaenge auf Startversion belassen (Version-Binding)

## Environment-Mapping

- `business-operations`: sensible manuelle Ausfuehrung einzelner Prozesse
- `month-close`: Monatsabschluss und periodische Aggregation
- optional `tax-submission`: letzte Freigabestufe vor externer Steuerabgabe

## Fachliches Mapping

| Git/GitHub-Mechanismus | Fachliche Bedeutung |
| --- | --- |
| Branch | in Arbeit befindlicher Geschaeftsvorgang |
| Pull Request | formaler Antrag mit Freigabebedarf |
| Review | fachliche Freigabe |
| Action Run | dokumentierte maschinelle Ausfuehrung |
| Artifact | exportierter Nachweis oder Bericht |
| Tag | Abschlussstand |
| Release | publizierter, versionierter Nachweis |

## Praktische Regeln pro Domäne

### Gruendung

- Schritte koennen in einem Sammelvorgang oder als einzelne Prozessdateien gefuehrt werden.
- Status `needs_review` sollte mit manuellem Review gekoppelt werden.

### Rechnungsstellung

- `draft -> approved` nur ueber Pull Request.
- `approved -> issued` nur in einer gesicherten Runtime oder nach dokumentierter Freigabe.
- RVG-bezogene Rechnungen nur mit dokumentierter Qualifikation und Freigabe.

### Buchfuehrung

- Buchungssaetze muessen ausgeglichen sein.
- Idempotenzschluessel und Belegreferenzen verhindern Doppelbuchungen.

### Steuer

- `prepared -> approved` immer mit Vier-Augen-Prinzip.
- `submitted` sollte nur nach manueller Freigabe und moeglichem externen Filing gesetzt werden.

## Rollenbasierte Entscheidungslogik

- Jede Rolle darf Tickets eroefnnen.
- `low impact` ohne Compliance-Effekt kann self-resolve sein.
- `medium/high impact` oder rechtlicher Effekt braucht Review/Approval.
- Qualifikationspflichten haben Vorrang vor allgemeinen Rollenrechten.

Referenz: `policies/role-model-policy.yaml`

## Weiterfuehrende Betriebsstandards

- Fork-Modell und Verantwortungen: `docs/fork-and-release-operating-model.md`
- Sync-Zyklus und PR-Gates: `docs/release-sync-playbook.md`
- Mischbetrieb und Audit-Nachweis: `docs/parallelbetrieb-version-binding.md`
- Repo-uebergreifende Issue-Fuehrung: `docs/issue-taxonomie-pro-repo.md`
- Rollen, Zugriffe und zentrale Task-Uebersicht: `docs/access-and-issue-operations.md`
- Revisionssicherheit ueber Event-Journal: `docs/revisionssicherheit-eventstreaming.md`
- Konkrete Plattformvorlagen: `docs/eventstream-implementation-templates.md`
- Azure Runbook: `docs/eventstream-runbook-azure.md`
- AWS Runbook: `docs/eventstream-runbook-aws.md`
- GCP Runbook: `docs/eventstream-runbook-gcp.md`
- OCI Runbook: `docs/eventstream-runbook-oci.md`
- Tenant-Owner- und Service-Modell: `docs/tenant-ownership-and-eventlock-service.md`
- Function8 Leistungskatalog: `docs/function8-service-catalog.md`
- Drittbetrieb und Exit ohne Lock-in: `docs/third-party-operations-and-exit.md`
