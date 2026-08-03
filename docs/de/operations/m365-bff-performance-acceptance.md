# M365-BFF-Performance-Abnahme

Status: Offline-Plan, Safety-Runtime und Verification Contract implementiert;
die Microsoft-365-/Azure-Preflight-Adapter und der Live-CLI-Befehl bleiben
fail-closed und Owner-gated.

Dieser Standard definiert eine kapazitätsgebundene Abnahme-Lane für den
aktivierten M365-BFF-Read-Endpunkt. Die maschinenlesbare Quelle ist
[m365-bff-performance-acceptance.contract.json](../../../workflows/contracts/m365-bff-performance-acceptance.contract.json),
der Verification-Harness steht in
[m365-bff-performance-acceptance.verification.json](../../../workflows/verification-contracts/m365-bff-performance-acceptance.verification.json).

## Feste Route

Das fachliche Ziel ist unveränderlich:

| Feld | Exakter Wert |
| --- | --- |
| Schema | `https` |
| Host | `func-nac-bff-test-funktion8.azurewebsites.net` |
| Methode | `GET` |
| Workspace | `notary_team_01` |
| Akte | `NAC-SYN-MATTER-001` |
| Pfad | `/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001/workbench-snapshot` |
| Query | `purpose=view_synthetic_matter_workspace` |
| Wire-Schema | `nac.workbench.snapshot/v1` |

Redirects, alternative Ziele, Klartext-HTTP und Cache-Busting-Änderungen sind
verboten. Jede versandte Anfrage muss exakt HTTP `200` erhalten, als
`nac.workbench.snapshot/v1` validieren und darf höchstens `128 KiB` groß sein.
Bodies werden im Speicher validiert und niemals aufbewahrt.
Dabei verwendet der Transport denselben kanonischen Exact-Shape-Validator wie
die serverseitige Workbench-Projektion. Unbekannte Top-Level- oder
verschachtelte Felder führen zum Abort. Der gehashte Instanz-Epoch-Header wird
nur bei einer erfolgreichen Antwort auf genau diese feste Workbench-Route
ausgegeben, nicht auf Health-, Auth- oder Fehlerantworten.

## Kapazitäts-Preflight

Die Live-Ausführung ist `BLOCKED`, solange keine aktuelle autoritative Evidence
den SharePoint-Service-Tier des Tenants identifiziert und sowohl dessen
Anfragen-Allowance als auch dessen Resource-Unit-Allowance verifiziert.
Schätzungen, Defaults und abgeleitete Tiers sind keine autoritative Evidence.

Der Preflight misst außerdem die Baseline-Last des Tenants für Anfragen und RU
und leitet die Testallokation aus einer konservativen RU-Obergrenze pro Anfrage
ab. Baseline plus geplante Testlast müssen in jedem durch den autoritativen Tier
definierten Allowance-Zeitfenster bei höchstens `50 %` beider verifizierter
Allowances bleiben. Die niedrigere resultierende Rate begrenzt jede Phase.
Evidence, die älter als 24 Stunden, an einen anderen Tenant/Workspace gebunden
oder ohne verfügbare Allowance ist, lässt den Status auf `BLOCKED`.
Die autoritative Bescheinigung wird vor jedem Target-Dispatch sowie nach jeder
Idle-Phase erneut gelesen und validiert. Das Owner-Gate bindet den initial
freigegebenen Hash; Zustand und Abschluss-Evidence binden zusätzlich den
jeweils letzten gültigen Hash. Eine erneuerte Bescheinigung darf die
freigegebenen Kapazitätsgrenzen nicht verändern.

Der Azure-Preflight liest Azure Monitor und verlangt:

- `AlwaysReadyUnits=0`
- prognostizierte und beobachtete Execution Units der Abnahme höchstens am
  inklusiven Cap von `120.000 GB-s`
- fortlaufende Monitor-Verfügbarkeit während und nach dem Lauf

Dies sind Read-only-Prüfungen. Sie erlauben keine Kapazitäts-, Berechtigungs-,
Konfigurations- oder Infrastrukturänderung.
Azure-Monitor-Evidence besitzt einen eigenen Quellen-Hash und wird nicht als
SharePoint-Kapazitätsquelle ausgegeben.

