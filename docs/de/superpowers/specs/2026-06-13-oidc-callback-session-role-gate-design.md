# OIDC Callback, Session und NaC-Rollengate

Datum: 2026-06-13

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: oidc-callback-session-role-gate
leading_issue: https://github.com/notariat8/NaC/issues/128
risk_gate: Identity and Session
delivery_mode: Protected PR
acceptance_ids:
  - AC-001
  - AC-002
  - AC-003
  - AC-004
  - AC-005
  - AC-006
validation_commands:
  - env PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_oci_functions_adapter
  - env GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

## Kontext

Der Live-Test für `myjur` hat den OIDC-Fluss bis zur Rückkehr nach
`/auth/callback` bestätigt. Passwort-Reset, Consent und Redirect funktionieren.
NaC zeigt danach bewusst nur `Anmeldung empfangen`, weil der Arbeitsbereich erst
nach serverseitiger State-, Token-, Session- und Rollenprüfung geöffnet werden
darf.

Der aktuelle Zustand ist damit kein Identity-Provider-Fehler, sondern der
nächste Produktinkrement: Der Auth-Callback muss vom geschlossenen
Zwischenereignis zur validierten notariat8-Sitzung werden.

## Entscheidung

Ansatz A ist freigegeben: `/auth/callback` wird fachlich zur auth/stateful
Runtime gehören. Die Public-GET-Function bleibt für öffentliche Seiten und
Login-Intent-Readiness leicht und möglichst secretfrei. Token-Austausch,
Client-Secret-Zugriff, Session-Erzeugung und NaC-Rollengate laufen serverseitig
im geschützten Callback-Pfad.

## Ziele

- `state` wird serverseitig validiert und abgelaufene oder fremde Werte schlagen
  geschlossen fehl.
- Der Authorization Code wird nur serverseitig gegen Tokens getauscht.
- ID-Token werden gegen Issuer, Audience, Nonce und Signatur geprüft.
- NaC mappt Identity-Domain-Gruppen oder Claims auf eigene Rollen.
- Ein geschützter Arbeitsbereich wird erst nach positivem Rollengate geöffnet.
- Callback-Werte, Tokens und Secrets erscheinen nicht in Browsertexten, Logs,
  GitHub, Git oder Chat.

## Nichtziele

- Keine Mandatsdaten in diesem Track.
- Kein generisches Benutzerverwaltungs-Frontend.
- Keine Umstellung der gesamten Public-GET-Function auf eine secretführende
  Runtime.
- Keine OCI-Schreiboperation ohne eigenes Owner Apply Gate.

## Architektur

Die Login-Intent-Route bleibt public und erzeugt den signierten Redirect-Kontext.
Der Callback wird dagegen in eine stateful/auth Runtime geführt. Diese Runtime
hat Zugriff auf die notwendigen Vault-Referenzen, nicht auf Klartext-Secrets in
Git oder Function-Konfiguration.

Der Callback verarbeitet nur serverseitig:

1. Query empfangen und Log-Ausgabe redigieren.
2. `state` validieren und `tenant_hint` nur als Kontext behandeln.
3. Code am Token-Endpunkt tauschen.
4. ID-Token und Nonce validieren.
5. Gruppen/Claims auf NaC-Rollen abbilden.
6. Session-Cookie mit sicheren Attributen setzen.
7. Nur bei passender Rolle in den Arbeitsbereich weiterleiten.

## Rollenmodell

Für den ersten Live-Test ist `nac-tenant-admin` der Rollenanker. Ein IdP-Login
allein reicht nicht. NaC akzeptiert nur eine serverseitig verifizierte
Rollenbindung, zum Beispiel die Mitgliedschaft in `nac-tenant-admin`, bevor der
Arbeitsbereich für `myjur` geöffnet wird.

`tenant_hint` bleibt unverbindlich. Er hilft beim Routing und bei der Anzeige,
begründet aber keine Berechtigung.

## Sicherheitsregeln

- Client Secrets liegen ausschließlich in OCI Vault oder einem gleichwertigen
  Secret Store.
- Tokens werden nicht persistiert, solange keine explizite Session-Store-
  Entscheidung getroffen wurde.
- Session-Cookies sind `HttpOnly`, `Secure` und `SameSite=Lax`.
- Fehlerseiten zeigen keine Providerdetails, Codes, States, Nonces, Tokens oder
  Secret-Referenzen.
- Rollengate-Fehler sind geschlossen: kein Workspace, keine Mandatsdaten.

## Akzeptanzkriterien

- AC-001: Die Public-GET-Function liefert für `/auth/callback` geschlossen
  `404` und zeigt weder `code` noch `state` im Antwortkörper.
- AC-002: Die stateful NaC-Function bedient `/auth/callback` weiterhin, damit
  Token-Austausch, Session-Aufbau und Rollengate dort ergänzt werden können.
- AC-003: Callback-Werte, Tokens und Secrets werden in Public- und Stateful-
  Antworten nicht offengelegt.
- AC-004: Q2C führt einen reinen, lokal testbaren Token-Claim- und
  Rollen-Gate-Vertrag ein. Er prüft Issuer, Audience, Nonce-Bindung und
  `nac-tenant-admin`, öffnet aber noch keine Sitzung und führt keinen Live-
  Token-Austausch aus.
- AC-005: Der Q2C-Vertrag schlägt geschlossen fehl, wenn Issuer, Audience,
  Nonce-Bindung oder Rolle fehlen oder nicht passen.
- AC-006: Der Q2C-Vertrag gibt keine Roh-Tokens, Callback-Codes, States,
  Nonces, Nonce-Hashes oder Secret-Referenzen in browsernahe Ergebnisse aus.

## Q2C-Schnitt

Q2C ist bewusst kein OCI-Apply und kein Live-Token-Austausch. Der Schnitt
modelliert die serverseitige Entscheidung, die nach einer späteren Token-
Exchange-Schicht benötigt wird: Aus bereits verifizierten Claims entsteht nur
dann eine NaC-Rollenentscheidung, wenn die Claims zur erwarteten Identity
Domain, zum erwarteten OIDC-Client, zur nonce-gebundenen State-Validierung und
zur Rolle `nac-tenant-admin` passen.

Damit wird die spätere Live-Anbindung kleiner und sicherer: Token-Austausch und
JWT-Signaturprüfung liefern dann nur noch Eingaben an diesen Vertrag. Jede
Abweichung bleibt fail-closed und öffnet keinen Arbeitsbereich.

## Tests

Die Implementierung braucht Tests für:

- gültigen Callback mit validiertem State, Token-Antwort und passender Rolle,
- ungültigen oder abgelaufenen State,
- Token-Exchange-Fehler ohne Secret-Leak,
- ID-Token mit falschem Issuer, falscher Audience oder falscher Nonce,
- fehlende Rolle trotz erfolgreichem IdP-Login,
- Session-Cookie nur nach positivem Rollengate,
- Schutz gegen Callback-Werte in HTML und Logs.

## Auslieferung

Die Code-Änderung erfolgt über geschützten PR. Danach folgen getrennte Gates:

1. Release Approval für das neue NaC-Image.
2. Resource-Manager-Plan ohne Apply für Route/Function-Konfiguration.
3. Owner Apply Approval für die Callback-Route zur auth/stateful Runtime und
   die Vault-Secret-Referenz.
4. Live-Test mit synthetischem `myjur`-Testkonto.
