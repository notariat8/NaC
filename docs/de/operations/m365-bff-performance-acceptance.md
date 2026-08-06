# M365-BFF-Performance-Abnahme

Status: Issue #735 implementiert den owner-gebundenen Live-CLI- und
Kompositionspfad offline. Er bindet die reproduzierbare, noch nicht
irreversibel gesperrte WORM-Baseline, die Koordinationsinfrastruktur, Azure
Monitor, die dedizierte Blob-Lease und exakt 500 synthetische GETs an eine
einzige spätere Owner-Freigabe. In diesem Slice werden keine Azure-Ressourcen
erstellt und keine Live-Aufrufe ausgeführt.

Die maschinenlesbaren Quellen sind der
[Abnahmevertrag](../../../workflows/contracts/m365-bff-performance-acceptance.contract.json)
und der
[Verification Contract](../../../workflows/verification-contracts/m365-bff-performance-acceptance.verification.json).
Der Modus lautet exakt `endpoint_scoped_conservative_measurement`.

## Aussagegrenze

Diese Lane misst ausschließlich einen synthetischen GET-Endpunkt. Sie erhebt
keine tenantweite SharePoint-Baseline, keine tenantweite Request-Allowance und
keine tenantweite Resource-Unit-Allowance. Der Status dieser drei Aussagen ist
explizit `NOT_CLAIMED`.

Ergebnisse dürfen weder auf andere Endpunkte noch auf die SharePoint-Kapazität
des Tenants hochgerechnet werden. Azure-Monitor-Werte sind konservativ
verwendete, app-weite Deltas der gebundenen Function App. Sie sind keine
Attribution zum gemessenen Endpunkt und keine SharePoint-Kapazitätsquelle.

## Festes Ziel

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

Redirects, alternative Hosts, Klartext-HTTP, Cache-Busting und automatische
Retries sind verboten. Jede Antwort muss HTTP `200`, das exakte Wire-Schema
und höchstens `128 KiB` erfüllen. Body und Body-Hash werden nicht gespeichert.

## Fester Messplan

Ein vollständiger Lauf sendet exakt `500` synthetische GETs. Die
Phasenallokationen lauten `1, 1, 90, 120, 288`; die wiederholten Intervalle
lauten `10, 60, 300` Sekunden.

| Reihenfolge | Phase | GETs | Intervall |
| --- | --- | ---: | ---: |
| 1 | `cold_epoch_baseline` | 1 | sofort |
| 2 | `cold_epoch_candidate` | 1 | nach 1.200 Sekunden Runner-Idle |
| 3 | `endpoint_scoped_sample` | 90 | 10 Sekunden |
| 4 | `sustained_2h` | 120 | 60 Sekunden |
| 5 | `soak_24h` | 288 | 300 Sekunden |

Es gilt durchgehend Client-Concurrency `1` und ein inklusives Maximum von
`6` Target-Dispatches pro Minute. Catch-up-Bursts, parallele Phasen und das
Wiederholen abgeschlossener Phasen sind nicht zulässig. Jeder reservierte
Versuch zählt; ein unklarer In-Flight-Ausgang wird nach einem Crash nicht
erneut gesendet.
Unmittelbar vor dem HTTP-Aufruf persistiert der Runner
`transport_boundary_crossed` und erhöht
`completed_network_dispatch_count`. Ein Crash nach dem Dispatch kann dadurch
die finale Monitor-Untergrenze nicht verringern. Ziel-Drift oder ein anderer
deterministischer Fehler nach der Reservierung, aber vor dieser Grenze wird
dagegen als ein fehlgeschlagener Versuch mit null Netzwerk-Dispatches
abgeschlossen, sodass valide terminale Evidence entsteht.

Die Cold-Start-Klassifikation lautet nur dann `VERIFIED`, wenn die gebundene
Serverinstanz oder Start-Epoch nachweislich gewechselt hat. Sonst lautet sie
`INCONCLUSIVE`. Rohe Instanz- oder Epoch-Werte werden nicht gespeichert und
die Infrastruktur wird für die Messung nicht neu gestartet.

