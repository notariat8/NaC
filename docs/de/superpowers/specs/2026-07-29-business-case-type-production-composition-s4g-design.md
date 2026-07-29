# BusinessCaseType Produktionskanten-Komposition S4g
Lieferstatus: `IMPLEMENTED_OFFLINE_PENDING_PROTECTED_PR`

Status: `S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE`
Live-Status: `BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION`
Datum: 29. Juli 2026
Scope: produktionsförmige Offline-Komposition ohne Live-Aktion

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-production-composition-s4g
leading_issue: https://github.com/notariat8/NaC/issues/708
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-07-29-business-case-type-production-composition-s4g.md
review_gates:
  - Secrets
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4G-01
  - AC-S4G-02
  - AC-S4G-03
  - AC-S4G-04
  - AC-S4G-05
  - AC-S4G-06
  - AC-S4G-07
  - AC-S4G-08
validation_commands:
  - python3 -m unittest tests.test_business_case_type_production_composition tests.test_business_case_type_write_identity_inspection tests.test_azure_blob_worm_rest_transport tests.test_business_case_type_production_composition_cli tests.test_business_case_type_production_composition_contract
  - python3 scripts/validate_business_case_type_production_composition.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - git diff --check
  - python3 -m compileall -q src scripts tests
  - python3 scripts/quality_gate.py --profile strict
