# Plugin Plan: OCI Infrastructure

Status: `proposed`

## Ziel

OCI wird lokal aus WSL angebunden und dient für NaC als mögliche Infrastruktur- und Evidence-Plattform:

- OCI CLI für lokale Verwaltung.
- Resource Manager für Terraform/OpenTofu-Stacks.
- OCI Streaming und Object Storage für revisionssichere Eventstreams.
- Vault für Signaturen und Schlüsselreferenzen.

## Day0

- OCI CLI lokal installieren.
- Lokalen API-Key erzeugen, Public Key in OCI hochladen, Private Key lokal halten.
- `~/.oci/config` lokal pflegen.
- Zugriff prüfen:

```bash
oci iam region list
oci iam region-subscription list --tenancy-id <tenancy_ocid>
```

- Keine OCI-Keys oder Configs ins Repo committen.

## Day1

- Resource Manager Stack für erste IaC-Konfiguration anlegen.
- OCI Eventstream-Runbook aus `docs/de/eventstream/runbook-oci.md` konkretisieren.
- Minimalen Plan für folgende Komponenten erstellen:
  - Compartment-Struktur.
  - IAM-Policies für Operator, Audit Reader und Break Glass.
  - Object Storage Bucket für Evidence.
  - Streaming Stream für Event Journal.
  - Vault Key für Daily Anchors.
- Terraform/OpenTofu-Code erst nach Plan-Review anwenden.

## Day2

- API-Keys rotieren.
- Resource Manager Drift Detection oder refresh-only Plan nutzen.
- Kosten- und Quota-Grenzen dokumentieren.
- Retention, Legal Hold und Evidence-Read-Pfad prüfen.
- Manuelle OCI-Konsoleingriffe in Git reconciled.

## Connector-Grenzen

Der OCI-Connector darf:

- OCI-Metadaten lesen.
- Resource-Manager-Plans anstossen.
- Evidence- und Drift-Status dokumentieren.
- freigegebene Stacks anwenden.

Der OCI-Connector darf nicht:

- Private Keys ins Repo schreiben.
- Resource Manager State manuell verändern.
- Retention-/Legal-Hold-Regeln ohne Review ändern.
- Omnistation-Keys oder Remote-Keys wiederverwenden.

## Akzeptanzkriterien

- OCI CLI funktioniert lokal in WSL.
- Private Keys bleiben lokal.
- Resource Manager oder Remote State ist vor Teamnutzung entschieden.
- Eventstream- und Evidence-Komponenten sind mit Runbooks verknüpft.