## Azure Monitor

Der Offline-Adapter liegt in
`src/nac_bff/azure_performance_monitor.py`. Er plant ausschließlich einen
read-only ARM-GET auf den festen `Microsoft.Insights/metrics`-Pfad der
gebundenen Function App. Zulässig sind exakt:

- API-Version `2023-10-01`
- Namespace `Microsoft.Web/sites`
- `OnDemandFunctionExecutionUnits`
- `OnDemandFunctionExecutionCount`
- `AlwaysReadyFunctionExecutionUnits`
- `AlwaysReadyUnits`
- `AlwaysReadyFunctionExecutionCount`
- Aggregation `Total`, Intervall `PT1M`
- kein Dimensionfilter; app-weites, ungefiltertes Rollup

Jede Metrik muss pro Teilfenster exakt eine dimensionslose `Total`-Serie
liefern. Damit bleibt der Messwert ein konservatives app-weites Rollup und
wird nicht einem Endpunkt oder einer Instanz zugerechnet. Die Fenster müssen
UTC-minutengenau sein,
pro ARM-Request zwischen `60` und `86.400` Sekunden liegen und beim Lesen seit
mindestens `300` Sekunden abgeschlossen sein. Längere Gesamtzeiträume werden
lückenlos in höchstens 24-stündige Requests zerlegt und anschließend kumulativ
gebunden. Jede zurückgegebene Serie muss das vollständige `PT1M`-Raster ihres
Teilfensters enthalten. Unbekannte Felder, fehlende oder mehrere Serien,
Dimensionswerte, doppelte Zeitstempel sowie nicht gesetzte Fenster blockieren.

Das finale gesetzte Fenster beginnt am Owner-gebundenen
`monitor_window_anchor` und muss die terminale Messung vollständig abdecken:
`monitor_window_end_utc` liegt bei oder nach `measurement_finished_at_utc`, und
`monitor_observed_at_utc` folgt erst nach Fensterende plus 300 Sekunden
Settlement. Der Abschlussnachweis bindet diese Zeitpunkte und
`monitor_settlement_delay_seconds`. Ein früheres, bereits gesetztes Fenster reicht auch bei
eingehaltenem Cap nicht aus.

Bei einem erfolgreichen Lauf muss der Monitor mindestens alle `500` GETs
zeigen. Bei einem fehlgeschlagenen Lauf ist die Untergrenze nicht die Zahl der
reservierten Versuche, sondern `completed_network_dispatch_count`: nur
tatsächlich bis zum Transport gelangte Netzwerkaufrufe werden verlangt. Ein
Token- oder Zielbindungsfehler vor dem HTTP-Aufruf kann daher mit dem Wert null
terminalisiert und die Lease trotzdem nachweisbar freigegeben werden.

Die statische Projektion des vollständigen Laufs beträgt exakt `30,000 GB-s`.
Vor jedem Dispatch wird das verbleibende Budget proportional zu den noch
offenen GETs plus höchstens `30` noch nicht gesetzten Dispatches berechnet;
dies entspricht fünf Minuten Monitor-Lag bei maximal sechs Dispatches pro
Minute. Jede Safety-Beobachtung bindet diesen konservativen
`projected_remaining_execution_units_gb_seconds`-Wert. Der innere
Messnachweis darf diese Reserve noch enthalten. Erst der äußere, nach dem
finalen Settlement erzeugte Abschlussnachweis muss den Wert exakt null binden;
die separat benannte statische Gesamtlaufprojektion bleibt `30,000 GB-s`. Das app-weite beobachtete Delta plus die Projektion der
verbleibenden GETs darf den inklusiven Cap von `120,000 GB-s` nicht
überschreiten. Alle Always-Ready-Metriken müssen exakt null sein. Der gleiche
Cap gilt nach dem finalen Settling; ein Überschreiten oder eine nicht
verfügbare Beobachtung bricht fail-closed ab.
Dies ist eine Ausführungsverbrauchsgrenze und keine monetäre Kostenschätzung.
Monetäre Kosten bleiben `NOT_CLAIMED`: Gebühren für Ausführungsanzahl,
Azure-Monitor-Abfragen oder -Ingestion, Blob-Speicher und -Transaktionen,
Netzwerk, Steuern, Guthaben, Freikontingente und aktuelle Preise sind bewusst
nicht Teil dieser Aussage.

