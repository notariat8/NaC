# Einmaliger operatorischer Server-Read für die Teams-403-Störung

Status: lokale Designrevision zur Owner-Review; kein produktiver Read, keine
Anmeldung, kein Token-Refresh und keine Änderung des inaktiven #756-Vertrags.

Datum: 28. September 2026. Führendes [Issue #756](https://github.com/notariat8/NaC/issues/756).
Die [bestehende Stufe-A-Spezifikation](2026-09-26-m365-bff-403-diagnostic-event-design.md)
und ihr [Folgeplan](../plans/2026-09-26-m365-bff-403-direct-server-diagnosis.md)
bleiben bis zur Review unverändert. Dieser Entwurf ersetzt weder die
historischen #739-/#632-Gates noch autorisiert er einen Providerzugriff.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-403-operator-read
leading_issue: https://github.com/notariat8/NaC/issues/756
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Privacy
  - Secrets
  - Policy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-756-OR-01
  - AC-756-OR-02
  - AC-756-OR-03
  - AC-756-OR-04
  - AC-756-OR-05
validation_commands:
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - graft check
```

## Zweck und Grenze

Der geschützte aktuelle Client-Beleg vom 25. September 2026 zeigt
`spfx_subject_available=true` und einen HTTP 403 beim synthetischen
Workbench-GET. Er beweist nicht, ob Azure vor dem BFF oder ein BFF-Zweig
antwortete. **AC-756-OR-01:** Vor neuem Code oder einer Bereitstellung wird
höchstens einmal der aktuelle Serverzustand lesend geprüft. Der bisherige
`LOCAL_INACTIVE_ONLY`-Vertrag und der produktive
`BLOCKED_NO_REFRESH_CAPABILITY`-Stopp werden nicht durch diesen Text
umgangen. Eine spätere Umsetzung benötigt einen vorwärtsversionierten,
geprüften Operator-Vertrag und eine gesonderte, exakt gebundene Freigabe.

Es gibt keinen generischen Treiber, keinen freien Azure-Suchlauf, keinen
neuen Teams-Test und keine Wiederaufnahme des terminalen #739-Laufs.

## Geschlossene Ziel- und Lesesequenz

Alle Parameter in geschweiften Klammern sind **geschützte Laufzeitbindungen**,
keine geratenen Werte: `{bound_subscription}` aus dem freigegebenen
Testziel, `{bound_component}` und `{bound_app_id}` aus eindeutig geprüfter
Azure-Metadaten-Evidence, `{bound_workspace}` aus der eindeutig verknüpften
Application-Insights-Komponente. Die Werte und die bytegenauen URI-Hashes
werden erst nach dieser lokalen Design-Review und vor jedem echten GET in
repository-externer, nur für den Operator lesbarer Evidence gebunden. Ein
abweichender Tenant, eine andere Ressourcengruppe oder ein Mehrfachtreffer
stoppt; der Vertrag darf keine freie URL akzeptieren.

**AC-756-OR-02:** Die folgende Reihenfolge ist geschlossen; jeder Schritt hat
höchstens einen GET und nur die genannten Ausgabefelder:

1. Function-Metadaten:
   `GET https://management.azure.com/subscriptions/{bound_subscription}/resourceGroups/rg-nac-bff-test/providers/Microsoft.Web/sites/func-nac-bff-test-funktion8?api-version=2025-03-01`.
   Projektion: exakte Ressourcen-ID, Typ, Name, `kind`, `state` und
   Provisionierungszustand. Ein 404 gilt nur bei zuvor belegtem exaktem
   Subscription-/Ressourcengruppen- und Leserechtsnachweis als
   Nichtvorhandensein; 401/403 oder unklare Antworten sind `UNPROVEN`.
   Dieser GET allein beweist **keinen** bereitgestellten Code- oder
   Paketstand.
2. Nur wenn die Function nachgewiesen ist: genau ein auf die Ressourcengruppe,
   `Microsoft.Insights/components`, den Namensteil `appi-nac-bff-test-` und
   höchstens zwei Treffer eingeschränkter ARM-GET:
   `GET https://management.azure.com/subscriptions/{bound_subscription}/resourceGroups/rg-nac-bff-test/resources?api-version=2021-04-01&$filter=resourceType eq 'Microsoft.Insights/components' and substringof('appi-nac-bff-test-',name)&$top=2`.
   Die lesbare URI wird vor einem echten Zugriff kanonisch percent-encodiert
   und bytegenau als einzig erlaubte Request-URI gebunden.
   Bei null oder zwei Treffern, `nextLink`, unerwartetem Ressourcentyp oder
   falschem Scope: `UNPROVEN`, kein weiterer Suchversuch. Nur Name und
   Ressourcen-ID werden übernommen.
3. Nur für genau einen passenden Treffer:
   `GET https://management.azure.com/subscriptions/{bound_subscription}/resourceGroups/rg-nac-bff-test/providers/Microsoft.Insights/components/{bound_component}?api-version=2020-02-02`.
   Die Allowlist umfasst Ressourcen-ID, `properties.AppId`,
   `properties.IngestionMode`, `properties.WorkspaceResourceId`,
   `properties.RetentionInDays`, `properties.SamplingPercentage` und
   Provisionierungszustand. `ConnectionString`, `InstrumentationKey`,
   Tokens und andere nicht erlaubte Felder dürfen weder ausgegeben,
   gespeichert noch gehasht werden. Da die API solche Felder in der Antwort
   enthalten kann, muss ihre technische Projektion **vor** diesem GET
   unabhängig nachgewiesen sein; andernfalls stoppt der Lauf hier. Die tatsächliche Verknüpfung zum
   erwarteten BFF bleibt separat zu belegen; bloße Namensähnlichkeit genügt
   nicht.
4. Bei workspace-basierter Erfassung nur für den exakt aus Schritt 3
   gebundenen Workspace:
   `GET https://management.azure.com{bound_workspace}?api-version=2025-07-01`.
   Projektion: exakte Ressourcen-ID und `properties.retentionInDays`.
   Die Workspace-ID muss ein kanonischer ARM-Ressourcenpfad ohne eigene
   Query oder Fragment und im selben Test-Scope sein. Fehlende oder für das
   Belegfenster unzureichende Aufbewahrung stoppt vor der Log-Abfrage.

Die offiziellen API-Formen sind [Web Apps Get](https://learn.microsoft.com/en-us/rest/api/appservice/web-apps/get?view=rest-appservice-2025-03-01),
[Resources List by Resource Group](https://learn.microsoft.com/en-us/rest/api/resources/resources/list-by-resource-group?view=rest-resources-2021-04-01),
[Insights Components 2020-02-02](https://learn.microsoft.com/en-us/azure/templates/microsoft.insights/2020-02-02/components)
und [Log Analytics Workspace Get](https://learn.microsoft.com/en-us/rest/api/loganalytics/workspaces/get?view=rest-loganalytics-2025-07-01).

## Einzige historische Log-Abfrage

**AC-756-OR-03:** Erst bei nachgewiesener Zielidentität, Erfassung,
Aufbewahrung und Leseberechtigung ist genau ein GET an
`https://api.applicationinsights.io/v1/apps/{bound_app_id}/query` zulässig.
Sein URL-Parameter `query` enthält ausschließlich diese vor dem Zugriff
bytegenau gebundene KQL-Abfrage; Roh-URL, Pfad, Request-ID und personenbezogene
Felder werden nicht zurückgegeben:

```kusto
requests
| where timestamp between (datetime(2026-09-25T10:42:03.397Z) .. datetime(2026-09-25T10:42:10.487Z))
| where url startswith "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001/workbench-snapshot"
| summarize telemetry_rows=count(), http_401=countif(resultCode == "401"), http_403=countif(resultCode == "403"), other=countif(resultCode !in ("401", "403"))
```

Das [Application-Insights-Query-GET](https://learn.microsoft.com/en-us/rest/api/application-insights/query/get?view=rest-application-insights-v1)
und das [Request-Telemetriemodell](https://learn.microsoft.com/en-us/azure/azure-monitor/app/data-model-complete)
belegen die API- und Feldform. Die Abfrage zählt nur Telemetriezeilen; Sampling,
fehlende Erfassung oder leere Ergebnisse dürfen nicht als „kein Request“
interpretiert werden. Die aktuelle BFF-Quelle belegt keine persistierte
`request_correlation_binding_sha256` für den historischen Request. Deshalb
ist selbst ein einzelner zeitgleicher 403 **keine** eindeutige Korrelation und
kein konkreter Berechtigungsgrund. Der Befund lautet dann höchstens
`TEMPORAL_STATUS_ONLY`; die Ursache bleibt `UNPROVEN`.

## Authentifizierung, Datenschutz und Stopps

**AC-756-OR-04:** Ein späterer Operatorlauf darf nur den geschützten,
vorab geprüften bestehenden Funktion8-Account und seine vorhandenen
Leserechte verwenden. Die Azure CLI ist lediglich ein möglicher Transport,
keine Freigabe und kein Nachweis für Einzel-GET, Redirect-/Retry-Sperre oder
Refresh-Grenzen. Ein technisch überprüfter Transport muss GET-only, exakte
Hosts und URIs, höchstens einen Aufruf je erlaubter Ressource, keine
Redirects, Retries, Seitenabrufe, freien Bodies oder Rohantwort-Logs
erzwingen. Kann er das nicht, bleibt der Lauf gesperrt. Ein eventuell nötiger
stiller Token-Refresh samt Cache-Write im vorhandenen Current-User-only-Speicher
ist eine **eigene ausdrücklich zu genehmigende Credential-Operation**; kein
Browserlogin, Gerätecode, Konto- oder Tenantwechsel, Tokenexport oder
Credential-Inhalt. 401/403, Authentifizierungsaufforderung, Mehrfachtreffer,
unerwartete Felder oder nicht redigierbare Antwort stoppen ohne Retry.

**AC-756-OR-05:** Dieser Entwurf erteilt null Provider-Reads, null
Credential-Writes, null Deployments, null Tenant-Writes und keinen #739-/
#632-Lauf. Nach Spec-Review folgen DE/EN-Plan, vorwärtsversionierter Vertrag,
synthetische Negativtests und lokale Validierung; vor dem ersten realen GET
werden finaler Commit/Tree, Belegpaar, Ziel, Kontoprincipal, Berechtigung,
AVV-/DPA-Basis, Transport und exakte URI-/Query-Hashes separat geprüft und
genehmigt. Wenn Stage A nur `UNPROVEN` liefert, ist die bereits geplante
interne #756-Instrumentierung der **begründete**, weiterhin separat
freizugebende Folgeweg. Die eigentliche Berechtigungskorrektur folgt erst aus
einem belegten Ablehnungsgrund.
