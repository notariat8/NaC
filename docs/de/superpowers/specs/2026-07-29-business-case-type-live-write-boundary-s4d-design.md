# BusinessCaseType Live-Write-Grenze S4d

Status: `S4D_DESIGN_READY_OFFLINE`
Datum: 29. Juli 2026
Scope: owner-gated Produktionsgrenze ohne Live-Tenant-Ausführung

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-live-write-boundary-s4d
leading_issue: https://github.com/notariat8/NaC/issues/700
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Secrets
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4D-01
  - AC-S4D-02
  - AC-S4D-03
  - AC-S4D-04
  - AC-S4D-05
  - AC-S4D-06
  - AC-S4D-07
  - AC-S4D-08
validation_commands:
  - python3 -m unittest tests.test_business_case_type_live_write_boundary tests.test_business_case_type_live_write_boundary_contract tests.test_business_case_type_live_write_boundary_cli
  - python3 scripts/validate_business_case_type_live_write_boundary.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Ziel

S4d komponiert die bestehende S4c-Write-Edge mit einer getrennten
owner-gated Write-Identität, kanonischer S6-Evidence und dem S6b-WORM-Port.
Der BFF bleibt strikt read-only. Der Offline-Slice liefert keine Live-Factory
und nimmt weder Entra-, Credential-, Azure- noch Tenant-Änderungen vor.

Der Abschlussstatus lautet `S4D_READY_OFFLINE`. `READY_FOR_LIVE` ist erst
zulässig, wenn produktive Identity-, Outbox-, Broker-, Signatur-, WORM- und
Reconciliation-Adapter in einem späteren gebundenen Owner-Gate nachgewiesen
sind.

## Bindungen

Eine unveränderliche `LiveWriteApprovalAttestation` bindet mindestens:

- Git-Commit und Tree,
- S4d-Domain- und Verification-Contract,
- Plan, Toolchain und Schrittfolge,
- Evidence-Policy sowie Tenant-, Workspace-, Site-, Akten-/Aufgabenlisten- und
  Graph-v1.0-Zielgrenze,
- Write-Principal und getrennten BFF-Read-Principal.

Vor Credential- oder Transportzugriff werden alle statischen Bindungen
validiert. Danach prüft ein injizierter `WriteIdentityInspectionPort` über
eine getrennte, owner-gebundene read-only Inspection-Credential-/Transport-
Grenze frisch:

- Write-Identität: exakt `Sites.Selected` und Site-Rolle `write`,
- BFF-UAMI: exakt `Sites.Selected` und Site-Rolle `read`,
- verschiedene Principals, exakt dieselbe gebundene Ziel-Site,
- keine breiteren Graph-Rollen.

Erst nach diesem Readback darf der injizierte `WriteIdentityFactoryPort` den
Business-Write-Token-Provider liefern. Statischer Drift verursacht null
Credential-Zugriffe; die Inspection-Credentials werden nur für den
authentifizierten Ist-Readback verwendet. Die bestehende breit privilegierte
Provisioning-App wird nicht als Business-Daten-Write-Identität
wiederverwendet.

Die Owner-Attestation verwendet einen zirkelfreien
`plan_binding_sha256`: Der vollständige kanonische Plan wird mit normierter
Approval-Referenz gebunden. Im Ausführungsprozess wird der Plan aus dem
genehmigten Envelope neu aufgebaut, die typisierte
`owner-approval-v1-<sha256>`-Referenz eingesetzt und sowohl
`plan_binding_sha256` als auch der finale `plan_sha256` exakt revalidiert.

## Evidence- und Crash-Semantik

`S4dMutationEvidenceHook` implementiert den bestehenden S4b-
`MutationEvidenceHook`. Er delegiert den lokalen Generation-CAS-State an S4c
und führt parallel eine kanonische S6-Kette für die exakten Operationen
`case_create`, `case_status_update`, `task_create`, `task_update` und
`business_case_type_backfill`.

Die fail-closed Reihenfolge lautet:

1. statisches Owner-/Hash-/Target-/Principal-Gate,
2. frischer Identity-/Permission-Readback,
3. Dedupe- oder ETag-Preflight,
4. lokaler SQLite-Intent mit Generation-CAS,
5. kanonischer S6-Intent und verifizierter Outbox-Readback,
6. genau ein Graph-Write-Versuch,
7. lokales und kanonisches Outcome,
8. exakter Graph-Readback und kanonisches Readback,
9. Broker-Acks, Signature-Anchor mit Readback und Azure-WORM-Commit mit
   unabhängigem Version-Readback sowie persistiertem `complete_publication`,
10. lokale Closure erst nach vollständig validiertem Publisher-Ergebnis mit
    exakter Event-/Ack-Anzahl, Anchor-, Signatur- und WORM-Bindung.