## Exklusive Lease

Die lokale Grenze liegt in
`src/nac_bff/azure_performance_lease_broker_client.py`; der serverseitige
Broker und seine persistente State Machine liegen in
`src/nac_bff/azure_performance_lease_broker.py` und
`src/nac_bff/azure_performance_lease_broker_storage.py`. Lease-Storage,
BFF-Storage und WORM-Evidence-Storage müssen getrennt sein. Die Broker-API darf
nur diese Operationen anbieten:

1. `acquire(-1)` mit einer vorab persistent gespeicherten UUID
2. `assert_held`
3. `release`

Die persistente State Machine lautet exakt `ACQUIRE_INTENT`,
`ACQUIRE_IN_FLIGHT`, `HELD`, `RELEASE_INTENT`, `RELEASED`, `LOST`. Vor jedem
Target-Dispatch muss dieselbe Lease-ID auf demselben gebundenen Blob als
gehalten bestätigt werden. Resume setzt dieselbe Lease-ID, dieselbe
Zielbindung und dieselbe Lease-Bindung voraus.
Jedes `assert_held`-Receipt wird vor Uhr-, Monitor- oder Target-Arbeit auf
exakt `HELD`, Lease-Bindung, Zielbindung und Zustands-Hash geprüft. Ist eine
zuvor gehaltene Lease autoritativ nicht mehr vorhanden, persistiert der Broker
zuerst terminal `LOST`.

Eine verlorene oder fremde Lease sowie Binding-Drift blockieren ohne Dispatch.
Automatisches Reacquire, Lease-Break und Blob-Delete sind in Broker und lokalem
Adapter verboten. Die System-Assigned Identity der Function darf das exakt gebundene
Null-Byte-Block-Blob intern einmalig mit `If-None-Match: *` anlegen oder ein
bereits vorhandenes Blob per `HEAD` prüfen. Der Broker erzeugt die private
Azure-Lease-ID selbst und gibt weder Lease-ID, Storage-Token noch Storage-URL
an den lokalen Runner zurück. Ein Ergebnis darf
ausschließlich im dauerhaft geschriebenen Zustand
`RELEASED` den Status `PASSED` erhalten. `HELD`, ein unklarer Release-Ausgang
oder ein lediglich gesendeter Release reichen nicht aus.
Der finale Release-Receipt muss den Zustand exact `RELEASED` ausweisen; die
finale Evidence speichert ihn als `lease_release_lifecycle_state` und bindet
zusätzlich `lease_release_state_evidence_sha256`.
`target_binding_sha256` und `lease_binding_sha256` müssen zur Messung passen.
Ein Lifecycle-State-Hash ohne exakten Zustand und passende target binding ist
kein Release-Nachweis.
Zusätzlich müssen Lease-Bindung und `SHA256(lifecycle_state)` exakt zum Receipt
passen. Geht die Release-Antwort verloren und ist die Lease anschließend nicht
mehr vorhanden, wird der Zustand konservativ terminal als `LOST` persistiert;
`RELEASED` wird niemals aus dem bloßen Nichtvorhandensein abgeleitet.

