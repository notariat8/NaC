# Interner BFF-Diagnoseeintrag für den Teams-403

Status: Serverdiagnose-Designrevision und DE/EN-Folgeplan freigegeben; Stufe A und die lokale, inaktive Vorbereitung der Stufe B sind zur Review in Arbeit. Inaktive v1-Umsetzung in [Draft-PR #757](https://github.com/notariat8/NaC/pull/757) veröffentlicht, nicht aktiviert oder bereitgestellt.

Datum: 26. September 2026

Führendes Issue: [#756](https://github.com/notariat8/NaC/issues/756); historischer Bezug: [#748](https://github.com/notariat8/NaC/issues/748)

Ausgangsstand: `main`-Commit `862c87e1e378657f0066faed1bd36b830be2146d`
auf Branch `codex/756-bff-403-diagnostic-event`. Diese neue
Vorwärtsspezifikation ergänzt die [historische Request-Log-Triage](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/docs/de/superpowers/specs/2026-09-25-m365-bff-request-log-triage-design.md), ohne deren Belege,
Vertrag oder Freigabestatus zu verändern.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-403-diagnostic-event
leading_issue: https://github.com/notariat8/NaC/issues/756
plan: docs/de/superpowers/plans/2026-09-26-m365-bff-403-diagnostic-event.md
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Privacy
  - Secrets
  - Policy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-748-BD-01
  - AC-748-BD-02
  - AC-748-BD-03
  - AC-748-BD-04
  - AC-748-BD-05
  - AC-748-BD-06
validation_commands:
  - python scripts/validate_m365_bff_403_diagnostic_event.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python -m unittest discover -s tests -p test_nac_bff_workbench_endpoint.py
  - python -m unittest discover -s tests -p test_nac_bff_azure_function_host.py
  - python -m unittest discover -s tests -p test_nac_bff_403_diagnostic_event.py
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
```

Der Traceability-Block, die sechs bestehenden ACs und der verlinkte
Implementierungsplan gelten **nur für die veröffentlichte inaktive v1**. Der
Plan bindet die frühere Spec-Freigabe an einen älteren Commit. Die unten
beschriebene Stufe A/B ist eine neue Designrevision, keine Ausweitung dieser
Freigabe. Der Owner hat diese Revision auf Commit
`a76a1a0e9769cdf7f775e73d0812367ad408c066` und Tree
`6d95fea5fbc2038068eda0602ca06693e0e47cc4` als Grundlage für den
DE/EN-Folgeplan freigegeben. Der Folgeplan ist inzwischen freigegeben;
die aktuelle Umsetzung ist auf einen inaktiven, vorwärtsversionierten
Stufe-A-Vertrag, Validator, synthetische Tests und ein fail-closed Read-Gate
begrenzt. Die anschließende Owner-Entscheidung erlaubt zusätzlich die ausschließlich
lokale, inaktive Vorbereitung der Stufe B zur Review. Der neue
[Stufe-B-Vertrag](../../../../workflows/verification-contracts/m365-bff-403-terminal-reason.verification.json)
bindet diese Vorbereitung; ein Diagnose-Sink, Providerzugriff, Deployment und
eine neue Teams-Beobachtung bleiben gesperrt. Der
[v1-Vertrag](../../../../workflows/verification-contracts/m365-bff-403-diagnostic-event.verification.json)
bleibt unverändert.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-403-direct-server-diagnosis
leading_issue: https://github.com/notariat8/NaC/issues/756
plan: docs/de/superpowers/plans/2026-09-26-m365-bff-403-direct-server-diagnosis.md
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Privacy
  - Secrets
  - Policy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-756-SD-01
  - AC-756-SD-02
  - AC-756-SD-03
  - AC-756-SD-04
  - AC-756-SD-05
validation_commands:
  - python scripts/validate_m365_bff_403_direct_server_diagnosis.py
  - python scripts/validate_m365_bff_403_terminal_reason.py
  - python -m unittest discover -s tests -p test_nac_bff_403_terminal_reason.py
  - python -m unittest discover -s tests -p test_nac_bff_live_graph_ports.py
  - python -m unittest discover -s tests -p test_nac_bff_workbench_endpoint.py
  - python -m unittest discover -s tests -p test_nac_bff_403_direct_server_diagnosis.py
  - python -m unittest discover -s tests -p test_nac_bff_403_diagnostic_event.py
  - python -m unittest discover -s tests -p test_nac_bff_live_synthetic_workspace.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
  - git diff --check
```

Der neue Validator und der Stufe-A-Test sind Teil der freigegebenen lokalen
Umsetzung. Ihre Existenz oder ein lokaler Testerfolg autorisiert keinen
realen Provider-Read; dessen Ziel-, Account-, Principal-, Berechtigungs-,
AVV-/DPA- und No-Refresh-Nachweis bleibt separat zu prüfen.

## Zweck und Evidenzgrenze

Die vorhandenen Clientbelege zeigen eine verfügbare SPFx-Benutzerkennung und
HTTP 403 für den gebundenen Workbench-GET. Sie belegen nicht, ob die Azure-
Plattform oder welcher Python-Zweig die Antwort erzeugt hat. Der
[Workbench-Endpunkt](../../../../src/nac_bff/workbench_endpoint.py) fasst
Scope-Abweichung, Fehler des Access-Decision-Ports und ungültige oder
verweigerte Zugriffsentscheidung zur gleichen öffentlichen Meldung
`ACCESS_DENIED` zusammen. Das ist eine gewollte Informationsgrenze.

Die Diagnose beginnt **serverseitig mit vorhandenem Zustand**, nicht mit einer
weiteren SPFx-Änderung: zuerst den tatsächlich laufenden BFF und dessen
bestehende Request-Telemetrie eindeutig binden. Nur wenn diese Evidence die
Ablehnung nicht zuordnen oder erklären kann, wird der bereits inaktive Eintrag
aus [Draft-PR #757](https://github.com/notariat8/NaC/pull/757) für eine
**spätere, separat genehmigte neue Reproduktion** präzisiert. Der bisherige
Eintrag ist weder bereitgestellt noch ein Berechtigungsfix: Eine bloße Klasse
`ACCESS_DECISION_REJECTED` liefert noch keinen konkreten Graph-, Daten- oder
Rollengrund. Der historische Lauf wird nicht rekonstruiert.

## Scope und Designentscheidung

1. Nur der feste Workbench-Snapshot-GET des synthetischen Test-Workspaces
   `notary_team_01` ist im Scope. Die bereits veröffentlichte, **inaktive
   v1-Umsetzung** bestimmt einen internen, geschlossenen Grund am
   Entscheidungspunkt. Ihre Klassen sind
   `REQUEST_SCOPE_REJECTED`, `ACCESS_DECISION_UNAVAILABLE`,
   `ACCESS_DECISION_REJECTED` und `DENIAL_UNCLASSIFIED`. Ein Fehler oder eine
   Ablehnung innerhalb des [Live-Access-Decision-Adapters](../../../../src/nac_bff/live_access_decision.py)
   bleibt derzeit in `ACCESS_DECISION_REJECTED` zusammengefasst; seine
   bewusst neutrale öffentliche Entscheidung wird nicht aufgebrochen.
2. Der [FastAPI-Adapter](../../../../src/nac_bff/fastapi_adapter.py) gibt für
   jeden 403 weiterhin bytegleich
   `{"status":403,"error":{"code":"ACCESS_DENIED"}}` aus. Der interne
   Grund erscheint weder in Status, Body, Header noch im SPFx-Beleg. Ein
   voller oder fehlender Diagnosepuffer darf weder eine Freigabe bewirken noch die
   Antwort, den Access-Decision-Port oder den Provideraufruf verändern;
   fehlende Telemetrie ist **kein** positiver Diagnosebeleg.
   Der Endpunkt übergibt die interne Klasse ausschließlich über einen
   request-lokalen, nicht serialisierten Zustand an einen begrenzten,
   inaktiven In-Memory-Puffer ohne externen Callback. Entsteht der 403 vor dem Endpunkt, verwendet der HTTP-Rand
   `DENIAL_UNCLASSIFIED`; mehrere Schichten dürfen nicht mehrere Einträge
   für denselben Request erzeugen.
3. Der Eintrag hat eine feste Feld-Allowlist: Schema-Version, begrenzter
   UTC-Zeitpunkt, konstante Routenklasse `workbench_snapshot`, Methode `GET`,
   HTTP-Klasse `403`, geschlossene Grundklasse und
   `request_correlation_binding_sha256`. Es gibt keine frei formulierbaren
   Felder. Rohe Header/Korrelationswerte, URL, Pfad, Query, Claims, Actor-,
   Tenant- oder Matter-ID, Namen, Rollen, Grant-Daten, Graph-Antworten,
   Ausnahmeobjekte und Tokens bleiben aus dem Eintrag und öffentlichen Logs.
4. Eine Korrelation ist nur zulässig, wenn genau **ein** empfangener
   `X-Correlation-ID`-Header die einmalig per `crypto.randomUUID()` erzeugte
   `spfx-`-UUID-v4-Kennung enthält, der BFF den exakt empfangenen Wert vor
   jeder Fallback-Erzeugung ausschließlich im Speicher hasht und eine neue,
   geschützte Client-Receipt-Bindung denselben SHA-256-Wert trägt. Doppelte,
   kombinierte, fehlende, umgeschriebene oder syntaktisch abweichende Header
   führen zu `UNBOUND`, nie zu einer geratenen Zuordnung. Die bloße
   UUID-Syntax beweist weder Zufälligkeit noch ein Match; der geschützte
   Receipt-Abgleich ist zusätzlich nötig. Der Klarwert wird nicht
   persistiert. Die bestehende öffentliche Fallback-Antwort darf dabei
   nicht zur fälschlichen Korrelations-Evidence werden.
5. Der In-Memory-Puffer ist standardmäßig inaktiv und keine Live-Telemetrie.
   Eine spätere Aktivierung wird auf den
   gebundenen Test-BFF, ein kurzes geschlossenes Beobachtungsfenster und
   autorisierten Logzugriff begrenzt. Vor ihr müssen AVV-/DPA-Bezug,
   Aufbewahrungsfrist, Zugriffskreis, Paket-/Commit-/Tree-Bindung und die
   tatsächliche Telemetrie-Erfassung geprüft sein. Die jetzige Spezifikation
   erlaubt weder Aktivierung noch Deployment oder Provider-Read.
6. Der bestehende [Triage-Vertrag](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/workflows/verification-contracts/m365-bff-request-log-triage.verification.json)
   bleibt `OFFLINE_ONLY_NOT_LIVE_CAPABLE`. Seine historischen Datei-Hashes,
   das Zeitfenster, offenen Ziel-/Schema-/Auth-Bindungen und
   `provider_read_authorized=false` bleiben unverändert. Ein späterer
   Live-Versuch benötigt einen eigenen vorwärtsversionierten Vertrag und
   eine eigene exakt gebundene Owner-Freigabe.

## Gestufte direkte Serverdiagnose – Designrevision

**Stufe A: vorhandenen Serverzustand prüfen.** Vor einer neuen Bereitstellung
werden über einen separat freizugebenden Read-only-Kanal die Identität des
aktiven Test-BFF, der tatsächlich bereitgestellte Paket-/Versionsstand, die
gebundene Application-Insights-Ressource und deren Erfassungs-/Aufbewahrungs-
zustand festgestellt. Der Folge-Vertrag muss jeden hierfür benötigten
Metadaten-Endpunkt und sein Lesebudget einzeln schließen sowie App-ID,
Function, Tenant und vorhandene Leseberechtigung nachweisbar verbinden. Nur
ein so nachgewiesenes Ziel erlaubt eine bytegenau gehashte feste Abfrage mit
der geprüften Drei-Feld-Projektion `request_observed`, `http_class` und
`request_correlation_binding_sha256` im Beobachtungsfenster der vorhandenen
geschützten Clientbelege. Für die historische Triage gilt höchstens ein GET,
ohne Redirect, Retry oder Paging; auch ihr No-Refresh-Kanal ist erst zu
beweisen. Die [historische Triage](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/workflows/verification-contracts/m365-bff-request-log-triage.verification.json)
enthält dafür noch Platzhalter für Ziel, Query und Korrelationsnachweis; sie
ist **keine** Freigabe für eine reale Abfrage. Ein zeitgleicher HTTP 403 ohne
eindeutige Korrelationsbindung belegt nicht, dass genau der Teams-Request den
BFF erreichte. Leere, abgelaufene oder mehrdeutige Logs sind `UNPROVEN`, nicht
„BFF-Request fehlte“. Ein nachweislich nicht bereitgestellter BFF ist ein
eigener Befund und benötigt keinen instrumentierten Wiederholungstest.

**Stufe B: nur bei unzureichender Stufe A präzisieren.** Vor einer etwaigen
Aktivierung wird die inaktive v1-Implementierung in einem vorwärtsversionierten
Vertrag um geschlossene, nur intern lesbare Entscheidungsstufen ergänzt:
`GRAPH_READ_UNAVAILABLE`, `CASE_BINDING_INVALID`,
`ACTOR_ASSIGNMENT_MISSING`, `DEPUTY_GRANT_INVALID`,
`GRANT_AUDIT_INVALID` und `DECISION_PROJECTION_INVALID`. Sie unterscheiden
technischen Graph-Zugriff, synthetische Fall-/Team-Bindung, Zuordnung der
handelnden Person, Vertretungsfreigabe, Auditbindung und Validierung der
Zugriffsentscheidung. Der heutige
[Live-Access-Decision-Adapter](../../../../src/nac_bff/live_access_decision.py)
wandelt jede Ausnahme in eine neutrale Ablehnung um. Daher muss ein
vorwärtsversionierter, request-lokaler Diagnose-Result-/Port-Vertrag den
terminalen Entscheidungszweig **vor** dieser Zusammenfassung erfassen und an
den Endpunkt übergeben; die Projektionsprüfung kann ihren eigenen terminalen
Zweig ergänzen. Das öffentliche `AccessDecision`-Ergebnis und die
Provideraufrufe bleiben unverändert. Ein globaler, zwischen Requests geteilter
Fehlerzustand ist ausgeschlossen. Synthetische Negativ- und Nebenläufigkeitstests
müssen belegen, dass Graph-Fehler, leere/mehrdeutige Fallresultate und
Zwischenprüfungen nie fälschlich als fehlende Zuordnung oder ungültiger Grant
klassifiziert werden. Unbekannte Fehler bleiben `DENIAL_UNCLASSIFIED`.

Die Klassen `ACTOR_ASSIGNMENT_MISSING`, `DEPUTY_GRANT_INVALID` und
`GRANT_AUDIT_INVALID` erlauben trotz fehlender Roh-IDs Rückschlüsse auf
personenbezogene Zuordnungs- und Freigabezustände. Sie sind **sensible
geschützte Betriebsmetadaten**, nicht anonym. Vor ihrer Aktivierung muss
für jede Klasse der Inferenznutzen gegen das Datenschutzrisiko geprüft und
der namentlich qualifizierte, zweckgebundene Leserkreis samt kurzer
Aufbewahrung, Zugriffsschutz und AVV-/DPA-Basis belegt werden. Fehlt eine
dieser Bindungen, bleiben die Klassen im groben
`ACCESS_DECISION_REJECTED` zusammengefasst; kein konkreter Grund wird
behauptet. Explizite Existenzflags, konkrete IDs, Rohdaten, Graph-Antworten
und Ausnahmetexte dürfen weder im Ereignis noch in Teams, Git oder
öffentlichen Logs erscheinen. Die aktuelle v1-Allowlist und ihr Vertrag
bleiben bis zur Freigabe der neuen Spec-/Plan-/Vertragsfassung unverändert.

Erst danach kann eine separat genehmigte, exakt paket-, Ziel-, Principal-,
AVV-/DPA-, Aufbewahrungs- und Zugriffskreis-gebundene Bereitstellung im
bestehenden Test-BFF erfolgen. Genau **eine** neue Teams-Beobachtung verwendet
den bereits vorhandenen geschützten Client-Receipt-Mechanismus zur
Korrelation; sie benötigt keine neue SPFx-Funktion. Fehlt ein eindeutiger
Server-/Receipt-Abgleich oder die technisch geschützte Erfassung, endet der
Lauf ohne Ursachenbehauptung und ohne automatischen Retry. Die konkrete
Konfigurations-, Daten-, Rollen- oder Berechtigungskorrektur wird erst aus
einem bestätigten Befund abgeleitet und separat freigegeben.

## Risiken und verworfene Ansätze

Ein reiner HTTP-Middleware-Eintrag könnte nur „403 unbekannter Ursache“
melden und wäre für die Teams-Störung zu schwach. Ein Grundcode im
Client-Response würde den absichtlich neutralen Sicherheitsrand aufheben.
Rohe Graph-, Fall-, Personen- oder Vertretungsdaten im Telemetrieeintrag
würden den Datenschutz- und Inferenzumfang unnötig vergrößern. Die
vorgeschlagenen geschlossenen Stufen bleiben deshalb ausschließlich in
geschützter Server-Evidence und werden nur nach dokumentierter
Inferenzprüfung, AVV-/DPA-, Aufbewahrungs- und Zugriffskreisbindung aktiviert.
Bleibt nur
`ACCESS_DECISION_REJECTED` oder `DENIAL_UNCLASSIFIED`, darf dies nicht als
vollständige Ursache oder behobene Teams-Störung ausgegeben werden.

## Akzeptanzkriterien und Prüfziel

- **AC-748-BD-01:** Synthetische Negativtests treffen jeden 403-Zweig und
  prüfen seine geschlossene interne Klasse, einschließlich 403 vor dem
  Fach-Endpunkt. Unbekannte Fälle bleiben `DENIAL_UNCLASSIFIED`.
- **AC-748-BD-02:** Die öffentliche 403-Antwort und alle bestehenden
  Sicherheitsheader bleiben byte- und statusgleich; kein interner Grund
  erreicht Teams oder das SPFx-Receipt.
- **AC-748-BD-03:** Pro geeignetem, gebundenem 403 entsteht höchstens ein
  allowlist-konformer Eintrag. Doppelte, fehlende, ungültige, mehrdeutige
  oder nicht belegbar zufällige Korrelationswerte erzeugen keine positive
  Zuordnung; ein Fallback-Wert ersetzt nie den empfangenen Belegwert.
- **AC-748-BD-04:** Sink-Fehler, deaktivierter Sink und nicht erfasste
  Telemetrie verändern weder Zugriff noch Antwort und gelten als fehlende
  Evidenz. Tests prüfen, dass keine Rohwerte, IDs, URLs, Querys oder
  Ausnahmetexte im Eintrag landen.
- **AC-748-BD-05:** Aktivierung, Log-Read und neue Reproduktion bleiben bis
  zu separaten Ziel-, Vertrags-, AVV-/DPA-, Berechtigungs- und
  Owner-Bindungen gesperrt; #739, #632 und der historische #748-Lauf werden
  nicht entsperrt. Die Stufen A/B erweitern dieses v1-Akzeptanzkriterium
  nicht und erhalten eigene Kriterien im späteren Folgeplan.
- **AC-748-BD-06:** DE/EN-Spec, bestehender v1-Plan und -Vertrag,
  Traceability, synthetische Tests und lokale/Remote-Gates werden für jede
  Veröffentlichung synchron geprüft. Die oben genannten Befehle sind
  Prüfziele, keine bereits bestandenen Nachweise.

### Neue Designrevision mit begrenzter lokaler Freigabe für Stufe A und inaktive Stufe-B-Vorbereitung

- **AC-756-SD-01:** Ein Folge-Vertrag bindet vor jedem Read den aktiven
  Test-BFF, Paketstand, App-ID, Function, Tenant, bestehende Berechtigung,
  einzeln erlaubte Metadaten-Endpunkte und Lesebudgets; fehlende Bindungen
  blockieren statt einen anderen Tenant oder eine freie Abfrage zu nutzen.
- **AC-756-SD-02:** Die historische Abfrage bleibt bytegehasht, auf genau
  drei Ausgabefelder und höchstens einen GET ohne Redirect, Retry oder Paging
  beschränkt. Ein eindeutig mit dem geschützten Receipt korrelierter 401/403
  belegt nur Eingang und Antwortklasse, nicht die konkrete Ablehnungsursache;
  dafür wäre zusätzliche unabhängige geschützte Server-Evidence nötig.
  Leere, abgelaufene oder mehrdeutige Logs bleiben `UNPROVEN`.
- **AC-756-SD-03:** Ein vorwärtsversionierter, request-lokaler
  Diagnose-Result-/Port-Vertrag klassifiziert nur terminale Ablehnungszweige.
  Negativ- und Nebenläufigkeitstests schließen falsche Zuordnungen bei
  Graph-Fehlern, leeren oder mehrdeutigen Resultaten und Zwischenprüfungen
  aus. Die öffentliche Antwort und die Access-Decision-/Provider-Semantik
  bleiben unverändert.
- **AC-756-SD-04:** Jede inferenztragende Klasse benötigt eine dokumentierte
  Datenschutzbewertung, AVV-/DPA-Basis, qualifizierten Leserkreis,
  Zugriffsschutz und kurze Aufbewahrung. Ohne diese Bindungen bleibt die
  grobe v1-Klasse bestehen; Rohdaten und personenbezogene Evidence verlassen
  den geschützten Speicher nicht.
- **AC-756-SD-05:** Eine spätere Bereitstellung und genau eine neue
  Teams-Beobachtung brauchen separate exakte Freigaben und Korrelationsbelege.
  Fehlende Evidence stoppt ohne Retry oder Ursachenbehauptung; #739, #632
  und die historischen #748-Artefakte bleiben unberührt.

## Nicht-Ziele

Keine neue Anmeldung, kein Credential- oder Microsoft-Zugriff, kein
Token-Refresh, kein Azure-/BFF-/SPFx-Deployment, keine Rollen- oder
Berechtigungsänderung, keine reale Diagnose und keine Freigabe eines
weiteren Live-Laufs in dieser Designphase. Der Diagnoseeintrag ist keine
neue KI-Funktion und keine neue Bedienfunktion der `nac`-CLI; falls die
spätere Umsetzung eine Operator-Bedienkante einführt, benötigt sie einen
separaten CLI-Vertrag und die gewöhnliche SBOM-/Lizenzprüfung.
