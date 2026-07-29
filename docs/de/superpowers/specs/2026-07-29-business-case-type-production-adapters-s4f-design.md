# BusinessCaseType Produktionsadapter S4f

Status: `S4F_PARTIAL_IMPLEMENTATION_DESIGN_OFFLINE`
Datum: 29. Juli 2026
Scope: entschiedene Produktionsadapter ohne Live-Providerzugriff

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-production-adapters-s4f
leading_issue: https://github.com/notariat8/NaC/issues/704
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-07-29-business-case-type-production-adapters-s4f.md
review_gates:
  - Secrets
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4F-01
  - AC-S4F-02
  - AC-S4F-03
  - AC-S4F-04
  - AC-S4F-05
  - AC-S4F-06
  - AC-S4F-07
validation_commands:
  - python3 -m unittest tests.test_business_case_type_production_adapters tests.test_sqlite_evidence_staging_outbox tests.test_business_case_type_production_adapters_contract tests.test_business_case_type_production_adapters_cli
  - python3 scripts/validate_business_case_type_production_adapters.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/quality_gate.py --profile strict
  - git diff --check
```

## Ziel

S4f ersetzt die in S4e erkannten Platzhalter dort durch offline geprüfte
Adapterimplementierungen, wo die Plattform bereits entschieden ist. Der Slice
führt keinen Provideraufruf aus, aktiviert keine Laufzeit und erhebt keinen
Anspruch auf Produktionsreife.

## Implementierte Adapter

1. Ein GitHub-Issue-Kommentar-Verifier bindet Owner, Association, unveränderten
   kanonischen Kommentar, Issue und alle S4d-Hashes. Das hashgeprüfte `gh`-Abbild
   wird als versiegeltes Linux-`memfd` ausgeführt; stdout ist vor Abschluss
   begrenzt und stderr wird verworfen.
2. Eine zertifikatsbasierte Write-Identity-Factory bindet Tenant, Client-ID,
   Zertifikats- und Private-Key-Inhalt und übergibt nur bereits geprüfte Bytes
   an den Tokenprovider.
3. Ein `urllib`-HTTP-Port blockiert Redirects, fremde Hosts, Nicht-v1.0-Pfade,
   Dot-Segmente, kodierte Separatoren, nicht erlaubte Methoden, automatische
   Retries und unredigierte Fehlerkörper.
4. Eine lokale SQLite-Staging-Outbox persistiert kanonische Evidence-Ereignisse
   atomar, restartfest und hash-/sequenzgebunden. Routing-Spalten werden beim
   Öffnen global gegen den hashgebundenen Ereignisinhalt geprüft. Sie darf eine Mutation nicht
   abschließen und ist keine zentrale Wahrheit.

## Bewusst offene Adapter

- Der zentrale Produktions-Outbox-Store bleibt gemäß Zielarchitektur
  PostgreSQL. S4f liefert nur eine restartfeste lokale SQLite-Staging-Grenze.
  Promotion, zentrale Bestätigung, Retention und lokales Cleanup benötigen
  einen separaten PostgreSQL-Vertrag. Ohne diese Bestätigung darf die lokale
  Outbox eine Mutation nicht als abgeschlossen markieren.
- Brokerprodukt und Signatur-/Anchor-Verfahren sind in der Zielarchitektur
  ausdrücklich noch nicht entschieden. S4f implementiert dafür keine
  Scheinadapter.
- Der Azure-Blob-WORM-Journaladapter ist vorhanden; sein produktiver
  Management-/Data-Plane-Transport sowie der irreversible Policy-Lock bleiben
  owner-gated.
- Eine dedizierte Entra-Write-Identität, ihr Site-Grant und der provider-seitige
  Readback beider Bindungen bleiben Live-Gates.

Der Abschlussstatus lautet deshalb
`S4F_PARTIAL_ADAPTERS_VERIFIED_OFFLINE`, nicht `S4E_READY_OFFLINE`, nicht
`RUNTIME_READY` und nicht `LIVE_READY`.

## Sicherheitsgrenzen

- `notary_team_01` bleibt der einzige zulässige Workspace.
- Die Provisioning-App darf keine Geschäftsvorfallsdaten schreiben.
- BFF, Provisioning und Writer bleiben getrennte Principals.
- Kein Adapter folgt Redirects oder führt automatische Retries aus.
- Providerfehler werden auf stabile Reason Codes reduziert.
- Token, Zertifikatspfade, Principal-IDs, Kommentare und Providerkörper werden
  nicht ausgegeben.
- Tests verwenden ausschließlich injizierte lokale Fakes und temporäre
  SQLite-Dateien.

## Akzeptanzkriterien

- **AC-S4F-01:** Provisioning-, Writer- und BFF-Identitäten bleiben getrennt.
- **AC-S4F-02:** Der Graph-HTTP-Port blockiert jede Abweichung von der
  gebundenen Graph-v1.0-Schreibkante einschließlich Normalisierungs- und
  Percent-Encoding-Umgehungen sowie rohe und kodierte Kontrollzeichen.
- **AC-S4F-03:** Der Owner-Verifier akzeptiert genau einen unveränderten,
  kanonischen Owner-Kommentar, führt ausschließlich ein versiegeltes
  hashgeprüftes Binärabbild mit begrenzter Ausgabe aus und gibt keine Rohdaten
  aus.
- **AC-S4F-04:** Die lokale SQLite-Staging-Outbox überlebt Neustarts und
  erzwingt Sequenz, Hashkette, Routing-Spaltenbindung, Deduplizierung und
  atomare Transaktionen. Sie
  enthält keine Abschluss-, Ack-, Promotions- oder Cleanup-Operation.
  Datei und Verzeichnis erfordern exakt `0600` beziehungsweise `0700`. Nur
  explizit erlaubte lokale Linux-Dateisysteme werden akzeptiert; unbekannte
  Dateisysteme werden abgewiesen. Eine Erkennung lokaler Sync-Verzeichnisse ist
  noch nicht implementiert und bleibt ein Runtime-Blocker.
- **AC-S4F-05:** Zentrale PostgreSQL-Outbox mit Promotion, Ack, Retention und lokalem Cleanup,
  Brokerprodukt,
  Signatur-/Anchor-Verfahren, provider-seitiger Identity- und Site-Grant-Readback,
  Azure-WORM-REST-Transport, irreversibler WORM-Policy-Lock, dedizierte
  Entra-Writer-Identität mit Site-Grant, Erkennung lokaler Sync-Verzeichnisse und owner-gated Live-Aktivierung
  bleiben jeweils explizite Blocker.
- **AC-S4F-06:** Die Statusausgabe meldet nur
  `S4F_PARTIAL_ADAPTERS_VERIFIED_OFFLINE`; Produktionsreife,
  Runtime-Komposition und Live-Autorisierung bleiben `false`.
- **AC-S4F-07:** Tests, Contracts, Validatoren, Strict-Gate und unabhängiger
  Review bestehen.