Vor `acquire` muss ein kanonischer Lease-Acquisition-Safety-Nachweis die
vollständige Infrastruktur-Evidence mit Status `SAFE` validieren und deren
Koordinations-Resource-ID, Function-System-Identity und Provisioning-Caller an den exakten
`lease_binding_sha256`, die Zielbindung und das signierte Aktivierungsticket
binden. Der lokale Runner fordert ausschließlich ein App-Token für
`api://funktion8.de/nac-bff/.default` an. Der BFF akzeptiert dafür nur die feste
App-Rolle `Performance.Lease`; das höchstens 60 Sekunden gültige RS256-Ticket
bindet genau eine Operation sowie Owner, Tenant, Audience, Actor, Commit, Tree,
Function-Paket, Plan, Ziel, Blob-Pfad und Nonce. Nur die System-Assigned Identity der Function fordert
serverseitig `https://storage.azure.com/.default` an. Jede Abweichung blockiert
vor Broker-State und Storage-HTTP.
Nach einem echten Prozessneustart wird die Infrastruktur ausschließlich
read-only neu attestiert. Serialisierte Safety-Evidence allein autorisiert
nichts, weil die prozessgebundene Capability nicht serialisiert wird. Nur eine
frische Re-Attestation mit identischem Owner, Tenant, beiden Principals, Ziel und
Lease-Bindung darf die bestehende Lease reconciliieren; der alte abgelaufene
Nachweis autorisiert keine neue Mutation.

Die Offline-IaC liegt unter
`deploy/runtime/azure/nac-bff-performance-coordination`. Sie bindet die
System-Assigned Identity der Function, den davon getrennten Provisioning-Caller, Function-Paket,
Ticket-Zertifikat und die autoritative Function-Ressourceninstanz. Am
Storage-Endpunkt ist ausschließlich diese exakte Ressourceninstanz erlaubt; die
Netzwerk-Defaultregel ist `Deny`. Shared Keys, öffentliche Blobs sowie Delete-,
Owner- und Container-DataActions bleiben ausgeschlossen. Nur die System-Assigned Identity der Function
erhält am exakten Container und Blob-Pfad `blobs/read` und `blobs/write`; der
lokale Caller erhält keine Storage-DataAction. Da Azure `write` auch Overwrite
und Lease-Break umfasst, erzwingen ABAC und die feste Broker-API gemeinsam die
engere Operationsgrenze. Vor Acquire werden außerdem die exakte
`Performance.Lease`-Zuweisung und der hashgebundene Function-Settings-Satz
gesetzt und ohne Ausgabe seiner Werte zurückgelesen.
Die ID der Rollenzuweisung ist stabil an die autoritative Function-Ressourcen-ID
gebunden, während ihr Principal aus der aktuellen System-Assigned Identity
aufgelöst wird. ARM erlaubt die erst zur Deploymentzeit aufgelöste Principal-ID
nicht als Bestandteil des Rollenzuweisungsnamens. Ein Identitätswechsel ist
deshalb bewusst fail-closed: Azure darf eine bestehende Rollenzuweisung nicht
auf einen anderen Principal aktualisieren. Der effektive RBAC-Readback indexiert alle
sichtbaren Rollenzuweisungen an jedem geprüften Vorgängerscope, nicht nur die
Zuweisungen des erwarteten Principals. Eine zurückgebliebene Zuweisung derselben
Broker-Rolle an die Runtime-UAMI oder an eine frühere Function-Systemidentität
blockiert den Lauf. Sie wird weder automatisch gelöscht noch zurückgerollt;
vor einer Neuzuweisung nach Identitätsrotation erfordert ihre Entfernung eine
separat owner-freigegebene und evidenzgebundene Bereinigung.
Die bestehende User-Assigned Identity der Function bleibt getrennt für Graph,
Host-Storage und Application Insights gebunden; sie erhält keine Lease-Rolle.

## Owner-Gate und Evidence

Die kombinierte Infrastruktur- und Live-Abnahme braucht genau eine
Owner-Freigabe. Vor der Provisionierung bindet sie alle deterministischen
Eingaben:

