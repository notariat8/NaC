# NaC Release Lane Reference

Diese Referenz enthält nur nicht-geheime Release-Prozedur und Entscheidungslogik.
Reale OCIDs, Tokens, API-Keys, private Schlüssel, Zertifikate und Mandatsdaten
gehören nicht in dieses Dokument.

## Zweck

Der NaC-Releasepfad ist commitgebunden. Ein Release darf nicht aus einem
zufällig aktuellen Mirror-Stand entstehen. Der freigegebene GitHub-Commit muss
im OCI-Mirror vorhanden sein und als `NAC_RELEASE_COMMIT` an den Build-Run
übergeben werden.

## Zulässige Quellen für Release-Inputs

- GitHub PR/Merge-Commit und Owner-Release-Freigabe im Chat oder Issue.
- Bestehende Resource-Manager-Stack-Variablen und Stack-Konfiguration.
- Lokale, nicht versionierte Operator-Shell für reale OCIDs.
- OCI Vault für Secrets; nur Secret-OCIDs dürfen in passende Konfigurationen,
  niemals Secret-Werte.
- OCI DevOps BuildRun-/Deployment-Status und Release-Monitor-Kommentare.

## Nicht wiederholen

- Nicht durch breite OCI-`list`-Kommandos erraten, welche Pipeline gemeint ist,
  wenn der Releasepfad bereits dokumentierte IDs oder Variablen besitzt.
- Nicht `commit-info` als Checkout-Pinning missverstehen.
- Nicht nach einem DevOps-Timeout sofort denselben breiten Discovery-Pfad
  wiederholen.
- Nicht Resource-Manager-Stack-Variablenrefresh mit dem Release-Build-Gate
  vermischen.

## Release-Hotpath

1. `main` synchronisieren und Arbeitsbaum prüfen.
2. Merge-Commit aus GitHub bestimmen.
3. Owner-Release-Freigabe gegen genau diesen Commit prüfen.
4. OCI-DevOps-Mirror gezielt aktualisieren.
5. Commit gezielt im Mirror prüfen.
6. Build-Run commitgebunden starten.
7. BuildRun/Deployment-Status lesen oder Release Monitor nutzen.
8. Smoke-Tests auf öffentlichen, kundensicheren Endpunkten durchführen.
9. Image-Tag und Digest erfassen.
10. Separates Owner-Gate für Resource-Manager-Variablenrefresh formulieren.

## Bounded-Retry-Regel

Für einen gezielten OCI-Read oder Release-Start gilt:

- maximal zwei direkte Retries pro Kommando-Klasse;
- vor jedem Retry kurz begründen, was sich geändert hat;
- nach dem zweiten erfolglosen Versuch stoppen und als externen Blocker
  dokumentieren;
- keine alternative Schreibaktion starten, um den Blocker zu umgehen.

## Sanitized Evidence

Erlaubt:

- kurzer Commit-Hash;
- GitHub PR-/Issue-Link;
- BuildRun-/Deployment-Lifecycle-State;
- Image-Tag und Digest;
- Smoke-Endpunkt und HTTP-Status;
- Owner-Zeit in CET/CEST.

Verboten:

- OAuth-State, Nonce, Authorization-URL, Bearer- oder Session-Material;
- Secret-Werte, private Keys, Zertifikats-Private-Key-Material;
- echte Mandats- oder Kundendaten;
- rohe OCI-Konfiguration oder Shell-History.
