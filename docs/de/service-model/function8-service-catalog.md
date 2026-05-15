# Function8 Service Catalog fuer NoC

## Ziel

Dieses Dokument listet alle Function8-Leistungen im Kontext `NoC` transparent und oeffentlich nachvollziehbar.
Leistungen mit AVV-Pflicht muessen als solche gekennzeichnet und mit den erforderlichen Artefakten verlinkt sein.

## Katalogprinzip

- Jede Leistung hat eine stabile `service_id`.
- Jede Leistung nennt explizit, ob AVV erforderlich ist.
- Jede Leistung ist mit Policies, Runbooks und Exit-Pfad verknuepft.
- Keine versteckten Betriebsabhaengigkeiten ausserhalb dieses Repos.

## Leistungskatalog

| service_id | service_name | service_type | avv_required | data_scope | required_policies | runbook_references | portability_notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| f8-eventlock-saas | EventLock-as-a-Service | managed_saas | yes | event_journal_and_metadata | `policies/revisionssicherheit-eventstream-policy.yaml`, `policies/tenant-ownership-policy.yaml`, `policies/provider-open-services-policy.yaml` | `docs/de/eventstream/revisionssicherheit.md`, `docs/de/eventstream/implementation-templates.md`, `docs/de/eventstream/runbook-aws.md`, `docs/de/eventstream/runbook-azure.md`, `docs/de/eventstream/runbook-gcp.md`, `docs/de/eventstream/runbook-oci.md` | dedizierte Subinstanz pro Kunde, dokumentierter Exit |
| f8-noc-governance-pack | Governance und Policy Pack | documentation_and_controls | no | governance_metadata | `policies/process-policy.yaml`, `policies/role-model-policy.yaml`, `policies/access-control-policy.yaml` | `docs/de/governance.md`, `docs/de/issues/operations.md` | vollstaendig repo-basiert, durch Dritte uebernehmbar |
| f8-onboarding-pack | Onboarding und Einfuehrungsunterlagen | documentation | no | onboarding_metadata | `policies/onboarding-flow.json`, `policies/provider-open-services-policy.yaml` | `docs/de/START_HERE.md`, `docs/de/vscode-copilot-start.md`, `docs/de/platform-onboarding-matrix.md` | offen dokumentiert, kein proprietaerer Zwang |

## AVV-Referenz

Fuer Leistungen mit `avv_required = yes` gilt:

- `docs/de/avv-checkliste-eventlock-saas.md` ist verpflichtend anzuwenden.
- Subprozessoren, Regionen, Retention und Incident-Meldewege muessen dokumentiert sein.

## Pflegeprozess

1. Neue Leistung nur per PR aufnehmen.
2. `service_id` eindeutig vergeben.
3. AVV-Relevanz begruenden.
4. Runbook-/Policy-Referenzen vervollstaendigen.
5. Exit-/Ersetzbarkeitsnotiz dokumentieren.