- `approved_commit_sha`
- `approved_tree_sha`
- `toolchain_attestations_sha256`
- `contract_sha256`
- `phase_plan_sha256`
- `measurement_policy_sha256`
- `monitor_policy_sha256`
- `lease_policy_sha256`
- `lease_bootstrap_policy_sha256`
- `infrastructure_safety_policy_sha256`
- `infrastructure_source_sha256`
- `infrastructure_parameters_sha256`
- `infrastructure_binding_sha256`
- `worm_baseline_binding_sha256`
- `worm_baseline_compiled_arm_sha256`
- `worm_baseline_parameters_sha256`
- `worm_baseline_source_sha256`
- `deployment_sequence_sha256`
- `target_binding_sha256`
- `expected_activation_hash`
- `correlation_id`
- `monitor_window_anchor_utc`
- `monitor_window_anchor_sha256`

`infrastructure_source_sha256` bindet sowohl Bicep-Quellen als auch die mit
Bicep `0.45.15.27210` kanonisch kompilierten ARM-/Parameter-Artefakte. CI muss
beide Artefakte bytegenau reproduzieren; der spätere Live-Pfad verwendet nur
diese gebundene Ausgabe.

Die WORM-Baseline wird vor der Koordinationsinfrastruktur in derselben
Resource Group `rg-nac-bff-test` angelegt und anschließend read-only
abgeglichen. Der gebundene Ablauf darf keinen irreversiblen Immutability-Lock
setzen. Ein solcher Lock bleibt eine eigene spätere Governance-Entscheidung.

