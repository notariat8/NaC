# Plugin Plan: OCI Infrastructure

Status: `proposed`

## Ziel

OCI wird lokal aus WSL angebunden und dient fuer NoC als moegliche Infrastruktur- und Evidence-Plattform:

- OCI CLI fuer lokale Verwaltung.
- Resource Manager fuer Terraform/OpenTofu-Stacks.
- OCI Streaming und Object Storage fuer revisionssichere Eventstreams.
- Vault fuer Signaturen und Schluesselreferenzen.

## Day0

- OCI CLI lokal installieren.
- Lokalen API-Key erzeugen, Public Key in OCI hochladen, Private Key lokal halten.
- `~/.oci/config` lokal pflegen.
- Zugriff pruefen:

```bash
oci iam region list
oci iam region-subscription list --tenancy-id <tenancy_ocid>
```

- Keine OCI-Keys oder Configs ins Repo committen.

## Day1

- Resource Manager Stack fuer erste IaC-Konfiguration anlegen.
- OCI Eventstream runbook from `docs/en/eventstream/runbook-oci.md` needs to be concretized.
- Minimalen Plan fuer folgende Komponenten erstellen:
  - Compartment-Struktur.
  - IAM-Policies fuer Operator, Audit Reader und Break Glass.
  - Object Storage Bucket fuer Evidence.
  - Streaming Stream fuer Event Journal.
  - Vault Key fuer Daily Anchors.
- Terraform/OpenTofu-Code erst nach Plan-Review anwenden.

## Day2

- API-Keys rotieren.
- Resource Manager Drift Detection oder refresh-only Plan nutzen.
- Kosten- und Quota-Grenzen dokumentieren.
- Retention, Legal Hold und Evidence-Read-Pfad pruefen.
- Manuelle OCI-Konsoleingriffe in Git reconciled.

## Connector-Grenzen

Der OCI-Connector darf:

- OCI-Metadaten lesen.
- Resource-Manager-Plans anstossen.
- Evidence- und Drift-Status dokumentieren.
- freigegebene Stacks anwenden.

Der OCI-Connector darf nicht:

- Private Keys ins Repo schreiben.
- Resource Manager State manuell veraendern.
- Retention-/Legal-Hold-Regeln ohne Review aendern.
- Omnistation-Keys oder Remote-Keys wiederverwenden.

## Akzeptanzkriterien

- OCI CLI funktioniert lokal in WSL.
- Private Keys bleiben lokal.
- Resource Manager oder Remote State ist vor Teamnutzung entschieden.
- Eventstream- und Evidence-Komponenten sind mit Runbooks verknuepft.
