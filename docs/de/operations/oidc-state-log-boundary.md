# OIDC State- Und Log-Grenze

Stand: 2026-06-18.

## Zweck

Der Login-Callback darf nicht als Anmeldung gelten, bevor `state`,
Token-Antwort, Sitzung und notariat8-Rollengate geprüft sind. `state` ist kein
Mandatsdatum, aber ein sicherheitsrelevanter Callback-Wert. Er darf nicht in
Kundentexten, Reports, Debug-Ausgaben oder allgemein zugänglichen Logs landen.

## State-Vertrag

NaC kennt den Vertrag `nac.oidc-state/v0.1` für signierte, ablaufende
State-Werte:

- Status `valid`: Signatur und Ablauf sind gültig; der Tenant-Hinweis ist nur
  Kontext.
- Status `invalid`: Format oder Signatur passen nicht.
- Status `expired`: Signatur passt, aber der State ist abgelaufen.
- Status `not_configured`: Es gibt noch keinen geprüften serverseitigen
  Signing-Key-Pfad.

Auch bei `valid` bleibt der Arbeitsbereich geschlossen. Der nächste Schritt ist
Token-Austausch und danach erst das notariat8-Rollen- und Vorgangsgate.

Wenn State-Prüfung als konfiguriert markiert ist, aber kein validiertes
State-Ergebnis vorliegt, muss der Callback fail-closed abgelehnt werden. Ein
Konfigurationshinweis allein gilt nicht als erfolgreiche Prüfung.

## Token-Exchange-Adapter

NaC stellt einen serverseitigen Token-Exchange-Adapter bereit, der den
Authorization Code nur serverseitig gegen den Token-Endpoint tauscht. Der
Adapter ist fail-closed: ohne vollständige Metadaten, Client-Secret und
ID-Token-Verifier wird kein HTTP-Aufruf gestartet. Provider-Fehler, Access
Tokens, Refresh Tokens und ID Tokens werden nicht in browsernahe Ergebnisse
übernommen. Erfolgreich geprüfte Claims dürfen nur als interne Eingabe für das
notariat8-Rollengate weitergereicht werden.

Q2I öffnet weiterhin keinen Arbeitsbereich, darf aber nach gültigem State,
erfolgreichem Token-Austausch, geprüften Claims und positivem
notariat8-Rollengate ein kurzlebiges, signiertes Session-Cookie setzen. Das
Cookie enthält keine Tokens, Claims, Nonces, Providerdetails oder
Callback-Werte. Der Produktivbetrieb braucht zusätzlich den geprüften
Secret-Pfad und die serverseitige ID-Token-Signaturprüfung.

Q2G verdrahtet den zustandsbehafteten Callback mit diesem Adapter, öffnet aber
weiterhin keinen Arbeitsbereich. Der Callback
liest den Vault-basierten Client-Secret-Pfad nur, wenn `state` gültig ist,
`code`, Redirect-URI, Token-Endpoint und Client-ID vollständig vorliegen und
eine serverseitige ID-Token-Prüfung konfiguriert ist. Fehlt eine dieser
Bedingungen, bleibt der Pfad geschlossen und es wird kein produktiver
Arbeitsbereich geöffnet.

Q2H macht die Claim-Grenze explizit: Erfolgreich geprüfte Claims dürfen intern
an das notariat8-Rollengate weitergereicht werden. Browsernahe Ergebnisse
zeigen nur, ob die Claims verifiziert und an das Rollengate übergeben wurden.
E-Mail-Adressen, Gruppenlisten, Tokens, Nonces, Providerdetails und
Callback-Werte bleiben aus Kundentexten, Reports und normalen Logs heraus.
Auch bei bestätigter Rolle öffnet NaC in diesem Slice keinen Arbeitsbereich;
Q2I ergänzt nur die signierte Session-Grenze.

