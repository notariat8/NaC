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
Nach erfolgreichem Anlegen antwortet der öffentliche Pfad mit `303 See Other`
und `Location: /onboarding/requests/<request_id>?audience=customer`. Diese
Statusseite ist per GET/HEAD öffentlich lesbar und reloadbar; die URL enthält
keine Administrations-E-Mail und öffnet keine Admin-Queue-Funktionen.

Erforderliches Apply-Gate für den Functions-Parallelpfad:

`Owner Apply Approval for Apply Block J NaC OCI Functions parallel runtime`

## No-SSH Functions Release

Für die cloud-native Runtime ist der Zielpfad ein No-SSH Functions Release.
Ein geschützter, gemergter GitHub-Commit wird durch OCI DevOps gebaut, als
Container-Image in OCIR abgelegt und dort über einen OCIR-Digest gebunden. Die
OCI Function wird auf diesen Digest aktualisiert und anschließend über einen
API-Gateway-Smoke-Test geprüft.

Der Release ist commitgebunden: Der OCI DevOps Build-Run muss den
owner-freigegebenen Commit zusätzlich zu `commit-info` als Build-Argument
`NAC_RELEASE_COMMIT` erhalten. Die Build-Spec detacht den Checkout auf diesen
Commit und bricht ab, wenn der Commit nicht im OCI-Mirror verfügbar ist oder der
aktive Checkout davon abweicht. `commit-info` allein ist nur Audit-Metadatum und
pinnt den Build-Checkout nicht.

Dieser Pfad benötigt keinen Bastion- oder SSH-Zugriff auf die VM. Die VM bleibt
Fallback, bis der API-Gateway-Pfad für `/healthz`, `/onboarding/readiness`,
`/onboarding/dns-check`, `/login` und `/api/tenant/login-intent` live geprüft
ist und ein separates Owner-Apply-Gate den Cutover freigibt.

Der Function-Release-Pfad bleibt bis auf `POST /onboarding/requests`
GET/HEAD-only; die reloadbare Kundenseite
`GET /onboarding/requests/<request_id>?audience=customer` ist die zugehörige
öffentliche Lese-Route nach dem Redirect. Login-Intent-Konfiguration kommt ausschließlich aus
serverseitigen Umgebungswerten; Query-Parameter dürfen keine Identity-Domain-,
Client-, Redirect-, State- oder Nonce-Werte setzen.

## ATP-Onboarding-Request-Store

Der produktive Store für Onboarding-Anfragen und serverseitige Portal-Sessions
wird nur über explizite serverseitige Gates aktiviert:

- `NAC_ONBOARDING_STORE=atp`
- `NAC_SESSION_STORE=atp`
- `NAC_ATP_DSN`
- `NAC_ATP_USER`
- `NAC_ATP_PASSWORD_SECRET_OCID`
- `NAC_ATP_WALLET_OBJECT_STORAGE_NAMESPACE` bei mTLS-erforderlicher ATP
- `NAC_ATP_WALLET_BUCKET_NAME` bei mTLS-erforderlicher ATP
- `NAC_ATP_WALLET_OBJECT_NAME` bei mTLS-erforderlicher ATP
- `NAC_ATP_WALLET_PASSWORD_SECRET_OCID` bei mTLS-erforderlicher ATP

Ein Klartext-Passwort in `NAC_ATP_PASSWORD` aktiviert keinen Store. Fehlt
einer der erforderlichen Werte, bleiben die betroffenen Routen fail-closed.
Onboarding antwortet mit `onboarding_request_store_disabled`; geschützte
Startseiten bleiben ohne aktiven Server-Session-Record geschlossen. Der
Passwortwert wird zur Laufzeit über OCI Vault und Resource Principal gelesen;
in Git, Chat, Query-Parametern, HTML und Function-Config steht nur die
Secret-OCID, nicht der Secret-Inhalt.

Bei mTLS-erforderlicher ATP wird das Wallet-Zip aus einem privaten Object
Storage Bucket gelesen und in das ephemere Function-Dateisystem entpackt. Das
Wallet-Passwort bleibt ein separates Vault-Secret. Das Wallet enthält
Credential-Material, nicht Mandatsdaten. Der Inhalt wird nicht in Git, Chat,
Resource-Manager-Variablen, Function-Config, Query-Parametern oder HTML
geschrieben. `NAC_ATP_WALLET_ZIP_SECRET_OCID` bleibt nur als
Kompatibilitäts-Pfad erhalten, weil ein reales ATP-Wallet nach Base64-Encoding
nicht zuverlässig in ein einzelnes OCI Vault Secret passt.

Optionale Wallet-/Netzwerkpfade:

- `NAC_ATP_CONFIG_DIR`
- `NAC_ATP_WALLET_LOCATION`
- `NAC_ATP_WALLET_EXTRACT_DIR`

Der ATP-Apply, Tabellenanlage und Secret-Boundary bleiben ein separater
Owner-gated Infrastruktur-Track über `notariat8/oci-landing-zone#44`. Der
App-Adapter-Track ist `notariat8/NaC#85`.

Das versionierte Bootstrap-Artefakt für die ersten Tabellen liegt in
[deploy/database/atp-onboarding-request-store.sql](../../../deploy/database/atp-onboarding-request-store.sql).
Es legt `onboarding_requests` und `nac_sessions` mit den aktuellen
Vertragsfeldern an. `nac_sessions` speichert nur gehashte Session-IDs,
Tenant-/Benutzer-/Vorgangs-/Zweck-Bindungen und redaktierte Audit-Metadaten.
Tokens, Claims, Zugangsdaten und Mandatsdaten sind per Contract und
Schema-Guardrail ausgeschlossen. Die Ausführung gehört in den
Block-M-Runbook-Schritt nach geprüfter ATP-Zielwahl und vor dem finalen
Live-Smoke für `POST /onboarding/requests` und den geschützten
`GET /workspace`-Startstatus.
Der Smoke-Test muss zusätzlich den `303`-Redirect und die reloadbare
GET-Statusseite ohne `admin_email` in der URL prüfen.

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