## Globales Dispatch-Budget

Für alle Phasen gilt exakt ein inklusives globales Limit:

```text
maximale Target-Dispatches = 50.000
```

Ein erfolgreicher vollständiger Abnahmelauf verbraucht exakt diese gebundene
Allokation; wenn der Kapazitäts-Preflight sie nicht sicher zulässt, bleibt der
Lauf `BLOCKED`. Jeder Target-Versuch zählt,
einschließlich Versuchen mit Timeout, Authentifizierungsfehler, Redirect,
Throttling oder Abort. Vor dem Netzwerkversand wird atomar eine Sequenz
reserviert. Wenn die nächste Sequenz `50.000` überschreiten würde, wird keine
Anfrage gesendet.

Client-Retries und automatisches Folgen von Redirects sind deaktiviert. Es gibt
weder eine unbedingte Phase mit 50.000 Anfragen noch die unbedingte Vorgabe,
50.000 Anfragen innerhalb von zwei Stunden abzuschließen.

## Phasen

Der owner-gebundene Phasenplaner allokiert alle Phasenbudgets vorab. Ihre Summe
darf höchstens `50.000` betragen; jede Rate wird durch die verifizierten
50-%-Allowances für Anfragen und RU begrenzt.

| Phase | Sicherheitsgebundenes Verhalten |
| --- | --- |
| `cold_epoch_baseline` | Exakt eine gebundene Baseline-Anfrage senden. |
| `cold_epoch_candidate` | 20 Minuten Runner-Idle-Zeit beobachten, danach exakt eine Anfrage senden; Infrastruktur nicht neu starten. |
| `capacity_bounded_volume` | 37.758 Dispatches mit höchstens einer Anfrage/Sekunde und maximal zwölf aktiven Stunden ausführen. |
| `sustained_2h` | Höchstens zwei aktive Stunden mit maximal 1,5 Anfragen/Sekunde ausführen. |
| `soak_24h` | Höchstens 24 aktive Stunden, nicht schneller als eine Anfrage/Minute und mit höchstens 1.440 Dispatches ausführen. |

Die akzeptierte Fehlerrate beträgt `0 %`. Für jede Anfrage gilt eine
Latenzobergrenze von `20.000 ms`. Volume- und Sustained-Phase verlangen p95
höchstens `2.000 ms` und p99 höchstens `5.000 ms`; für Soak gelten p95 höchstens
`1.500 ms` und p99 höchstens `3.000 ms`. Diese Metriken bleiben reine
Aggregate.

Die Phasen laufen nacheinander und verwenden keine Catch-up-Bursts. Ein
restart-sicherer Zustand persistiert die globale Sequenz, verbrauchte
Allokation sowie alle Vertrags-, Aktivierungs-, Ziel-, Kapazitäts- und
Phasenplan-Hashes. Jeder Checkpoint wird vor dem nächsten Dispatch dauerhaft
geschrieben, per SHA-256-Sidecar gebunden und unmittelbar zurückgelesen. Beim
Neustart ist ausschließlich dieser Store die Resume-Quelle. Ein Resume darf
keine Zähler verringern, keine Sequenz
wiederverwenden und keine freigegebene Allokation erhöhen.
Ein fataler Response-Zustand wird vor der Terminalisierung persistiert. Nach
einem Crash wird dieser Zustand ohne weiteren Target-Dispatch als fehlgeschlagen
terminalisiert.

## Cold-Start-Klassifikation

Die 20-minütige Idle-Beobachtung allein weist keinen Plattform-Cold-Start nach.
`cold_start_classification` ist nur dann `VERIFIED`, wenn autoritative
Server-Telemetrie beweist, dass sich die Serverinstanz oder die Server-Start-
Epoch zwischen gebundener Baseline und gemessener Anfrage geändert hat.

Wenn diese Änderung fehlt, unverändert, nicht verfügbar oder nicht beweisbar
ist, lautet die einzig zulässige Klassifikation `INCONCLUSIVE`. Rohe Instanz-
und Start-Epoch-Werte werden niemals aufbewahrt. Die Infrastruktur wird nicht
neu gestartet, um ein Ergebnis zu erzwingen.

