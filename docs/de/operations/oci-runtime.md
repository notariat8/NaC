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

## OCI Functions Parallel Runtime

Die nächste Runtime-Stufe ist eine OCI Functions Parallel Runtime hinter OCI
API Gateway. Sie ersetzt die VM nicht sofort: Die VM bleibt Fallback, bis der
Functions-Pfad live per Smoke-Test bestätigt ist.

Der erste Functions-Adapter ist grundsätzlich GET/HEAD-only. Er ruft denselben
`NaCLocalWebApp.handle(...)`-Vertrag wie der lokale Webserver auf. Genau eine
POST-Ausnahme ist für das Kunden-Onboarding zugelassen:
`POST /onboarding/requests`. Dieser Pfad nimmt nur Domain, Tenant-Referenz und
verantwortliche E-Mail-Adresse entgegen. Es werden keine Mandatsdaten, Secrets,
OCI-API-Schlüssel oder Tenant-Zugangsdaten im Function-Paket gespeichert.

Erforderliches Apply-Gate für den Functions-Parallelpfad:

`Owner Apply Approval for Apply Block J NaC OCI Functions parallel runtime`

## No-SSH Functions Release

Für die cloud-native Runtime ist der Zielpfad ein No-SSH Functions Release.
Ein geschützter, gemergter GitHub-Commit wird durch OCI DevOps gebaut, als
Container-Image in OCIR abgelegt und dort über einen OCIR-Digest gebunden. Die
OCI Function wird auf diesen Digest aktualisiert und anschließend über einen
API-Gateway-Smoke-Test geprüft.

Dieser Pfad benötigt keinen Bastion- oder SSH-Zugriff auf die VM. Die VM bleibt
Fallback, bis der API-Gateway-Pfad für `/healthz`, `/onboarding/readiness`,
`/onboarding/dns-check`, `/login` und `/api/tenant/login-intent` live geprüft
ist und ein separates Owner-Apply-Gate den Cutover freigibt.

Der Function-Release-Pfad bleibt bis auf `POST /onboarding/requests`
GET/HEAD-only. Login-Intent-Konfiguration kommt ausschließlich aus
serverseitigen Umgebungswerten; Query-Parameter dürfen keine Identity-Domain-,
Client-, Redirect-, State- oder Nonce-Werte setzen.

## ATP-Onboarding-Request-Store

Der produktive Store für Onboarding-Anfragen wird nur über ein explizites
serverseitiges Gate aktiviert:

- `NAC_ONBOARDING_STORE=atp`
- `NAC_ATP_DSN`
- `NAC_ATP_USER`
- `NAC_ATP_PASSWORD_SECRET_OCID`

Ein Klartext-Passwort in `NAC_ATP_PASSWORD` aktiviert den Store nicht. Fehlt
einer der erforderlichen Werte, bleibt die Route fail-closed und antwortet mit
`onboarding_request_store_disabled`. Der Passwortwert wird zur Laufzeit über
OCI Vault und Resource Principal gelesen; in Git, Chat, Query-Parametern,
HTML und Function-Config steht nur die Secret-OCID, nicht der Secret-Inhalt.

Optionale Wallet-/Netzwerkpfade:

- `NAC_ATP_CONFIG_DIR`
- `NAC_ATP_WALLET_LOCATION`

Der ATP-Apply, Tabellenanlage und Secret-Boundary bleiben ein separater
Owner-gated Infrastruktur-Track über `notariat8/oci-landing-zone#44`. Der
App-Adapter-Track ist `notariat8/NaC#85`.

## App-Release-Overlay

Normale NaC-Software-Releases brauchen nach dem initial stabilen Runtime-Start
kein VM-Replacement. Der Standardpfad ist ein App-Release-Overlay: Ein reviewed
NaC-Commit wird als geprüftes Archiv mit dokumentierter SHA-256 auf die private
Runtime übertragen, durch [deploy/runtime/nac-web-release.sh](../../../deploy/runtime/nac-web-release.sh)
nach `/opt/nac/releases/<commit>` entpackt, über `/opt/nac/current` aktiviert
und anschließend per systemd-Restart von `nac-web` geprüft.
Der Healthcheck nutzt ein kurzes, konfigurierbares Wartefenster
(`NAC_RELEASE_HEALTH_ATTEMPTS`, `NAC_RELEASE_HEALTH_SLEEP_SECONDS`), damit ein
gesunder Prozess nach dem Restart Zeit zum Binden des Ports hat. Wenn der
Healthcheck danach fehlschlägt, setzt das Skript `/opt/nac/current` per
Rollback auf den vorherigen Zielstand zurück und startet `nac-web` erneut.

Erforderliches Apply-Gate für diesen App-Release-Pfad:

`Owner Apply Approval for Apply Block H NaC app release overlay`

Das VM-Replacement bleibt ein Fallback oder eine bewusste Host-Änderung. Es ist
weiterhin erforderlich, wenn sich Basisimage, Betriebssystem, Firewall,
Netzpfad, systemd-Vertrag oder Abhängigkeiten ändern, die nicht bereits auf der
laufenden Runtime vorhanden sind.

Der Zugriff auf die private OCI-VM erfolgt über OCI Bastion-Diagnostik oder
einen anderen owner-approved privaten Zugriffspfad. Für diese Runtime wird kein
öffentlicher SSH-Zugriff ergänzt.