Ein Fehler vor Schritt 6 verursacht null Write-Versuche. Scheitert Schritt 5
nach lokalem Intent, wird bereits sticky `reconciliation_required`
persistiert. Jeder Fehler ab Schritt 6 laesst Intent und Reconciliation
ebenfalls sticky offen. Automatischer Mutation-Replay ist verboten; nur eine
spätere Dual-Control-Reconciliation darf Evidence-Publikation oder Closure
fortsetzen.

S4c-SQLite und die spätere zentrale Evidence-Outbox sind zwei
Persistenzsysteme. S4d behauptet deshalb keine atomare verteilte Transaktion.
Die Reihenfolge stellt stattdessen sicher, dass jedes Crash-Fenster entweder
vor der Mutation endet oder einen offenen, replay-blockierenden Zustand
hinterlaesst.

## Datenschutz

Ausgaben und persistierte technische Metadaten sind rekursiv allowlist-basiert.
Erlaubt sind Status, stabile Reason-Codes, Operationen, Zähler, Booleans und
SHA-256-Referenzen. Verboten sind rohe Tenant-, Site-, Listen-, App-,
Principal-, Matter-, Task- oder Item-IDs, URLs, Mutation-Felder, ETags,
HTTP-Header, Tokens, Zertifikate, Schlüssel, Dateipfade, Provider-
Attestationsinhalte und Exception-Texte.

## Akzeptanzkriterien

- **AC-S4D-01:** Lokale SQLite-Replay-Sicherung und S6/S6b-Publikation sind
  komponiert; lokale Closure erfolgt erst nach verifiziertem WORM-Readback.
- **AC-S4D-02:** Write- und BFF-Identität bleiben getrennt und exakt auf
  `Sites.Selected/write` beziehungsweise `Sites.Selected/read` begrenzt.
- **AC-S4D-03:** Statischer Drift blockiert vor Credentials; frischer
  Provider-Readback blockiert vor Mutation.
- **AC-S4D-04:** Crash- und Failure-Injection beweisen sticky
  Reconciliation und null automatischen Mutation-Replay.
- **AC-S4D-05:** Resultate, Fehler und Evidence enthalten nur die definierte
  Redaktions-Allowlist.
- **AC-S4D-06:** Ein synthetischer Offline-One-Shot-Smoke prüft alle fünf
  Operationen bei null externen Credential-, Socket-, DNS-, Graph-, Azure- und
  Tenant-Aktivitaeten.
- **AC-S4D-07:** Ein kanonischer Owner-Kommentar bindet Commit, Contracts,
  Plan, Target, Principals, Toolchain, Schrittfolge und Evidence-Policy.
- **AC-S4D-08:** Domain-/Verification-Contract, Validator, Tests, Doku,
  Strict-Gate und CI sind grün; der Slice bleibt `READY_OFFLINE`.

## Nicht Im Scope

- Entra-App-, Permission-, Site-Grant-, Credential- oder Zertifikatsänderung,
- produktive Adapter oder Live-Factory,
- Live-Graph-, Azure-, SharePoint- oder Teams-Aktion,
- produktive Daten oder andere Workspaces,
- automatische Retries, Rollbacks, Löschungen oder Reconciliation.

## Safety-Rework nach unabhängigem Review

Die `LiveWriteApprovalAttestation` ist nur ein unbestätigter Kandidat. Sie ist
nicht selbstautorisierend. Vor jedem Identity-Readback muss ein separater
`OwnerApprovalVerifierPort` den unveränderten Owner-Kommentar, Issue #700,
Owner-Allowlist und Verifier-Principal bestätigen. S4d enthält dafür nur einen
synthetischen Offline-Adapter; ein produktiver GitHub-Readback-Adapter und eine
Live-Factory bleiben ausdrücklich ausstehend.

Die finale Plan-Revalidation läuft vor Owner-Verifikation, Identity-Inspection,
Credential-Factory und Transport. Die Identity-Inspection trägt zusätzlich
Quelle, sekundengenauen Beobachtungszeitpunkt, Inspection-Principal-Bindung und
Owner-Approval-Digest. Der aktuelle Offline-Vertrag akzeptiert ausschließlich
die synthetische Quelle `synthetic-offline-owner-bound-readback` und erhebt
keinen Anspruch auf einen produktiven Entra-/Graph-Readback.

S6 v0.2 bindet jede Kette an Mutation, Execution-Key, Operation, Target,
finalen Plan, Authorization-Run und optionalen S5-Operationshash. Ein
verifiziertes Readback benötigt zusätzlich den SHA-256-Digest des kanonischen
Providerzustands. Bereits vorhandene Phasen werden nur bei byteidentischem
rekonstruiertem Event akzeptiert; eine fremde oder alte Kette setzt den lokalen
Intent sticky auf `reconciliation_required` und kann ihn nicht schließen.