## Abort-Verhalten

Die Lane bricht ohne Retry ab bei:

- Authentifizierungsfehler oder Challenge
- jeder Redirect-Antwort oder jedem `Location`-Signal
- jedem Throttle-Status oder Throttle-Signal
- Drift bei Schema, Host, Port, Pfad, Query, DNS, Zertifikat oder Target-Binding
- Status ungleich `200`, Schemafehler oder Antwort über `128 KiB`
- Überschreitung der Anfrage- oder aggregierten Phasen-Latenzschwelle
- ausgeschöpftem globalem Dispatch-, verifiziertem Anfragen-/RU- oder Azure-Execution-Unit-Budget
- veralteter oder nicht verfügbarer Kapazitäts- oder Azure-Monitor-Evidence
- beschädigtem Zustand oder fehlgeschlagener Evidence-Redaktion

Ein Abort löst keinen Rollback, keine Löschung, Berechtigungs- oder
Credential-Änderung und keinen Infrastruktur-Neustart, keine Skalierung oder
Umkonfiguration aus.
Kapazitäts- und Azure-Monitor-Abbrüche werden vor einem möglichen Resume als
terminale fehlgeschlagene Phase persistiert. Scheitert die Prüfung vor der
ersten Monitor-Beobachtung, bleiben ausschließlich die beiden Monitor-Aggregate
im Fehlerartefakt `null`; ein `PASSED`-Artefakt darf niemals Nullwerte enthalten.

## Aggregierte Evidence

Die Evidence besteht aus redigiertem JSON und semantisch entsprechendem
Markdown und enthält ausschließlich Aggregate: Phasenzähler und -metriken,
globalen Dispatch-Zähler, genutzte Anteile der verifizierten Allowances, Azure
Execution Units, Always Ready Units, Cold-Start-Klassifikation, den booleschen
Instanz-/Epoch-Wechsel, Hashbindungen, den finalen Checkpoint-Hash und einen
Abort-Reason-Code. Der Evidence-Writer akzeptiert ein Artefakt nur, wenn seine
Aggregate semantisch zum finalen, unmittelbar zurückgelesenen Checkpoint passen.

Die Evidence speichert keinen Einzelrequest-Datensatz, rohe Header, Bodies,
Body-Hashes, URLs, Pfade, Hosts, Queries, Tokens, Cookies, Credentials,
Tenant-IDs, Benutzer-IDs, Serverinstanz-IDs, Start-Epochen,
Provider-Antworten oder Azure-Monitor-Antworten. Unbekannte Evidence-Felder
führen zur Ablehnung des Artefakts.

## Aktivierungs- und Owner-Gate

Der Offline-Planbefehl ist implementiert:

```text
nac m365 teams-sharepoint bff-performance-acceptance-plan --expected-activation-hash <sha256> --format json
```

Ein künftiger Live-Befehl bleibt an redigierte Aktivierungs-Evidence mit
finalem Status exakt `PASSED` gebunden. Die Owner-Freigabe bindet Aktivierung,
Vertrag, festes Ziel, Kapazitäts-Preflight, Phasenplan und Correlation-ID. Der
Aktivierungs-Receipt muss außerdem der aktuellen Azure-BFF-Bindung entsprechen:
Function-Host, Workspace und synthetische Akte werden gegen das feste
Performance-Ziel geprüft. Ein erfolgreiches Abschlussartefakt ist nur für den
kanonischen Phasenplan mit exakt `50.000` Target-Dispatches zulässig. Der
geplante Befehlsname lautet:

```text
nac m365 teams-sharepoint bff-performance-acceptance
```

Er wird erst nach Implementierung der drei Live-Preflight-Adapter aktiviert.
Der Safety-Runtime ruft Owner-/Aktivierungsverifier, Kapazitätsprovider,
Runtime-Monitor und den exakten Fixed-Transport-Verifier selbst auf; fertige
caller-konstruierte Freigabe- oder Kapazitätsobjekte akzeptiert `run()` nicht.
Fehlende oder
abweichende Aktivierungs-, Owner-, Kapazitäts- oder Zielbindungen blockieren
vor jedem Target-Dispatch.