Der UTC-minutengenaue `monitor_window_anchor` begrenzt den frühesten
Monitorzeitpunkt. Unmittelbar vor dem ersten Lease- oder Monitor-Netzwerkzugriff
werden Commit, Tree, Toolchain, Contract, Infrastrukturquellen und Parameter
aus den tatsächlichen Quellen neu gemessen. Drift blockiert vor Netzwerk.
Die TOCTOU-Grenze bleibt während der Ausführung aktiv: Unmittelbar vor jedem
Target-Dispatch wird die Zielbindung geprüft und unmittelbar vor jedem
Subprozess wird die versiegelte Azure-CLI-Toolchain neu gemessen. Die
Zielbindung wird nach der Tokenbeschaffung erneut geprüft; der Request wird
ausschließlich aus dem zuvor erfassten und gebundenen Endpoint konstruiert. Die
Monitor-Command-Grenze akzeptiert nur argv-basiertes
`az rest --method get` mit der exakt vom read-only Adapter erzeugten
kanonischen URL. Body, abweichende Methode, umsortierte Query oder zusätzliche
Query-Parameter blockieren. Jeder Monitor-Read verbraucht vor Token- und
Netzwerkzugriff eine eigene, owner- und policy-gebundene Capability; höchstens
`2048` Reads sind erlaubt. Dieses Budget ist vom dauerhaften 500-GET-Ledger
getrennt. Der generische Azure-CLI-Adapter lehnt Monitor-Metrik-URLs ab; nur
die dedizierte konsumierende Monitor-Methode darf sie ausführen. Target-GET,
Blob-Bootstrap und Lease-Acquire verbrauchen ihre Capability jeweils vor
Tokenbeschaffung oder State-Persistenz. Delegierte M365-Tokens werden vor der
Versiegelung kryptografisch gegen Entra-RS256, Ressource und Scopes validiert.
Die Parameter binden zusätzlich den exakten Tenant, die Subscription, die
Resource Group `rg-nac-bff-test`, den Modus `Incremental`, die Region
`germanywestcentral` und den kanonischen effektiven Tag-Satz aus Owner-Tags
plus den sieben unveränderlichen NaC-Koordinationstags.
Die tatsächlichen Resource-IDs des bestehenden BFF-Storage und des
WORM-Evidence-Storage sind ebenfalls vorab gebunden. Die Namensprüfung vor dem
Deployment muss belegen, dass das Koordinationskonto noch nicht existiert. Ein
erfolgreicher Erstlauf persistiert diesen ursprünglichen
`nameAvailable=true`-Receipt unveränderlich vor dem ersten Deployment und einen
exakten `Succeeded`-Deployment-Receipt unmittelbar nach dem
Koordinationsdeployment. Bei einem Neustart mit vollständigem Receipt-Paar wird
vor jeder Provider-Mutation ein frisches GET desselben deterministischen
Deployments geprüft. Owner-, Ziel-, Quell-, Parameter- und Hashbindungen müssen
übereinstimmen; es erfolgen dabei exakt null Namensprüfungen und null
Deployment-Creates. Danach werden die vollständigen Safety-Readbacks frisch
wiederholt. `Running`, `Failed`, fehlende, ersetzte, unvollständige, manipulierte
oder abweichende Receipts blockieren. Liegt nach einem Absturz nur der
ursprüngliche Namens-Receipt vor, darf der Fresh-Name-Pfad ausschließlich nach
einer neuen aktuellen Prüfung mit `nameAvailable=true` fortgesetzt werden;
andernfalls wird ohne Redeployment blockiert. Der historische Receipt allein
autorisiert nie ein Deployment. Es gilt strikt
`original observed < started <= completed < current reconciliation observed`.
Ein
getrennter Readback nach dem Deployment muss dessen exakte Resource-ID, Region,
effektive Tags und die vollständige Storage-/Netzwerkkonfiguration bestätigen:
öffentlicher Netzwerkzugriff aktiviert, Default `Deny`, Bypass `None`, keine
IP- oder VNet-Regel, genau eine tenantgebundene Resource-Access-Regel für die
gebundene Function-Ressourceninstanz, keine Shared Keys
oder öffentlichen Blobs, TLS 1.2 und ausschließlich HTTPS. Der Blob-Service muss
Versionierung sowie Blob- und Container-Löschaufbewahrung deaktiviert haben. Der
Lease-Container muss `publicAccess=None` und exakt die gebundenen Metadaten für
Schema, synthetische Klassifikation, Lock-Pfad, Blob-Typ, Bootstrap,
Autorisierungsgrenze und Principal-Trennung tragen. Namensprüfung, gebundener
Deployment-Receipt und Post-Deployment-/RBAC-Readback müssen in dieser
Reihenfolge liegen und dieselbe Owner-Bindung sowie denselben einmaligen Nonce
tragen. Der Nonce wird intern erzeugt und gegen Wiederverwendung gesperrt. Alle
Readbacks binden die tatsächliche versiegelte ausführbare Datei, argv, Toolchain
und Laufsitzung; die vertrauenswürdige Prüfzeit wird intern erzeugt. Der
Pre-Deployment-Nachweis darf höchstens 30 Minuten, jeder Post-Deployment- und
RBAC-Nachweis höchstens fünf Minuten alt sein; mehr als 30 Sekunden
Zukunftsdrift blockieren. Nach dem Deployment muss der vollständige effektive RBAC-/ABAC-Readback
beim zum Owner-Tenant passenden Tenant-Root beginnen und
eine autoritative, geordnete Management-Group-Abstammung der Subscription
belegen. Er umfasst Tenant-Root, Management-Group-Kette, Subscription, Resource Group, Storage-Konto,
Blob-Service und Container genau die gebundene Provisioner-Identität sowie alle
transitiven Entra-Gruppen, Rolle, DataActions, Bedingung und Scope zeigen. Jede
breitere direkte, gruppenbasierte oder geerbte Data-Plane-Zuweisung sowie jede
effektive Control-Plane-Zuweisung blockiert Bootstrap und Lease-Acquire.
Ein vom Aufrufer abweichend gewählter Azure-Scope blockiert vor Netzwerk; das
Bicep-Template bricht zusätzlich ab, wenn tatsächlicher Tenant, Subscription
oder Resource Group von den gebundenen Parameterwerten abweichen.

Die Freigabe erlaubt genau die hashgebundene Custom-Role-Definition und
-Zuweisung aus diesem Infrastrukturplan. Credential-Änderungen und jede andere,
nicht durch Quellen-, Parameter- und Infrastruktur-Hash gebundene
Rechteänderung bleiben verboten.

