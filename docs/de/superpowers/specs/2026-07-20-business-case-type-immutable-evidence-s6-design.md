# BusinessCaseType Immutable Evidence S6a Design

Status: `S6_OFFLINE_FOUNDATION`; Live-Ausführung bleibt `BLOCKED_PENDING_S7_APPROVAL`
Datum: 20. Juli 2026
Scope: kanonische, redigierte und vollständig synthetische Offline-Grundlage für Mutationsevidence

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-immutable-evidence-s6
leading_issue: https://github.com/notariat8/NaC/issues/687
risk_gate: Privacy
delivery_mode: Protected PR
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S6-01
  - AC-S6-02
  - AC-S6-03
  - AC-S6-04
  - AC-S6-05
  - AC-S6-06
  - AC-S6-07
  - AC-S6-08
validation_commands:
  - python3 -m unittest tests.test_immutable_evidence tests.test_business_case_type_immutable_evidence tests.test_business_case_type_immutable_evidence_cli tests.test_business_case_type_immutable_evidence_contract
  - python3 scripts/validate_business_case_type_immutable_evidence.py
  - python3 scripts/nac.py kg business-case-type-evidence-dry-run --format json
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Zweck Und Grenze

S6a definiert den Evidence-Kern für spätere Schema-, Backfill-, Korrektur-,
Cutover- und Rollback-Mutationen. Nur lokale synthetische In-Memory-Adapter
prüfen Reihenfolge, Hashkette, Identitätsbindungen, restart-sichere
Publikation und Reconciliation. Es gibt keine Mutation, keinen Netzwerk-,
Provider-, Tenant- oder Credential-Zugriff und keine neuen Live-Funktionen.

Das Ergebnis ist ausschließlich `S6_OFFLINE_FOUNDATION`. Es ist weder
Produktionsfreigabe noch Nachweis von WORM, Signatur, Anchor, Retention,
Persistenz oder Revisionssicherheit. Jeder Live-Schritt bleibt
`BLOCKED_PENDING_S7_APPROVAL`; `AuditJournalLite` bleibt eine
Betriebsprojektion.

## Kanonisches Evidence-Envelope

Ein Event verwendet `nac.immutable-evidence-event/v0.1`. Die Basisfelder
enthalten unter anderem `correlation_id`, `actor_ref`,
`actor_principal_ref`, `tenant_binding_sha256`,
`principal_key_binding_sha256`, Tool, Rolle, Aktion, die S3-Katalogbindung,
Manifest, Retention, Privacy und ETags. Der operationsweite
`idempotency_key_sha256` bleibt über die Kette stabil. Der
event-spezifische `delivery_key_sha256` bindet das vollständige kanonische
Event mit Ausnahme von `event_id` und `delivery_key_sha256` selbst und darf
nicht wiederverwendet werden.

`reconciliation_closed` persistiert neben `result_code`, Operator- und
Approver-ActorRefs auch `operator_principal_ref`,
`operator_tenant_binding_sha256`,
`operator_principal_key_binding_sha256`, `approver_principal_ref`,
`approver_tenant_binding_sha256` und
`approver_principal_key_binding_sha256`.

ASCII-JSON mit sortierten Schlüsseln, kompakten Separatoren, ohne NaN und ohne
Fließkommazahlen ist die einzige kanonische Serialisierung. SHA-256 über exakt
diese Bytes bildet den Event-Hash. Sequenzen starten bei eins, sind lückenlos
und binden über `previous_event_sha256` exakt den Vorgänger. Correlation,
Actor, beide Security-Bindings, Fachbindung, Idempotenz, Retention und Privacy
sind innerhalb der Kette unveränderlich.

Tool und Rolle stammen aus den festen Runtime-Registern. Geschäftsvorfalltyp
und Katalogversion stammen exakt aus `BusinessCaseTypeCatalog.from_repo`: 20
kanonische S3-Slugs und ausschließlich die SHA-256-`CatalogVersion`
`fcf1c7ba1a35980f5f1d371381ae5c218cd3ce94372f2c1df821f2ad40d2fab0`.
ETags werden ausschließlich als
`hmac-sha256:k<positive_integer>:<64_lowercase_hex>` gespeichert. Der HMAC
verwendet `nac.etag-evidence.v1\u0000`, einen mindestens 32 Byte langen
separaten Schlüssel, eine positive Key-Version und die Tenant-Bindung
`SHA-256(nac.tenant-binding.v1\u0000,tenant_id)`.

## Intent, Outcome Und Readback

Der normale Pfad lautet exakt `intent -> outcome -> readback`. Persistiertes
Intent muss einer Mutation vorausgehen. Outcome dokumentiert nur den
Write-Versuch; Readback ist eine getrennte Beobachtung. Fehlendes oder
ungewisses Outcome, fehlender Readback oder fehlende Downstream-Evidence
blockiert Abschluss und Blind-Retry fail-closed. Nach
`write-state-uncertain` ist zuerst `reconciliation_required` erforderlich.

