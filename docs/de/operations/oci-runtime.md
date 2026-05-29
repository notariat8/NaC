# NaC OCI Runtime

Dieses Dokument beschreibt den ersten Live-Runtime-Vertrag für die NaC-Web-App
in OCI. Diese Umgebung verarbeitet keine Mandatsdaten. Keine Mandatsdaten,
Kundengeheimnisse, OCI-API-Schlüssel oder Tenant-Zugangsdaten werden in diesem
Repository oder in der systemd-Unit gespeichert.

Erforderliches Apply-Gate:

`Owner Apply Approval for Apply Block G NaC runtime deployment`

Der erste Runtime-Befehl lautet:

`nac-web --repo-root /opt/nac/current --host 0.0.0.0 --port 8768`

Erste Live-Endpunkte:

- `GET /healthz`
- `GET /admin/onboarding`

Der Zugriff auf die private OCI-VM erfolgt über OCI Bastion-Diagnostik oder
einen anderen owner-approved privaten Zugriffspfad. Für diese Runtime wird kein
öffentlicher SSH-Zugriff ergänzt.
