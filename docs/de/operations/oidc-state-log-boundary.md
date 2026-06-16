# OIDC State- Und Log-Grenze

Stand: 2026-06-16.

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

Dieser Stand öffnet noch keinen Arbeitsbereich und setzt kein Session-Cookie.
Der Produktivbetrieb braucht zusätzlich den geprüften Secret-Pfad und die
serverseitige ID-Token-Signaturprüfung.

## Aktueller OCI-Befund

Read-only geprüft am 2026-06-09:

- Das API-Gateway-Deployment `nac-dev-nac-app` hat keine Logging-Policies auf
  Deployment- oder Routenebene.
- Im `nac-dev` Compartment ist nur die DevOps-Service-Log-Gruppe aktiv:
  `nac-dev-devops-logs`.
- Es wurde keine API-Gateway- oder Functions-Access-Log-Gruppe für die
  öffentliche App-Kante gefunden.
- Der lokale NaC-Webserver redigiert `/auth/callback`-Queries in seinen
  Requestlogs.

Das ist ein momentaner Befund, keine dauerhafte Freigabe. Wenn
API-Gateway-, Function-, Proxy- oder CDN-Access-Logs aktiviert werden, muss
vorher nachgewiesen werden, dass `code` und `state` nicht als Query-String
gespeichert werden.

## Nächste Grenze

Vor produktivem Token-Austausch auf der Live-Route ist eine der folgenden
Varianten erforderlich:

1. Nachweis, dass alle beteiligten Logs Callback-Queries redigieren oder gar
   nicht speichern.
2. Wechsel des Callback-Modus auf eine geeignete POST-Kante, zum Beispiel einen
   separat geprüften `response_mode=form_post`-Pfad.
3. Geprüfter Secret-/Key-Pfad für die State-Signatur, bevor die Live-Route
   eine echte State-Prüfung als konfiguriert behandeln darf.

Beide Varianten brauchen einen eigenen Protected PR. Falls dafür API-Gateway-
Routen, Logging-Policies oder Secret-Zugriffe geändert werden, braucht der
Apply außerdem eine explizite Owner-Freigabe.
