# Interner BFF-Diagnoseeintrag für den Teams-403 – Implementierungsplan

Status: Plan zur Owner-Review; keine Implementierung, Aktivierung oder reale Diagnose

Datum: 26. September 2026

Führendes Issue: [#748](https://github.com/notariat8/NaC/issues/748)

Freigegebene Spec: [Interner BFF-Diagnoseeintrag](../specs/2026-09-26-m365-bff-403-diagnostic-event-design.md)
(`m365-bff-403-diagnostic-event`, `AC-748-BD-01` bis `AC-748-BD-06`).
Die Spec wurde auf Commit `166ef85665e7b90efdfcc8560926ffcde16ffc53`
und Tree `2653fb02da349a6954534f29dbd229571285671a` freigegeben.
Delivery Mode: Protected PR; Risk Gate: Human Approval. Dieser Plan erteilt
keine Implementierungs- oder Live-Freigabe.

Scope-Hinweis: [#748](https://github.com/notariat8/NaC/issues/748) ist
bereits als erledigt geschlossen. Sein ursprünglicher Auftrag deckt den
Windows-Current-State-Pfad mit `AC-CSD-01` bis `AC-CSD-08` ab, nicht diesen
neuen internen 403-Eintrag. Die freigegebene Spec referenziert #748 noch als
Ausgangspunkt; vor Umsetzung oder Veröffentlichung muss ein eigener offener,
passend abgegrenzter führender Auftrag feststehen und die Spec-Traceability
darauf synchron angepasst und erneut geprüft werden. Dieser Plan nimmt eine
solche GitHub-Änderung nicht vorweg.

## Ziel und Abgrenzung

Ein künftig separat freigegebener, neuer Teams-Test soll anhand eines einzigen
geschützten internen BFF-Eintrags erkennen lassen, welcher grobe Zweig den
Workbench-403 auslöste. Die vorhandenen Clientbelege beweisen nur ein
verfügbares SPFx-Subject und einen HTTP 403, nicht die BFF- oder
Berechtigungsursache. Die öffentliche Antwort bleibt unverändert. Der
historische [Request-Log-Triage-Vertrag](../../../../workflows/verification-contracts/m365-bff-request-log-triage.verification.json)
bleibt `OFFLINE_ONLY_NOT_LIVE_CAPABLE`; #739 und #632 bleiben gesperrt.

## Test-first-Umsetzung nach Planfreigabe

1. **Prüfziel vor Code (AC-748-BD-01, -02).** In
   `tests/test_nac_bff_403_diagnostic_event.py` synthetische Fälle für
   Scope-Ablehnung, Access-Decision-Port-Fehler, ungültige/verweigerte
   Entscheidung und einen 403 vor dem Fach-Endpunkt anlegen. Sie erwarten nur
   `REQUEST_SCOPE_REJECTED`, `ACCESS_DECISION_UNAVAILABLE`,
   `ACCESS_DECISION_REJECTED` oder `DENIAL_UNCLASSIFIED`. Die exakten
   öffentlichen 403-Body-Bytes `{"status":403,"error":{"code":"ACCESS_DENIED"}}`,
   Status und Sicherheitsheader gegen bestehende Fixtures vergleichen. Eine
   Ablehnung oder ein Fehler des Live-Access-Decision-Adapters bleibt in der
   groben Klasse `ACCESS_DECISION_REJECTED`.
2. **Korrelation und Datenschutz zuerst negativ prüfen (AC-748-BD-03, -04).**
   Tests belegen höchstens einen Eintrag pro geeignetem Request und prüfen
   den inaktiven Sink, Sink-Ausnahmen und fehlende Telemetrie als fehlende
   Evidenz ohne Änderung von Zugriff oder Antwort. Nur genau ein empfangener
   `X-Correlation-ID`-Header mit `spfx-`-UUID-v4 aus einer einmaligen
   `crypto.randomUUID()`-Erzeugung darf vor jeder Fallback-Erzeugung im
   Speicher gehasht werden. Der positive Abgleich verlangt zusätzlich den
   gleichen SHA-256-Wert in einem neuen geschützten Client-Receipt; Syntax
   allein genügt nicht. Fehlende, doppelte, kombinierte, umgeschriebene oder
   abweichende Header sowie unbewiesene Receipt-Bindung bleiben `UNBOUND`.
   Bei fehlendem oder ungültigem Einzelheader entsteht kein korrelierbarer
   Eintrag und kein Ersatz-Hash; für einen syntaktisch gültigen Einzelheader
   darf ein Eintrag nur dessen Hash tragen. Erst ein späterer geschützter
   Receipt-Abgleich darf diesen Eintrag einem Clientversuch zuordnen.
   Negativ-Fixtures untersagen Rohheader, URL/Pfad/Query, Claims, IDs,
   Namen, Rollen, Grants, Graph-Daten, Tokens und Ausnahmetext im Eintrag
   und in öffentlichen Logs.
3. **Geschlossene interne Umsetzung (AC-748-BD-01 bis -04).** Nur für den
   festen Workbench-Snapshot-GET des synthetischen `notary_team_01` die
   Grundklasse an den bestehenden Entscheidungspunkten in
   [workbench_endpoint.py](../../../../src/nac_bff/workbench_endpoint.py)
   bestimmen. Sie geht ausschließlich über request-lokalen,
   nicht serialisierten Zustand an den einmalig aufgerufenen Sink am
   [FastAPI-Rand](../../../../src/nac_bff/fastapi_adapter.py); ein vor dem
   Endpunkt entstandener 403 ist `DENIAL_UNCLASSIFIED`. Der Sink bleibt
   standardmäßig inaktiv und nimmt ausschließlich Schema-Version,
   begrenzten UTC-Zeitpunkt, feste Routenklasse `workbench_snapshot`,
   Methode `GET`, HTTP-Klasse `403`, geschlossene Grundklasse und
   `request_correlation_binding_sha256` an. Keine freie Text- oder
   Metadatenfläche, kein neuer SDK-Zwang, keine Änderung der
   Access-Decision- oder Provider-Semantik. Fehler des Sinks werden als
   fehlende Evidence behandelt und dürfen weder Zugang gewähren noch
   Antwort oder Provideraufruf ändern.
4. **Vorwärtsvertrag und Fail-closed-Gates (AC-748-BD-05, -06).** Einen
   getrennten vorwärtsversionierten Vertrag unter
   `workflows/verification-contracts/m365-bff-403-diagnostic-event.verification.json`
   samt `scripts/validate_m365_bff_403_diagnostic_event.py` und synthetischen
   Negativtests erstellen. Bis zu eigener Ziel-, Paket-/Commit-/Tree-,
   AVV-/DPA-, Aufbewahrungs-, Zugriffs-, Telemetrie-, Client-Receipt- und
   Owner-Bindung bleiben `provider_read_authorized=false` und
   `deployment_authorized=false`; keine historische Evidence wird
   rekonstruiert. Accounts desselben Principals dürfen keine unabhängige
   Freigabe darstellen. Ohne konkret zitierte, anwendbare externe
   Zwei-Personen-Pflicht ist eine dokumentierte `OWNER_SOLO_APPROVAL` mit
   `four_eyes_satisfied=false` zulässig; verlangt eine solche Pflicht zwei
   natürliche Principals und ist nur einer verfügbar, gilt
   `BLOCKED_SINGLE_PRINCIPAL`. Fehlt die behauptete Quellen-/Scope-Bindung,
   gilt `BLOCKED_REQUIREMENT_CITATION_MISSING`. Negativtests und Vertrag
   müssen diese Grenze erzwingen. Der bestehende Triage-Vertrag bleibt
   unverändert.
5. **Synchronisierung und Review (AC-748-BD-06).** DE/EN-Spec und -Plan,
   Traceability, Vertrag, Validator und Tests führen dieselben sechs ACs.
   Dokumentation beschreibt den inaktiven Zustand und die Grenze einer bloßen
   `ACCESS_DECISION_REJECTED`-Klasse. Keine neue `nac`-CLI-Bedienkante, da
   nur ein interner Eintrag entsteht; sollte doch eine Operator-Funktion
   nötig werden, vor ihrer Umsetzung separat spezifizieren. SBOM/AI-SBOM
   nur bei tatsächlich neuer Laufzeit- bzw. AI-Komponente ändern. Die
   Umsetzung durchläuft `implement -> review -> fix` mit unabhängiger
   Datenschutz-, Sicherheits- und DE/EN-Prüfung.

## Prüfgates und Abschlussgrenze

Nach einer gesonderten Plan- und Implementierungsfreigabe: fokussierte
Negativtests und bestehende Workbench-/Host-Tests, Validator, Spec-Traceability,
DE/EN-Parität, Dokumentationslinks, Privacy-/Secret-Gates, `graft build`,
`graft check` und
`python scripts/nac.py doctor --profile strict`. Vor einer späteren
Veröffentlichung zusätzlich vollständige `main...HEAD`-Datei- und
Commitliste prüfen, nur den gebundenen Scope pushen und verpflichtende
   Remote-CI auswerten. Ein Push oder eine PR-Änderung braucht dafür eine
   eigene, scopegebundene Freigabe; die Planfreigabe allein genügt nicht.
   Diese Befehle sind geplante Gates, noch keine
Erfolgsnachweise. Aktivierung, Microsoft-/Provider-Read, neue Reproduktion,
Deployment, #739-Freigabe und #632-Live-Lauf benötigen jeweils separate,
exakt gebundene Freigaben. Ein späteres `ACCESS_DECISION_REJECTED` belegt
allein noch keinen konkreten Graph- oder Rollenfehler und keinen Fix.