## Actor-, Correlation- Und Principal-Bindung

`ActorRef` ist tenant- und key-version-gebundenes HMAC-SHA256 im Format
`actor-v1-k<version>-<64hex>`. Die separate stabile Principal-Referenz ist
`HMAC-SHA256(principal_key, nac.principal-ref.v1\u0000 || tenant_id || actor_object_id)`
und wird als `principal-v1-<64hex>` persistiert.

Zusätzlich werden zwei nicht umkehrbare Security-Bindings persistiert:

- `tenant_binding_sha256 = SHA-256(nac.tenant-binding.v1\u0000 || tenant_id)`,
- `principal_key_binding_sha256 = SHA-256(nac.principal-key-binding.v1\u0000 || principal_key)`.

Correlation und Actor müssen dieselbe Tenant-Bindung besitzen. Actor,
Operator und Approver müssen denselben Tenant und denselben
Principal-Key-Binding-Hash besitzen. Unterschiedliche Tenants oder
Principal-Keys schlagen bei Event-Erzeugung, Closure, Claim und
Retry-Autorisierung fail-closed fehl. Operator und Approver müssen trotzdem
unterschiedliche stabile Principals sein. Rohidentitäten und Schlüsselmaterial
werden weder gespeichert noch ausgegeben.

## Produktionsports Ohne Produktivadapter

S6a friert fünf Ports ohne produktive Wirkung ein:
`OutboxPort`, `BrokerPort`, `SignatureAnchorPort`, `WormJournalPort` und
`ReconciliationStorePort`.

Der Broker bestätigt jedes Event mit einer eindeutigen opaken Referenz, die
Event-ID, Event-Hash, Operations- und Delivery-Key bindet.
`SignatureAnchorPort.anchor(records, *, idempotency_key_sha256)` und
`WormJournalPort.commit(records, anchor, *, idempotency_key_sha256)` verlangen
jeweils einen deterministischen, kettenkopfgebundenen Operations-Key:

`SHA-256(nac.immutable-evidence-publication-operation.v1\u0000 || operation || chain_head_sha256)`

Die Operationsnamen sind exakt `signature-anchor` und `worm-commit`. Derselbe
Key muss beim crash-sicheren Resume dasselbe Receipt liefern. Anchor- und
WORM-Readback bleiben getrennte Aufrufe; alle Providerreferenzen werden als
opake SHA-256-Referenzen normalisiert.

## Restart-Sichere Publication Und Reconciliation

`ReconciliationStorePort` umfasst exakt `claim_publication`,
`advance_publication`, `complete_publication`,
`authorize_publication_retry`, `require`, `close` und `is_required`.
`claim_publication` verlangt `claim_id`, `tenant_binding_sha256`,
`principal_key_binding_sha256` und die nichtleere geordnete Sequenz
`event_sha256s`; deren letztes Element muss dem Kettenkopf entsprechen.
`require` akzeptiert beide Security-Bindings und `event_sha256s` als optionale
Keyword-only-Felder.

Ein Pre-Claim-Requirement mit Reason
`evidence-publication-incomplete` persistiert beide Security-Bindings, den
vollständigen aktuell verfügbaren geordneten Event-Hash-Präfix,
`retry_authorized=false` und eine leere `retry_authorizations`-Liste. Vor dem
Outbox-Snapshot darf der Präfix leer sein. Vier-Augen-Autorisierung wird zuerst
in diesem Requirement persistiert. Ohne Principal-Key-Bindung bleibt der Retry
fail-closed. Der erste passende Claim muss den Präfix exakt fortsetzen,
übernimmt Autorisierungen und Zähler unter derselben atomaren State-Änderung
in den Publication-State, persistiert dort die vollständige geordnete Sequenz
und entfernt das konsumierte Requirement. Reclaims verlangen exakt dieselbe
Sequenz.

Vor jedem möglichen externen Side Effect wird eine Write-ahead-Stufe
persistiert: `outbox-snapshot`, `broker-in-flight`, `broker-complete`,
`anchor-in-flight`, `anchor-readback-in-flight`,
`anchor-readback-complete`, `worm-commit-in-flight`,
`worm-readback-in-flight`, `worm-readback-complete`. Der persistierte
`publication_progress` enthält exakt Stufe, bestätigte Event-Hashes sowie
Anchor-, Signatur- und WORM-Receipt-Hash. Bestätigungen sind append-only;
persistierte Referenzen dürfen nicht ersetzt werden.

Ein unterbrochener Claim bleibt gesperrt. Nur
`authorize_publication_retry` mit unterschiedlichen, an denselben Tenant und
Principal-Key gebundenen Operator-/Approver-Principals erlaubt die
Wiederaufnahme desselben Kettenkopfs und Fortschritts. Bereits bestätigte
Broker-Events werden übersprungen.