Der reale ETag und daraus abgeleitete `lease_binding_sha256` entstehen erst
beim gebundenen Bootstrap-Readback. Sie müssen vor dem ersten Target-Dispatch
in State und Evidence übernommen werden. Jede deterministische Abweichung
blockiert vor dem Netzwerkzugriff; jeder Readback-Drift blockiert vor dem
Messlauf. Monitor-, Lease- und Infrastrukturbindung sind voneinander und von
WORM-Evidence getrennt.
Das Offline-Gate liefert bewusst nur `owner_execution_bindings`. Erst der
kanonisch validierte `SAFE`-Readback ergänzt
`infrastructure_safety_evidence_sha256` und bildet damit vollständige
Runtime-Execution-Bindungen. Die Komposition nach dem Bootstrap bindet
zusätzlich `lease_binding_sha256` und
`lease_acquisition_safety_evidence_sha256`. Sie muss vor Lease-Acquire exakt
bestätigt sein; vom Aufrufer gelieferte Hashes werden nie ungeprüft in finale
Evidence übernommen. Unmittelbar nach dem vollständigen Readback werden
Commit, Tree, Contract, Toolchain, Infrastrukturquellen und Parameter erneut
gemessen; Drift blockiert noch vor Lease-Acquire. Ein nicht blockierend erworbener lokaler Prozess-Fence
umfasst den vollständigen Mess- und Finalisierungslebenszyklus eines State-Pfads.
Ein zweiter Prozess blockiert daher vor Owner-Prüfung und Netzwerkzugriff.
Der öffentliche Readback-Adapter erzeugt die verifier-fertigen ARM-, Graph- und
Effective-RBAC-Envelopes selbst aus festen Allowlist-Aufrufen. Seine Umgebung ist
bereinigt und gebunden; das ausführbare Azure-CLI-Binary wird unmittelbar vor
jedem Subprozess erneut gemessen. Private, handgefertigte Evidence ist kein
zulässiger Produktionspfad.

Die Mess-Engine erzeugt zunächst nur einen Nachweis mit
`final_acceptance_scope: MEASUREMENT_ONLY_LEASE_RELEASE_PENDING`. Erst der
Runtime-Wrapper darf nach einem unabhängig bestätigten Zustand `RELEASED` den
finalen Nachweis `nac.m365-bff-performance-final-evidence/v1` mit Status
`PASSED` erzeugen. Das terminale Messergebnis wird vor dem finalen Monitor-Read
als `nac.m365-bff-performance-terminal-measurement/v1` persistiert. Ein
fehlgeschlagener oder noch nicht gesetzter Monitor-Read erhält daher Checkpoint
und gehaltene Lease; beim Resume wird nur der finale Monitor-Read wiederholt,
nicht Owner-Preflight, Acquire, Runner oder Target-Traffic. Nach erneuter
Validierung von Settled-Window-Abdeckung, Monitor-Attestation, Ziel- und
Hashbindungen sowie dem auf null projizierten Restbudget wird vor dem Release
ein dauerhafter
`nac.m365-bff-performance-pending-finalization/v1`-Datensatz geschrieben. Ein
früher Cleanup-Release wird analog zuerst durch einen atomaren
`nac.m365-bff-performance-release-recovery/v1`-Checkpoint gebunden. Nach einem
Prozessneustart wird dieser Checkpoint vor jedem neuen Acquire reconciliiert
und erst nach einem exakten `RELEASED`-Receipt gelöscht. Ein
autoritativer Checkpoint wird mit `O_NOFOLLOW` geöffnet und anhand desselben
Dateideskriptors per `fstat` geprüft; atomare Ersetzungen verwenden einen zuvor
auf Eigentümer und Modus geprüften Verzeichnisdeskriptor. Symlinks oder unsichere
Elternverzeichnisse blockieren. Ein
crash-sicherer Resume darf den Release nur mit derselben Lease-ID und exakten
Zielbindung reconciliieren; Acquire, Monitor-Read und Target-Dispatch bleiben
verboten. Die terminal finalization verlangt einen Receipt mit exact
`RELEASED`. Wirft der Runner an einem sauberen Checkpoint eine Exception,
bleibt dieselbe Lease gehalten, bis der Runner fortsetzt oder diesen Checkpoint
dauerhaft als `FAILED` terminalisiert; der Wrapper gibt die Lease nie vorher
frei und lässt keinen fortsetzbaren Messzustand zurück. Der finale
Monitor-Nachweis muss für `PASSED` mindestens die 500 gebundenen
On-Demand-Ausführungen und für `FAILED` mindestens den verschachtelten,
dauerhaften `completed_network_dispatch_count` enthalten. Die finale
Validierung bindet diese abgeleitete Untergrenze und den verschachtelten
Messstatus an die finale Monitor-Attestation. JSON und Markdown werden erst
danach jeweils atomar mit Verzeichnis-`fsync` geschrieben. Ein zuletzt
geschriebenes `nac.m365-bff-performance-completion-manifest/v1` bindet die
exakten Hashes beider Dateien und den finalen Evidence-Hash und ist der alleinige
Commit-Punkt; ohne gültiges Manifest existiert keine finale Evidence. Der
Pending-Datensatz wird erst nach diesem Manifest gelöscht. Ein Crash zwischen terminalem
Messende und finaler Persistenz kann damit weder einen falschen finalen PASS
hinterlassen noch Test-Traffic wiederholen.
Die 500er-Untergrenze gilt nur für `PASSED`. Ein früh abgebrochener, gültiger
`FAILED`-Lauf verlangt mindestens seine tatsächlich dispatchten Versuche im
finalen Monitor-Read, gibt dieselbe Lease dennoch dauerhaft frei und schreibt
redigierte finale Fehler-Evidence.
Ein späterer Aufruf wiederholt zuerst den aktuellen owner-gebundenen und den
Infrastruktur-Safety-Preflight. Erst danach validiert und liefert er die fertige
finale Evidence ohne Lease-, Monitor- oder Target-Netzwerkaktionen zurück.