Q2J prüft das signierte Session-Cookie serverseitig und darf nur eine
geschützte notariat8-Start-/Statusseite öffnen. Fehlende, manipulierte,
abgelaufene oder unkonfigurierte Cookies bleiben fail-closed. Das
Prüfergebnis gibt keinen Cookie-Wert, Token, Claim, Nonce, Providerdetail oder
Callback-Wert aus. Der vollständige Arbeitsbereich und alle Mandatsdaten
bleiben geschlossen.

Q2K ergänzt die produktionsfähige ID-Token-Prüfung auf der Serverseite. Der
Verifier verwendet die konfigurierte Identity-Domain-URL als Issuer, die
konfigurierte Client-ID als Audience und lädt die Signaturschlüssel über
OIDC-Discovery und JWKS. Nur RS256-signierte ID Tokens mit passendem Issuer,
passender Audience und gültigem Ablauf werden intern als geprüfte Claims an das
notariat8-Rollengate weitergegeben. Bei fehlender Konfiguration, ungültiger
Signatur, falscher Audience, falschem Issuer oder abgelaufenem Token bleibt der
Pfad geschlossen. Browsernahe Ergebnisse enthalten weiterhin keine Tokens,
Claims, Nonces, Providerdetails oder Callback-Werte.

## Aktueller OCI-Befund

Read-only geprüft am 2026-06-18:

- Der aktive OCI-Logging-Pfad fuer die zustandsbehaftete Function ist die
  Functions invoke Log-Gruppe `nac-dev-functions-logs` mit dem Log
  `nac-dev-functions-invoke`.
- Die abgefragten Eintraege fuer die Function `nac-dev-nac-app` enthalten nur
  feste Service-Meldungen wie `Received function invocation request` und
  `Served function invocation request ...` sowie Function- und
  Request-Metadaten.
- Die Logging Search lieferte keine Callback-URL und keine browserseitigen
  Callback-Werte wie `code`, `state`, `nonce`, `token` oder `claim` in den
  zurueckgegebenen Feldern.
- Der lokale NaC-Webserver redigiert `/auth/callback`-callback query Werte in
  seinen Requestlogs.

Das ist ein momentaner Befund, keine dauerhafte Freigabe. Wenn
API-Gateway-, Function-, Proxy- oder CDN-Access-Logs aktiviert werden, muss
vorher nachgewiesen werden, dass `code` und `state` nicht als Query-String
gespeichert werden.

## Wiederholbarer Proof

Der Proof bleibt read-only und braucht Kein OCI Apply:

1. Live-Routen nur lesend aufrufen: `/healthz`, `/login`, `/workspace` und
   `/api/tenant/login-intent`.
2. OCI Logging Search fuer das aktive Functions invoke Log
   `nac-dev-functions-invoke` auf die Function `nac-dev-nac-app` begrenzen.
3. Ergebnis nur als redigierte Evidenz dokumentieren: Service-Meldungen,
   Function-Name, Zeitfenster und dass keine callback query Werte (`code`,
   `state`, `nonce`, `token`, `claim`) in den zurueckgegebenen Feldern
   auftauchen.
4. Die Evidenz per Protected PR versionieren. Ein Apply-Gate ist erst noetig,
   wenn Logging-Policies, API-Gateway-Routen, Secret-Zugriffe oder Runtime-
   Konfiguration geaendert werden.

## Nächste Grenze

Vor produktivem Token-Austausch auf der Live-Route ist eine der folgenden
Varianten erforderlich:

1. Nachweis, dass alle beteiligten Logs Callback-Queries redigieren oder gar
   nicht speichern.
2. Wechsel des Callback-Modus auf eine geeignete POST-Kante, zum Beispiel einen
   separat geprüften `response_mode=form_post`-Pfad.
3. Geprüfter Secret-/Key-Pfad für die State-Signatur, das OIDC-Client-Secret
   und die Session-Signatur, bevor die Live-Route eine echte State-, Token-
   und Session-Prüfung als konfiguriert behandeln darf.

Beide Varianten brauchen einen eigenen Protected PR. Falls dafür API-Gateway-
Routen, Logging-Policies oder Secret-Zugriffe geändert werden, braucht der
Apply außerdem eine explizite Owner-Freigabe.