Ein abgeschlossener Claim liefert `status`, `result` und
`publication_progress`. Vor einem idempotenten Replay werden die gespeicherte
Kettenlänge gegen die aktuelle reale Eventzahl, `broker_ack_count` gegen die
Progress-Länge, der letzte bestätigte Hash gegen den Kettenkopf, die
`worm-readback-complete`-Stufe sowie Anchor-, Signatur- und WORM-Bindungen
validiert. Erst danach darf das gespeicherte Resultat ohne neue Provideraufrufe
zurückgegeben werden.

Alle Fehler externer Ports, einschließlich eines von einem Port ausgelösten
`ImmutableEvidenceError`, werden an der Boundary vollständig redigiert.
Providerdetails werden weder zurückgegeben noch persistiert. Zulässig sind nur
die festen Meldungen `evidence publication state is unavailable` und
`evidence publication requires reconciliation`. Nur der interne,
vertrauenswürdige Reconciliation-State-Fehler bleibt unterscheidbar.

## Retention, Legal Hold Und Zugriff

Jedes Event deklariert mindestens zehn Jahre Retention und
`legal_hold_capable=true`. Produktive Policy-Readbacks, Löschschutz,
monatlicher Access Review und Funktionstrennung bleiben spätere Gates. S6a
behauptet keinen dieser Nachweise.

## Negative Gates

Kein erfolgreicher Abschluss erfolgt bei Manipulation, Duplikat, Sequenz- oder
Phasenfehler, falschem Vorgänger, Factory-/Snapshot-Drift, unvollständiger
Evidence, sensiblen Feldern, Retention-Downgrade, ungültigem ETag-HMAC,
fehlendem oder falsch gebundenem Receipt, Claim-/Progress-/Completion-Drift,
abweichender realer Kettenlänge, nichtdeterministischem Anchor-/WORM-Key,
nicht autorisiertem Retry, identischen Vier-Augen-Principals, fremdem Tenant,
abweichendem Principal-Key oder Offenlegung externer Fehlerdetails.

## Status Und Nachweis

Der CLI-Smoke erzeugt nur synthetische Normal- und Reconciliation-Ketten. Die
redigierte Ausgabe nennt technische Hashes, Phasen, Eventzahl,
Reconciliation-Status und fehlende Produktionsports. Alle sechs Zähler
`network_calls`, `provider_calls`, `tenant_calls`, `tenant_writes`,
`credential_reads` und `live_mutations` sind null;
`production_worm_claim=false`.

## Akzeptanzkriterien

- **AC-S6-01:** Kanonisches Envelope, strikte Phasen, lückenlose Sequenz und
  SHA-256-Kette.
- **AC-S6-02:** Intent vor Mutation, Outcome und Readback danach sowie
  unveränderliche Operations-, Delivery-, Tenant- und Principal-Key-Bindungen;
  Retry nur nach autorisiertem Resume.
- **AC-S6-03:** Correlation, Actor, Operator und Approver sind an denselben
  persistierten Tenant gebunden; alle drei Principals an denselben
  Principal-Key. Abweichungen schlagen fail-closed fehl.
- **AC-S6-04:** Explizite Ports verlangen deterministische
  kettenkopfgebundene Anchor-/WORM-Idempotenz, unabhängige Readbacks und
  restart-sichere Publication-Claims.
- **AC-S6-05:** Mindestens zehn Jahre Retention und Legal-Hold-Fähigkeit sind
  deklariert; produktive Kontrollnachweise bleiben offen.
- **AC-S6-06:** Pre-Claim-Retry-Autorisierung und geordneter Event-Hash-Präfix
  werden principal-key-gebunden persistiert; der Claim muss den Präfix exakt
  fortsetzen und konsumiert ihn atomar in eine vollständige Publication-Sequenz.
  Completed-Replay validiert reale Kettenlänge und Providerbindungen.
- **AC-S6-07:** Offline-/Live-Status und alle sechs Nullzähler sind exakt; es
  gibt keinen Produktions- oder WORM-Anspruch.
- **AC-S6-08:** Ungebundener Pre-Claim-Retry, Präfix-/Sequenz-Drift sowie alle
  weiteren negativen Bindungs-, Resume-, Progress- und Portfehlerfälle schlagen
  ohne Detailleck fail-closed fehl.

## Nichtziele

- keine PostgreSQL-, Broker-, Signatur-, Anchor- oder WORM-Verbindung,
- kein Graph-, SharePoint-, Entra-, Azure-, Netzwerk- oder Credential-Zugriff,
- keine produktiven oder auflösbaren Akten-, Personen- oder Dokumentdaten,
- kein Live-Schema-Apply, Backfill, Cutover, Rollback oder Cleanup,
- keine S7-Freigabe und keine Aussage revisionssicherer Produktion.