Evidence enthält nur redigierte Aggregate, die Gate- und Readback-Bindungen, die
app-weiten Monitor-Deltas, das verbleibende Projektionsbudget,
Phasenaggregate, Abort-Code und den finalen Lease-Zustand. Die Aussage
`tenant-wide SharePoint baseline: NOT_CLAIMED`,
`tenant-wide SharePoint request allowance: NOT_CLAIMED`,
`tenant-wide SharePoint resource-unit allowance: NOT_CLAIMED` und
`monetary cost: NOT_CLAIMED` bleiben darin ausdrücklich erhalten.
Einzelrequests, rohe Antworten, URLs, Header, Bodies, Tokens,
Tenant-/Benutzer-/Instanz-/Epoch-Werte und die rohe Lease-ID sind verboten.

## Live-Grenze

Der bestehende Planbefehl bleibt offline und sendet null Requests:

```text
nac m365 teams-sharepoint bff-performance-acceptance-plan
```

Dieser PR führt keine Live-Aktion aus: keine Azure-Ressourcenaktion, keine
Blob-/Lease-Mutation, keinen Monitor-Read und keinen Target-Dispatch. Der
implementierte Live-CLI-Pfad
`nac m365 teams-sharepoint bff-performance-acceptance` bleibt durch die beiden
jeweils genau einmal erforderlichen Flags `--owner-approved` und
`--execute-live-acceptance` sowie das unveränderliche Owner-Gate geschlossen.
Er wird erst nach einer frischen hashgebundenen Owner-Freigabe ausgeführt.
Direkte Adapteraufrufe blockieren vor Token-, Netzwerk- oder State-Zugriff,
wenn nicht die exakte begrenzte Capability aus unveränderlicher
Owner-Kommentar- und versiegelter Infrastruktur-Safety-Verifikation vorliegt;
jeder Blob-Aufruf, Monitor-Read und Target-GET benötigt diese frische
owner-gebundene Capability.
