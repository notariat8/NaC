# Interner BFF-Diagnoseeintrag für den Teams-403

Status: Spezifikation freigegeben; Implementierungsplan zur Owner-Review; keine Implementierung

Datum: 26. September 2026

Führendes Issue: [#748](https://github.com/notariat8/NaC/issues/748)

Ausgangsstand: Branch `codex/748-bff-request-log-triage`, Commit
`d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b`. Diese neue
Vorwärtsspezifikation ergänzt die [historische Request-Log-Triage](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/docs/de/superpowers/specs/2026-09-25-m365-bff-request-log-triage-design.md), ohne deren Belege,
Vertrag oder Freigabestatus zu verändern.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-403-diagnostic-event
leading_issue: https://github.com/notariat8/NaC/issues/748
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
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python -m unittest discover -s tests -p test_nac_bff_workbench_endpoint.py
  - python -m unittest discover -s tests -p test_nac_bff_azure_function_host.py
  - python -m unittest discover -s tests -p test_nac_bff_403_diagnostic_event.py
  - graft check
  - python scripts/nac.py doctor --profile strict
```

## Zweck und Evidenzgrenze

Die vorhandenen Clientbelege zeigen eine verfügbare SPFx-Benutzerkennung und
HTTP 403 für den gebundenen Workbench-GET. Sie belegen nicht, ob die Azure-
Plattform oder welcher Python-Zweig die Antwort erzeugt hat. Der
[Workbench-Endpunkt](../../../../src/nac_bff/workbench_endpoint.py) fasst
Scope-Abweichung, Fehler des Access-Decision-Ports und ungültige oder
verweigerte Zugriffsentscheidung zur gleichen öffentlichen Meldung
`ACCESS_DENIED` zusammen. Das ist eine gewollte Informationsgrenze.

Für eine **spätere, separat genehmigte neue Reproduktion** soll ein
geschützter, strukturierter BFF-Eintrag zeigen, welcher grobe interne Zweig
einen 403 erzeugte. Er ist kein Fix der Berechtigung, rekonstruiert den
historischen Lauf nicht und liefert bei einer bloßen Klasse
`ACCESS_DECISION_REJECTED` noch nicht automatisch den konkreten Graph- oder
Rollenfehler.

## Scope und Designentscheidung

1. Nur der feste Workbench-Snapshot-GET des synthetischen Test-Workspaces
   `notary_team_01` ist im Scope. Ein interner, geschlossener Grund wird am
   Entscheidungspunkt bestimmt. Die erlaubten Klassen sind
   `REQUEST_SCOPE_REJECTED`, `ACCESS_DECISION_UNAVAILABLE`,
   `ACCESS_DECISION_REJECTED` und `DENIAL_UNCLASSIFIED`. Ein Fehler oder eine
   Ablehnung innerhalb des [Live-Access-Decision-Adapters](../../../../src/nac_bff/live_access_decision.py)
   bleibt zunächst in `ACCESS_DECISION_REJECTED` zusammengefasst; seine
   bewusst neutrale öffentliche Entscheidung wird nicht aufgebrochen.
2. Der [FastAPI-Adapter](../../../../src/nac_bff/fastapi_adapter.py) gibt für
   jeden 403 weiterhin bytegleich
   `{"status":403,"error":{"code":"ACCESS_DENIED"}}` aus. Der interne
   Grund erscheint weder in Status, Body, Header noch im SPFx-Beleg. Ein
   Fehler des Diagnose-Sinks darf weder eine Freigabe bewirken noch die
   Antwort, den Access-Decision-Port oder den Provideraufruf verändern;
   fehlende Telemetrie ist **kein** positiver Diagnosebeleg.
   Der Endpunkt übergibt die interne Klasse ausschließlich über einen
   request-lokalen, nicht serialisierten Zustand an den einmalig aufgerufenen
   Sink. Entsteht der 403 vor dem Endpunkt, verwendet der HTTP-Rand
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
5. Der Sink ist standardmäßig inaktiv. Eine spätere Aktivierung wird auf den
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

## Risiken und verworfene Ansätze

Ein reiner HTTP-Middleware-Eintrag könnte nur „403 unbekannter Ursache“
melden und wäre für die Teams-Störung zu schwach. Ein Grundcode im
Client-Response würde den absichtlich neutralen Sicherheitsrand aufheben.
Feingranulare Graph-, Fall-, Personen- oder Vertretungsgründe im Telemetrie-
eintrag würden den Datenschutz- und Inferenzumfang unnötig vergrößern.
Deshalb beginnt der Entwurf mit groben internen Klassen. Ergibt die spätere
Reproduktion nur `ACCESS_DECISION_REJECTED`, ist eine weitere gezielt
freizugebende Read-only-Prüfung erforderlich; das Ergebnis darf nicht als
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
  nicht entsperrt.
- **AC-748-BD-06:** DE/EN-Spec, späterer Plan, neuer Vertrag,
  Traceability, synthetische Tests und lokale/Remote-Gates werden vor einer
  Veröffentlichung synchron geprüft. Die oben genannten Befehle sind
  Prüfziele, keine bereits bestandenen Nachweise.

## Nicht-Ziele

Keine neue Anmeldung, kein Credential- oder Microsoft-Zugriff, kein
Token-Refresh, kein Azure-/BFF-/SPFx-Deployment, keine Rollen- oder
Berechtigungsänderung, keine reale Diagnose und keine Freigabe eines
weiteren Live-Laufs in dieser Designphase. Der Diagnoseeintrag ist keine
neue KI-Funktion und keine neue Bedienfunktion der `nac`-CLI; falls die
spätere Umsetzung eine Operator-Bedienkante einführt, benötigt sie einen
separaten CLI-Vertrag und die gewöhnliche SBOM-/Lizenzprüfung.