```

## Ziel

S4g bindet die bereits offline definierten S4d-, S4f- und S6b-Grenzen zu
einer produktionsförmigen Kompositionshülle. Sie prüft die Form einer späteren
Produktionskante, konstruiert aber keine Laufzeit-Factory, liest keine
Writer-Credentials und autorisiert keinen Provider- oder Tenant-Schreibzugriff.

Der einzige positive Abschlussstatus ist
`S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE`. Der Live-Status bleibt
unabhängig davon
`BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION`.

## Gebundene Komposition

Die Kompositionshülle bindet den Workspace `notary_team_01`, die SHA-256-
Nachweise der tatsächlichen S4d-, S4f- und S6b-Vertragsdateien sowie
domänenseparierte Hashbindungen der Repository-Implementierungen für
Identity-Inspector, Owner-Verifier, Writer-Token-Factory, Graph-Transport und
Azure-WORM-REST-Transport. Das WORM-Ziel bleibt explizit offline-unconfigured. Die Offline-Bewertung gibt keine
Hashes, Principal-IDs, Pfade, Token, URLs oder Providerkörper aus.

## Identity-Inspector

Der `BusinessCaseTypeWriteIdentityInspectionAdapter` validiert ausschließlich
einen read-only Snapshot des exakten in-memory `SnapshotIdentityInspectionPort`;
andere injizierte Ports werden vor jedem `readback()` abgewiesen. Implementierungs-
und Snapshot-Attestation-Hash werden getrennt gebunden. Für
Provisioner, Writer und BFF werden `app_id` und
`service_principal_object_id` getrennt geführt, jeweils paarweise auf Eindeutigkeit geprüft und als vollständige
Namensräume gegeneinander disjunkt gehalten. Keine App-ID darf einer beliebigen
Service-Principal-Object-ID entsprechen; der Nachweis bindet jedes Principal-Paar separat per
SHA-256.

Der Writer besitzt exakt die Graph-Anwendungsrolle `Sites.Selected` und am
gebundenen Standort exakt `write`. Der BFF besitzt exakt `Sites.Selected` und
exakt `read`. Geschäftsvorfalls-Writer und Tokenquelle müssen beide der
Writer-Identität entsprechen. Der Provisioner darf diese Rollen nicht
übernehmen. Der Inspector verändert weder Entra noch Site-Grants.

## Getrennte SQLite-Pfade

Der Mutation-State liegt in `mutation-state.sqlite3`, das lokale
Evidence-Staging in `evidence-staging.sqlite3`. Beide Dateien müssen getrennte
absolute, kanonische Pfade unter derselben vertrauenswürdigen lokalen
Single-Host-Root verwenden. Die Root benötigt exakt Modus `0700`. Noch nicht angelegte Datenbanken sind für
die Precreation-Prüfung zulässig; existierende Datenbanken müssen reguläre, dem
aktuellen Benutzer gehörende Dateien mit exakt `0600`, `st_nlink == 1` und
unterschiedlichen Device-/Inode-Identitäten sein.

Gleiche Dateien oder Rollen, Symlinks, Sync-Verzeichnisse, Remote- oder
unbekannte Dateisysteme und schwächere Modi führen zu `BLOCKED`. Beide
SQLite-Stores sind lokale Staging-Grenzen, keine zentrale Wahrheit und dürfen
eine Mutation nicht abschließen.

## Azure-WORM-REST-Transport

`AzureBlobWormRestTransport` implementiert den vorhandenen
`AzureBlobWormTransport` mit injizierten Management- und Blob-Tokenports sowie
einem injizierten HTTP-Port. Gebunden sind HTTPS, `management.azure.com`, der
owner-gebundene Blob-Host, Management-API `2023-05-01`,
Subscription-API `2022-12-01` und Blob-API `2023-11-03`.

Nur `GET` und `PUT` sind erlaubt. Redirects, automatische Retries, fremde
Hosts und Requests oder Responses über 4 MiB werden abgewiesen. Create ist
create-only mit `If-None-Match: *`, Status `201` oder Konflikt `412` und
gebundenem `x-ms-version-id`-Readback. Providerkontext, Locked-Policy und die
exakte Blob-Version müssen gelesen und gegengeprüft werden. Der Transport
enthält weder `DELETE` noch eine Management- oder Data-Plane-Operation zum
Setzen oder Sperren der Immutability Policy.

Die Produktionsform des Ports wird ausschließlich mit injizierten lokalen
Fakes geprüft. Dabei erfolgen null Socket-/DNS-, Credential-Store-, Graph-,
Azure- oder Tenant-Aktionen.

## Verbleibende Blocker

Folgende Punkte bleiben einzeln und zwingend blockierend:

- zentrale PostgreSQL-Promotion mit Ack, Retention und lokalem Cleanup
- Produktentscheidung und Implementierung für den Broker
- Owner-Entscheidung und Implementierung für den Signatur-/Anchor
- dauerhafter Reconciliation-Store
- irreversibler Azure-WORM-Policy-Lock
- owner-gated Live-Aktivierung

Ohne alle sechs Nachweise wird die Runtime-Factory vor jedem Lesen von
Writer-Credentials blockiert. Lokale SQLite-Persistenz oder ein erfolgreicher
Azure-REST-Fake ersetzen weder zentrale Bestätigung noch WORM-Lock.

## Akzeptanzkriterien

- **AC-S4G-01:** Die produktionsförmige Komposition wird offline mit exakt
  null Socket-, DNS-, Credential-Store-, Graph-, Azure- und Tenant-Aktivität
  geprüft.
- **AC-S4G-02:** Provisioner, Writer und BFF sind sowohl über ihre drei
  `app_id`-Werte als auch unabhängig über ihre drei
  `service_principal_object_id`-Werte paarweise getrennt und hashgebunden.
- **AC-S4G-03:** Writer bleibt exakt `Sites.Selected/write`, BFF exakt
  `Sites.Selected/read`; nur Writer darf Geschäftsvorfalls-Writer und
  Tokenquelle sein.
- **AC-S4G-04:** Mutation-State und Evidence-Staging verwenden getrennte
  vertrauenswürdige SQLite-Pfade; gleiche, schwach geschützte, gesyncte,
  remote, unbekannte oder symlinkbasierte Pfade werden geschlossen
  abgewiesen.
- **AC-S4G-05:** Der Azure-WORM-REST-Transport ist an Hosts, API-Versionen,
  Methoden, Header, Größen, Idempotenz und exakten Readback gebunden und kann
  die Policy niemals sperren.
- **AC-S4G-06:** Fehlende PostgreSQL-Bestätigung, Brokerentscheidung,
  Signaturankerentscheidung oder dauerhafte Reconciliation blockieren die
  Runtime-Konstruktion vor dem Credential-Lesen.
- **AC-S4G-07:** Status und Evidence lauten ausschließlich
  `S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE` und
  `BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION`; sie behaupten
  weder Produktionsreife noch Produktions-Durability oder Live-Autorisierung.
- **AC-S4G-08:** Fokussierte Tests, Validatoren, Verträge, Strict-Gate und
  unabhängiger Review bestehen.
