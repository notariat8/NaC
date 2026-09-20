# Windows-native Current-State-Diagnose für Teams- und BFF-Zugriff

Status: DE/EN-Spec und Implementierungsplan vom Owner freigegeben; Repository-Implementierung in `implement -> review -> fix`; realer Providerlauf weiterhin separat gesperrt

Datum: 20. September 2026

Führendes Issue: [#748](https://github.com/notariat8/NaC/issues/748)

Ausgangsbasis: Merge-Commit `80bf813375d7fc2ab292dfdbcc1db447fdb6684a`,
Tree `007e277ca5643f7cb63355961fd0422d92fd4b87`, gemergter
[PR #747](https://github.com/notariat8/NaC/pull/747)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-current-state-access-diagnostic
plan: docs/de/superpowers/plans/2026-09-20-m365-current-state-access-diagnostic.md
leading_issue: https://github.com/notariat8/NaC/issues/748
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - External Service
  - Human Approval
  - Privacy
  - Secrets
  - Platform
  - Policy
affected_artifacts:
  - docs/de/superpowers/specs/2026-09-20-m365-current-state-access-diagnostic-design.md
  - docs/en/superpowers/specs/2026-09-20-m365-current-state-access-diagnostic-design.md
  - docs/de/superpowers/plans/2026-09-20-m365-current-state-access-diagnostic.md
  - docs/en/superpowers/plans/2026-09-20-m365-current-state-access-diagnostic.md
  - docs/de/cli.md
  - docs/en/cli.md
  - docs/de/m365-current-state-access-diagnostic.md
  - docs/en/m365-current-state-access-diagnostic.md
  - agent-context/index.json
  - .github/workflows/windows-portability.yml
  - assets/docs/generic-workbench/VIS-721-manifest.json
  - workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml
  - workflows/contracts/spec-traceability.contract.json
  - scripts/validate_m365_current_state_access_diagnostic.py
  - scripts/validate_spec_traceability.py
  - scripts/quality_gate.py
  - src/nac_bff/current_state_access_diagnostic.py
  - src/nac_bff/current_state_access_gate.py
  - src/nac_bff/current_state_access_ports.py
  - src/nac_bff/current_state_access_adapters.py
  - src/nac_bff/current_state_access_composition.py
  - src/nac_bff/activation_security_backend.py
  - src/nac_bff/azure_live_commands_win.py
  - src/nac_cli/cli.py
  - tests/test_m365_current_state_access_diagnostic.py
  - tests/test_m365_current_state_access_gate.py
  - tests/test_spec_traceability.py
  - tests/test_nac_cli.py
  - tests/test_windows_offline_cli_portability.py
acceptance_ids:
  - AC-748-01
  - AC-748-02
  - AC-748-03
  - AC-748-04
  - AC-748-05
  - AC-748-06
  - AC-748-07
  - AC-748-08
validation_commands:
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python scripts/validate_m365_current_state_access_diagnostic.py
  - python -m unittest discover -s tests -p test_m365_current_state_access_diagnostic.py
  - python -m unittest discover -s tests -p test_m365_current_state_access_gate.py
  - python -m unittest discover -s tests -p test_nac_cli.py
  - python -m unittest discover -s tests -p test_windows_offline_cli_portability.py
  - python -m unittest discover -s tests -p test_spec_traceability.py
  - python -m unittest discover -s tests
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
  - git status --short
  - git diff --check origin/main...HEAD
  - git diff --name-status origin/main...HEAD
  - git diff --stat origin/main...HEAD
  - git diff origin/main...HEAD
  - git log --oneline origin/main..HEAD
```

## Zweck

Diese Spec definiert einen neuen, ausschließlich lesenden Diagnosepfad für den
synthetischen Workspace `notary_team_01` und die Teams-App „NaC
Vorgangsansicht“. Der Pfad soll die sichtbare Meldung „Kein Zugriff auf diesen
Arbeitsbereich“ reproduzierbar einer von vier Klassen zuordnen:

1. `SPFX_SUBJECT_MISSING`: Die SPFx-Komponente erhält keine nutzbare Entra-
   Benutzer-ID und startet deshalb keinen BFF-Aufruf.
2. `BFF_REQUEST_NOT_OBSERVED`: Ein Benutzer- und UI-Kontext ist vorhanden,
   aber im exakt gebundenen Beobachtungsfenster wird kein passender BFF-Request
   nachgewiesen.
3. `BFF_AUTHENTICATION_REJECTED_401`: Der BFF erhält einen Request, lehnt aber
   die Authentisierung ab.
4. `BFF_AUTHORIZATION_REJECTED_403`: Der BFF akzeptiert die Identität, lehnt
   aber die fachliche Autorisierung oder den gebundenen Requestkontext ab.

Die Diagnose ersetzt keine Fehlerbehebung. Sie liefert ausschließlich eine
redigierte, hashgebundene Entscheidungsgrundlage für einen späteren separaten
Fix- und gegebenenfalls Aktivierungsauftrag.

## Vertrauens- und Provenienzgrenze

Der neue Pfad ist kein Nachfolger innerhalb der alten Issue-#739-Laufkette.
Der dort festgestellte Zustand `FUNCTION_DEPLOYMENT_PROVENANCE_LOST` bleibt
unverändert terminal mit `retry_allowed=false` und `next_phase=null`.

Insbesondere darf der Diagnosepfad:

- keine verlorenen #739-Artefakte lesen, nachbauen oder aus GitHub-, Modell-
  oder Providerdaten ableiten;
- kein #739-Journal freigeben oder verändern;
- kein Issue-#632-Paket erzeugen und keinen Live-Lauf autorisieren;
- keine alte #746-, #739- oder #632-Freigabe wiederverwenden;
- keinen erfolgreichen oder fehlgeschlagenen Deploymentzustand aus einem
  historischen Issue-Text ableiten.

Die einzige gemeinsame Provenienz ist dokumentarisch: Issue #748 referenziert
den gemergten PR #747 als Ausgangsbasis und hält ausdrücklich fest, dass der
alte Lauf terminal bleibt. Operative Eingaben des neuen Pfads stammen nur aus
seinem eigenen finalen Commit, Tree, Contract, Resolver und Owner-Gate.

## Bewertete Lösungswege

### A. Neuer unabhängiger Current-State-Diagnosepfad — gewählt

Ein eigenständiger Vertrag prüft ausschließlich den gegenwärtigen Zielzustand.
Er bindet den gemergten Ausgangsstand korrekt, verlangt vor Providerzugriff
eine neue Freigabe und erzeugt zwei redigierte Vergleichssnapshots. Dieser Weg
erhält die #739-Provenienz, erlaubt eine eindeutige Fehlerklassifikation und
vermeidet jede vorzeitige Tenant-Mutation.

### B. Erweiterung des terminalen #739-Pfads — verworfen

Eine Providerphase nach `FUNCTION_DEPLOYMENT_PROVENANCE_LOST` würde dem
gemergten Verification Contract widersprechen und könnte den Eindruck
erzeugen, verlorene Evidence sei rekonstruierbar. Das ist unzulässig.

### C. Manuelle Diagnose mit Azure-, Graph- und Browser-Einzelbefehlen — verworfen

Einzelne Ad-hoc-Abfragen hätten keine gemeinsame Commit-, Principal-,
Toolchain- und Snapshotbindung. Sie könnten Credentials oder Caches verändern,
unredigierte Daten ausgeben und wären nicht reproduzierbar. Deshalb werden sie
nicht als Ersatz für den produktiven Diagnosevertrag verwendet.

## Post-Merge-Bindung

Das bisherige Issue-#746-Gate verlangt, dass lokaler HEAD und früherer PR-Head
gleich sind. Nach einem Merge-Commit ist diese Gleichheit definitionsgemäß
nicht gegeben. Der neue Vertrag bildet stattdessen folgende Beziehung ab:

```text
approved_base_merge_commit = 80bf813375d7fc2ab292dfdbcc1db447fdb6684a
approved_base_tree         = 007e277ca5643f7cb63355961fd0422d92fd4b87
merged_pr                  = 747
merged_pr_head             = 25962846903b672d3bc5b5507f6c76089256891d
merged_pr_merge_commit     = approved_base_merge_commit
diagnostic_final_head      = finaler Commit aus Issue #748
diagnostic_final_tree      = Tree dieses finalen Commits
```

Der Gate-Prüfer weist über die GitHub-Semantik nach, dass PR #747 gemergt ist
und sein Merge-Commit der genehmigten Ausgangsbasis entspricht. Der finale
Diagnose-HEAD muss ein Nachfolger dieser Basis auf dem Issue-#748-Branch sein.
Er muss nicht und darf nicht fälschlich dem historischen PR-Head entsprechen.

Vor dem ersten externen Read bindet das Gate mindestens:

- Repository `notariat8/NaC`, Issue #748 und den neuen Draft-PR;
- Ausgangs-Merge-Commit und Ausgangs-Tree;
- finalen Diagnose-Commit und -Tree;
- vollständigen `main...HEAD`-Scope und verpflichtende Checks;
- Verification Contract und Validator;
- Windows-Sicherheitsbackend und attestierte Toolchain;
- geschützten repository-externen Resolver samt SHA-256;
- Operator-Account und stabilen Principal;
- exakt kanonischen `OWNER_SOLO_APPROVAL`-Kommentar;
- Workspace `notary_team_01`, Teams-App und erlaubte Zielressourcen.

Eine konkrete, anwendbare und zitierte externe Zwei-Personen-Pflicht führt bei
nur einem Principal zu `BLOCKED_SINGLE_PRINCIPAL`. Ohne eine solche Pflicht
ist `OWNER_SOLO_APPROVAL` zulässig und bleibt ausdrücklich keine
Vier-Augen-Freigabe.

## Evidence-Ports und erlaubte Read-Operationen

Der produktive Diagnosepfad besitzt eine geschlossene Portliste. Ein Adapter
darf ausschließlich die nachstehende Operation ausführen; allgemeine
Verzeichnis-, Tenant-, Ressourcen- oder Logsuche ist verboten:

| Port | Erlaubter Read | Reduzierte Ausgabe |
| --- | --- | --- |
| `ClientObservationReceiptPort` | bereits vorhandenen, repository-externen und geschützten Host-Kontext-Beleg für das fest gebundene Beobachtungsfenster lesen | UI-Zustand und Boolean `spfx_subject_available` |
| `TeamsTabMetadataReadPort` | Microsoft Graph GET auf das exakt gebundene Team, den Kanal und den Tab | App-/Tab-Vertragsmatch als Boolean und opake Versionsbindung |
| `SharePointAppCatalogReadPort` | SharePoint-/Graph-GET auf die exakt gebundene Site und Lösung | bereitgestellte Paketversion, Paketdigest und API-Permission-Match |
| `EntraApiPermissionReadPort` | Graph-GET auf die vorab gebundenen API- und SPFx-Service-Principals | Tenant-, Audience-, Scope- und Preauthorization-Match als Booleans |
| `AzureFunctionMetadataReadPort` | Azure Resource Manager GET auf die exakt gebundene Function App | Deployment-/Konfigurationsklasse und gebundene Digestwerte |
| `AzureFunctionRequestLogReadPort` | Application-Insights-/Log-Analytics-Read für das abgeschlossene feste Fenster und den Korrelationsbinding | Request beobachtet, 401, 403 oder anderer Status als geschlossene Enum |
| `SharePointAccessDecisionReadPort` | Graph-/SharePoint-GET nur auf die gebundenen synthetischen Akten-, Rollen-, Vertretungs- und Auditzeilen | ausschließlich Boolean-Matches der serverseitigen Zugriffsentscheidung |

Reale IDs und Ressourcennamen werden nur aus dem geschützten externen
Target-/Resolververtrag bezogen und erscheinen weder in CLI-Argumenten noch in
GitHub, CI oder persistierter Diagnoseausgabe. Jeder Port erhält eine
unveränderliche Autorisierungskapazität mit providerqualifiziertem
`account_id`, Provider, Tenant, konkreter Accountberechtigung, Zielressource,
Principal und Run-Binding. Ein anderes Konto desselben Principals blockiert;
Principal-Gleichheit erweitert keine Providerberechtigung.

Der Clientbeleg entsteht vor dem Providerlauf aus einem bereits vorhandenen,
vom Operator ausgelösten Teams-/SPFx-Hostkontext. Er darf nur UI-Zustand,
Subject-vorhanden-Boolean, Fensterbinding und einen zufälligen
Korrelationsbinding enthalten; Tokens, Header, Object ID, Name und E-Mail sind
verboten. Der Implementierungsschritt deployt keine neue Clienttelemetrie und
startet keine Browserautomation. Kann kein unterstützter bestehender Kanal
diesen Beleg liefern oder kann die tatsächlich bereitgestellte SPFx-Paket-
und Quellbindung nicht read-only bewiesen werden, endet der spätere Lauf mit
`BLOCKED_CLIENT_OBSERVATION_UNAVAILABLE` beziehungsweise
`BLOCKED_DEPLOYED_CLIENT_BINDING_UNAVAILABLE` statt einer geratenen Klasse.

Das Beobachtungsfenster wird vor dem Diagnose-Read fest abgeschlossen. Während
der zwei Providererhebungen wird kein neuer Teams-, Browser- oder BFF-Request
ausgelöst. Beide Erhebungen lesen unabhängig dieselben historischen
Fenstergrenzen und dieselbe Korrelationsbindung. Direkte BFF-Smoke-Requests
sind nicht Teil dieses Vertrags, weil sie den zu untersuchenden Zustand selbst
verändern würden.

## Datenschutz-, AVV- und lokale Evidence-Grenze

Obwohl der Workspace synthetisch ist, verarbeitet der spätere reale Lauf
pseudonyme Operator- und Autorisierungsmetadaten. Vor Port-Factory und
Netzwerkzugriff bindet das Gate deshalb einen repository-externen,
SID-/DACL-geschützten Datenschutzbeleg mit:

- anwendbarem und gültigem AVV-/DPA-Status; eine Nichtanwendbarkeit ist nur
  zulässig, wenn eine konkret zitierte übergeordnete Rechts- oder Policy-
  Grundlage diese Ausnahme für genau diesen SaaS-Verarbeitungsscope eröffnet;
- Provider, Tenant, Zweck und zulässigem Datenumfang;
- exakt `policies/data-protection-policy.yaml` und dessen aus dem gebundenen
  Repository-Blob neu berechnetem Digest;
- einem getrennten, geschützten AVV-Vertragsbeleg, dessen Digest im Receipt
  gebunden wird und dessen effektiver Status, Gültigkeitszeitraum, Microsoft-
  Provider, Tenant und Ziel vor jedem Read erneut geprüft werden;
- Aufbewahrungs- und Löschfrist der Diagnose-Evidence;
- Freigabestatus für genau Issue #748 und den einmaligen Read-only Lauf.

Fehlt oder driftet dieser Beleg, lautet das Ergebnis
`BLOCKED_DPA_AVV_BINDING` vor jeder Port-Erzeugung. Der Beleg selbst und reale
Vertragsdetails werden nicht in Git oder GitHub gespeichert.

Ein vorab geöffnetes, repository-externes und per SID/DACL geschütztes
Evidence-Ziel ist die einzige zulässige lokale Mutation. Der Providerprozess
erhält ausschließlich dessen Handle als Schreibkapazität; normale Datei-,
Credential-, Cache- und Konfigurationsspeicher bleiben über das Windows-
Sicherheitsbackend technisch nicht schreibbar. Vor und nach dem Lauf werden
allowlistete, nicht-inhaltliche Credential-/Konfigurationsmetadaten unverändert
gebunden. Dazu dürfen ausschließlich Owner/SID/DACL, Datei- und Volume-ID,
Reparse-/Hardlink-Status, Größe, Zeitstempel, USN oder gleichwertige
nicht-inhaltliche OS-Metadaten gehören. Credential-Inhalte, Tokenwerte,
Credential-Store-Bytes und deren Hashes dürfen weder gelesen, kopiert,
exportiert, persistiert noch verglichen werden. Kann diese OS-erzwungene
Begrenzung nicht hergestellt werden, blockiert der Lauf vor dem ersten Read.
Selbstberichtete Zähler allein reichen nicht aus.

Eine stabile Principal-ID und ihr ungesalzener Hash werden nicht persistiert.
Der lokale Evidence-Sink verwendet eine zufällige, einmalige Run-Nonce und eine
nur dort geschützte laufgebundene HMAC-Bindung. Öffentliche Ergebnisflächen
enthalten weder diese Bindung noch Resolver-, Account- oder Principalwerte,
sondern ausschließlich Diagnoseklasse, Contract-/Artifact-Digest und
Null-Seiteneffekt-Status.

Der Evidence-Sink enthält zugleich einen repository-externen, SID-/DACL-
geschützten Run-Gate-Eintrag. Er bindet Approval-Digest, finalen Commit und
Tree, Contract, Resolver, providerqualifizierten Account, Principal und Scope
und wird atomar vor der Port-Factory von `unused` auf `consumed` gesetzt. Ein
bereits konsumierter, paralleler oder nach einem Crash unklarer Eintrag
blockiert ohne Wiederaufnahme. Eine neue Nonce macht eine alte Approval nicht
erneut verwendbar. Parallele Invocation, sequenzielle Wiederholung, Crash nach
Consume, Replay derselben Approval und neue Nonce mit alter Approval sind
verpflichtende Negativtests mit `port_factory=0`, `network_read=0` und allen
Mutationszählern `0`. Ein neuer Versuch braucht einen neuen exakt gebundenen
Run-Gate-Eintrag und eine neue Freigabe.

## Governance-Negativmatrix

Der Verification Contract und die Tests müssen mindestens folgende Fälle
maschinenlesbar abbilden:

| Fall | Erwartetes Ergebnis vor Port-/Netzwerkzugriff |
| --- | --- |
| mehrere providerqualifizierte Accounts mit derselben `principal_id` | niemals Vier-Augen; kein unabhängiger Approver |
| unzitierte, nicht anwendbare oder nur aus einer Rolle abgeleitete Zwei-Personen-Behauptung | als Anforderung abgelehnt; keine erfundene Pflicht |
| zulässige Solo-Entscheidung | `OWNER_SOLO_APPROVAL` und `four_eyes_satisfied=false` |
| konkret zitierte anwendbare Zwei-Personen-Pflicht mit nur einem Principal | `BLOCKED_SINGLE_PRINCIPAL`, `port_factory=0`, `network_read=0`, alle Mutationszähler `0` |
| anderer Provideraccount desselben Principals als der gebundene Operator | `BLOCKED_ACCOUNT_BINDING`, keine Erweiterung der Accountberechtigung |

Die Matrix ist Teil von AC-748-04 und darf nicht nur als Prosa oder
Rollenbezeichnung umgesetzt werden.

## Phasenmodell

### Phase 0: Repository-Implementierung

Spec, Plan, Contract, CLI, Ports, Validatoren, Tests und Dokumentation werden
unter Windows ausschließlich gegen synthetische Fixtures implementiert.
Provider-, Netzwerk-, Login-, Credential-, Deployment-, #739- und #632-Zähler
bleiben null. Der Draft-PR wird erst nach lokaler Validierung gepusht und über
verpflichtende Remote-CI geprüft.

### Phase 1: Finales Diagnose-Gate

Nach grüner CI wird eine neue, exakt an den finalen Diagnose-HEAD gebundene
`OWNER_SOLO_APPROVAL`-Evidence erstellt. Die Spec- oder Planfreigabe ist dafür
nicht ausreichend. Fehlen Resolver, der providerqualifizierte Operatoraccount,
Principal, konkrete Leseberechtigung, AVV-/DPA-Bindung, GitHub-Semantik oder ein
verpflichtender Check, blockiert der Lauf vor Port-Factory, Credential- und
Netzwerkzugriff.

### Phase 2: Lokaler Windows-Preflight

Der Preflight prüft in bereinigter Umgebung Commit, Tree, Scope, Contract,
Toolchain, Windows-Handles, Datei- und Volume-IDs, SID, DACL, Reparse Points,
Resolver, providerqualifizierten Account, Principal, konkrete Leseberechtigung,
AVV-/DPA-Receipt und Approval. Er beweist außerdem, dass kein #739- oder
#632-Artefakt als Eingabe verwendet wird und ausschließlich der vorab gebundene,
geschützte externe Evidence-Sink beschreibbar ist.

### Phase 3: Einmaliger read-only Diagnose-Lauf

Ein separat freigegebener Lauf verwendet ausschließlich bereits bestehende
Authentifizierungskontexte. Login, Device Code, Browserauthentisierung,
Credential-Export, Tokenrefresh, Tokenimport, Credential-Write, Cache-Erstellung und
Konfigurationsänderung sind gesperrt. Kann ein Adapter seine Schreibfreiheit
nicht technisch beweisen, blockiert er vor Providerzugriff.

Der Lauf erhebt genau zwei Snapshots mit derselben Zielbindung und demselben
Beobachtungsfenster-Vertrag. Jeder Providerport prüft die Lauf-Autorisierung
vor jedem Read erneut. Ein Redirect, Authbedarf, unbekanntes Feld, unerwartete
Mutation oder nicht redigierbare Antwort beendet den Lauf ohne Retry.

### Phase 4: Diagnoseergebnis

Nur zwei byte-identisch kanonisierte Snapshotprojektionen mit gleichem SHA-256
erzeugen eine der vier erlaubten Diagnoseklassen. Alle anderen Zustände liefern
`BLOCKED` mit einem engen Fehlercode und `retry_allowed=false`.

Das Ergebnis autorisiert ausschließlich die Erstellung eines neuen Fixplans.
Es autorisiert keine produktive Änderung und keinen zweiten Diagnose- oder
Live-Lauf.

## Snapshotvertrag

Die Rohantworten werden im Speicher unmittelbar auf eine geschlossene
Allowlist reduziert. Persistiert werden dürfen nur Klassifikationen, boolesche
Nachweise, vollständig definierte Zähler, Zeitfenstergrenzen und opake
laufgebundene Bindungen. Nicht persistiert werden dürfen Tokens, Header,
Klarnamen, E-Mail-Adressen, reale Object IDs, Tenantinhalte oder
Account-Principal-Zuordnungen.

Jede der genau zwei unabhängigen Erhebungen erzeugt einen
`acquisition_envelope`. Dessen Sequenznummer und Erhebungszeit dürfen
verschieden sein. Beide Envelopes referenzieren jedoch dieselben bereits
abgeschlossenen Fenstergrenzen, denselben Clientbeleg und dieselbe
Korrelationsbindung. Aus jedem Envelope wird eine `decision_projection`
gebildet. Nur diese vollständig geschlossene Projektion muss byte-identisch
sein und denselben SHA-256 besitzen. Dadurch werden zwei echte Reads geprüft,
nicht zweimal dieselben gespeicherten Bytes gehasht.

Der vollständige zulässige Vertrag lautet:

```yaml
schema_version: nac.m365-current-state-access-diagnostic/v0.1
acquisition_envelope:
  sequence: enum-1-2
  acquired_at_utc: canonical-utc-timestamp
  provider_read_receipt_sha256: sha256-hex
decision_projection:
  target:
    workspace_id: notary_team_01
    app_id: nac-vorgangsansicht
  bindings:
    final_head_sha256: sha256-hex
    final_tree_sha256: sha256-hex
    contract_sha256: sha256-hex
    resolver_sha256: sha256-hex
    account_run_binding: opaque-run-hmac
    principal_run_binding: opaque-run-hmac
    dpa_avv_binding_sha256: sha256-hex
  observation_window:
    start_utc: canonical-utc-timestamp
    end_utc: canonical-utc-timestamp
    window_binding_sha256: sha256-hex
    client_receipt_sha256: sha256-hex
    request_correlation_binding_sha256: sha256-hex
  observations:
    spfx_subject_available: boolean
    matching_bff_request_observed: boolean
    bff_http_class: enum-none-401-403
    delegated_scope_contract_matches: boolean
    access_decision_evidence_matches: boolean
  classification: enum-four-diagnostic-codes
  side_effect_counters:
    port_factory: nonnegative-integer
    network_read: nonnegative-integer
    run_gate_consume_write: nonnegative-integer
    result_evidence_write: nonnegative-integer
    login: 0
    device_code: 0
    browser_authentication: 0
    token_refresh: 0
    token_import: 0
    credential_export: 0
    credential_write: 0
    cache_write: 0
    configuration_write: 0
    redirect_follow: 0
    retry: 0
    second_real_run: 0
    tenant_write: 0
    provider_write: 0
    deployment: 0
    issue_739_release: 0
    issue_632_authorization: 0
decision_projection_sha256: sha256-hex
```

Die Typdarstellung oben beschreibt das Schema; reale Evidence enthält
ausschließlich berechnete Bindungen und konkrete Enum-Werte. `port_factory`,
`network_read`, `run_gate_consume_write` und `result_evidence_write` werden gegen die im Verification
Contract exakt erlaubten Werte geprüft; jeder andere operative Zähler muss
null sein. Ein unbekannter Schlüssel oder eine nicht erlaubte Anzahl blockiert
die Kanonisierung.

Für `decision_projection_sha256` wird ausschließlich das vollständig
geschlossene Objekt `decision_projection` nach RFC 8785 als UTF-8-JSON
kanonisiert und mit SHA-256 gehasht. `schema_version`, das gesamte
`acquisition_envelope` und das Hashfeld selbst sind ausgeschlossen. Die erste
Erhebung hat zwingend Sequenz `1`, die zweite Sequenz `2`; ihre
Provider-Read-Receipts müssen verschieden sein. `acquired_at_utc` darf wegen
Zeitgeberauflösung gleich oder verschieden sein, muss aber nach Fensterende,
innerhalb der Approval-Gültigkeit und widerspruchsfrei zur Sequenz liegen.
Ziel, Bindungen, Fenster, Beobachtungen, Klassifikation und alle Zähler der
beiden Entscheidungsprojektionen müssen byte-identisch sein.

Unterschiedliche Fenstergrenzen, Clientbelege, Korrelationsbindungen oder
Zielbindungen, vertauschte beziehungsweise wiederverwendete Sequenzen,
identische Provider-Read-Receipts und gleiche Nutzdaten mit abweichender
gebundener Fenster- oder Projektionsprovenienz sind verpflichtende
Negativfälle. Eine bloße erlaubte Differenz in `acquired_at_utc` ist kein
Projektionsdrift. Die Felder `issue_739_release` und
`issue_632_authorization` sind
ausschließlich lokale Null-Invarianten; ihre Prüfung importiert oder liest
keine alten Module, Journale, Kommentare oder Artefakte.

## Klassifikationslogik

Die Reihenfolge ist verbindlich und verhindert mehrdeutige Diagnosen:

1. Beweist der geschützte Clientbeleg für die read-only gebundene tatsächlich
   bereitgestellte SPFx-Version `spfx_subject_available=false`, lautet das
   Ergebnis `SPFX_SUBJECT_MISSING`. Die zwei Erhebungen dürfen dann nur die
   Client-, Paket- und Null-Request-Nachweise lesen; ein direkter BFF-Request
   bleibt verboten.
2. Beweist derselbe Clientvertrag `spfx_subject_available=true`, aber im
   abgeschlossenen gebundenen Fenster ist kein passender BFF-Request
   nachweisbar, lautet das Ergebnis
   `BFF_REQUEST_NOT_OBSERVED`.
3. Ist ein passender Request mit HTTP 401 nachweisbar, lautet das Ergebnis
   `BFF_AUTHENTICATION_REJECTED_401`.
4. Ist ein passender Request mit HTTP 403 nachweisbar, lautet das Ergebnis
   `BFF_AUTHORIZATION_REJECTED_403`.
5. Fehlender Clientbeleg, nicht beweisbare bereitgestellte Clientversion,
   mehrere Klassen, 2xx, andere Statuscodes oder widersprüchliche Daten sind
   kein Diagnoseergebnis, sondern ein enger `BLOCKED_*`-Zustand.

Die UI bleibt absichtlich neutral. Die feinere Klasse erscheint nur in
redigierter Operator-Evidence und niemals als personenbezogene Detailmeldung in
Teams.

## CLI-Bedienkante

Die Produktdokumentation führt ausschließlich über eine neue zentrale
`nac`-CLI-Bedienkante. Der genaue Befehlsname wird im Implementierungsplan an
die bestehende `m365 teams-sharepoint`-Hierarchie angepasst. Direkte
Python-Skripte bleiben interne Test- oder Kompatibilitätsflächen.

Der CLI-Vertrag trennt strikt:

- rein lokale Contract-/Preflight-Prüfung;
- spätere, separat freigegebene read-only Ausführung;
- Ausgabe eines redigierten Ergebnisses.

Es gibt keinen `--force`, `--login`, `--retry`, `--deploy`, `--release` oder
anderen Mutationsschalter.

## Fehler- und Stopbedingungen

Vor dem nächsten Phasenübergang wird fail-closed gestoppt bei:

- falschem Repository, Issue, PR, Branch, Commit, Tree oder Scope;
- fehlendem oder abweichendem verpflichtendem Remote-Check;
- dirty Worktree oder nicht attestierter Git-/Toolchain-Binärdatei;
- fehlendem, falsch geschütztem oder abweichendem Resolver;
- falschem providerqualifiziertem Account, Provider, Tenant, konkreter
  Accountberechtigung, Zielressource, Principal oder Approval-Body;
- fehlendem oder abweichendem DPA-/AVV-, Clientbeleg-, Paket-, Fenster- oder
  Korrelationsbinding;
- anwendbarer externer Zwei-Personen-Pflicht mit nur einem Principal;
- Credential-, Login-, Refresh-, Cache- oder Konfigurationsschreibbedarf;
- Redirect, unbekanntem Providerfeld oder nicht redigierbarer Antwort;
- Snapshot-Differenz oder mehreren möglichen Diagnoseklassen;
- beobachteter oder möglicher Mutation;
- fehlender OS-erzwungener Schreibbegrenzung auf den einen geschützten
  Evidence-Sink;
- jeder Abweichung von den phasen- und klassifikationsspezifisch exakt
  erlaubten Werten für `port_factory`, `network_read` oder
  `run_gate_consume_write` oder `result_evidence_write` sowie jedem anderen
  operativen Zähler ungleich null;
- jedem Versuch, #739 oder #632 als Eingabe oder Folgewirkung zu verwenden.

Ein blockierter Lauf autorisiert keinen Retry. Ein neuer realer Versuch braucht
eine neue final-HEAD- und Snapshotvertrag-gebundene Freigabe.

## Akzeptanzkriterien

- **AC-748-01 — Sprach- und Designparität:** Deutsche und englische Spec sowie
  der spätere Plan beschreiben denselben unabhängigen Current-State-Scope, die
  vier Diagnoseklassen, Gates, Stopbedingungen und Nicht-Ziele.
- **AC-748-02 — Korrekte Post-Merge-Bindung:** Das Gate beweist die Beziehung
  zwischen gemergtem PR #747, Merge-Commit, Basis-Tree und finalem
  Issue-#748-HEAD, ohne Merge-Commit und historischen PR-Head gleichzusetzen.
- **AC-748-03 — Terminale Provenienz bleibt terminal:** Kein #739- oder
  #632-Artefakt, Kommentar oder Gate dient als operative Eingabe; der neue Pfad
  kann keine Quarantäne, Paketierung oder Live-Aktion öffnen.
- **AC-748-04 — Autorisierung vor jedem Read:** Resolver, Principal,
  providerqualifizierter Account, Provider, Tenant, konkrete
  Accountberechtigung, Zielressource, `OWNER_SOLO_APPROVAL`,
  `four_eyes_satisfied=false`, DPA-/AVV-Binding, Commit, Tree, Contract,
  Toolchain und Checks werden vor Port-Factory und vor jedem Providerread
  erneut geprüft. Die vollständige Governance-Negativmatrix ist Pflicht.
- **AC-748-05 — Deterministische Klassifikation:** Synthetische Positiv- und
  Negativtests unterscheiden exakt `SPFX_SUBJECT_MISSING`,
  `BFF_REQUEST_NOT_OBSERVED`, `BFF_AUTHENTICATION_REJECTED_401` und
  `BFF_AUTHORIZATION_REJECTED_403`; mehrdeutige Zustände blockieren.
- **AC-748-06 — Doppelte redigierte Evidence:** Genau zwei allowlistete,
  unabhängige Acquisition-Envelopes mit derselben Fenster-, Client-,
  Korrelations- und Zielbindung sowie zwei kanonische, identische
  Decision-Projections sind erforderlich. Unbekannte Felder, personenbezogene
  Daten, Sequenz-Replay, wiederverwendete Provider-Read-Receipts, gebundene
  Fenster-/Projektionsprovenienzdrift, Redirects oder
  Hashabweichungen blockieren.
- **AC-748-07 — Null-Seiteneffekte:** Windows-Tests beweisen, dass Login-,
  Device-Code-, Browserauth-, Tokenrefresh-, Tokenimport-, Credential-Export-,
  Credential-, Cache-, Konfigurations-, Redirect-, Retry-, Tenant-, Provider-,
  Deployment-, #739- und #632-Zähler in allen lokalen und read-only Phasen
  null bleiben. Nur die exakt begrenzten Port-, Read- und Evidence-Sink-Zähler
  dürfen ihre Contractwerte erreichen; das Windows-Backend erzwingt die
  Host-Schreibsperre unabhängig von Selbstberichtszählern. Das atomar vor der
  Port-Factory konsumierte Run-Gate blockiert Parallel- und Replay-Läufe.
- **AC-748-08 — Vollständige Nachvollziehbarkeit:** Issue, DE/EN-Spec,
  DE/EN-Plan, Verification Contract, CLI, Validatoren, Tests, Dokumentation,
  AI-SBOM-Entscheidung und lokale sowie Remote-Evidence sind über eine
  maschinenlesbare AC-Evidence-Matrix verbunden; vor einer späteren
  Merge-Empfehlung werden vollständige Datei-, Commit- und Patchlisten von
  `main...HEAD` geprüft. Verpflichtend sind `secret-scan`, `privacy-lint`,
  `quality-gate` und `NaC Windows Portability / windows-offline-cli`.

## Verbindliche AC-Evidence- und Windows-Matrix

Der Verification Contract führt je AC maschinenlesbar `artifacts`,
`validators`, `positive_tests`, `negative_cases`, `expected_result` und
`required_remote_checks`. Der Validator blockiert fehlende Dateien, leere
Testmengen, unbekannte Fall-IDs und nicht registrierte Quality-Gate-Schritte.

| AC | Hauptnachweis | verpflichtende Negativcluster |
| --- | --- | --- |
| AC-748-01 | DE/EN-Parität plus unabhängiger Docs-Review | fehlender Abschnitt, abweichende Klasse, abweichendes Gate |
| AC-748-02 | GitHub-Merge-Semantik und Git-Ancestry | falscher PR, PR nicht gemergt, falscher Merge-Commit/Tree, Diagnose-HEAD kein Nachfolger |
| AC-748-03 | unabhängige Modul-/Importgrenze | jeder #739/#632-Artefakt-, Journal-, Kommentar-, Modul- oder Gatezugriff |
| AC-748-04 | Gate-, Resolver-, Account-/Principal- und DPA-Matrix | Same-Principal-Aliase, anderer gebundener Account, unzitierte Pflicht, Solo-Approval als Vier-Augen, `BLOCKED_SINGLE_PRINCIPAL`, Drift vor zweitem Read |
| AC-748-05 | vier positive Klassifikationsfixtures | fehlender Clientbeleg, 2xx, anderer Status, mehrere Klassen, widersprüchliche Daten |
| AC-748-06 | zwei unabhängige Envelopes und identische Projection-Hashes | andere Fenster-/Ziel-/Korrelationsbindung, vertauschte oder wiederverwendete Sequenz, wiederverwendetes Provider-Read-Receipt, gebundene Fenster-/Projektionsprovenienzdrift, unbekanntes Feld, PII |
| AC-748-07 | Windows-Sicherheitsbackend, atomarer Run-Gate und geschlossene Zählermatrix | Login, Device Code, Browserauth, Refresh, Import, Export, Credential-/Cache-/Config-Write, Redirect, Retry, paralleler oder wiederholter Lauf, Crash nach Consume, Approval-Replay, jede Mutation |
| AC-748-08 | Validatorregistrierung, Strict Doctor, vollständiger Diff und Remote-Checks | fehlender Quality-Gate-Schritt, leere Testsuite, fehlender Windows-Check, Scope-Drift |

Der verpflichtende Windows-Workflow erweitert seine Matrix mindestens um:

- falschen Owner oder SID des Resolvers;
- geerbte oder erweiterte DACL;
- Symlink, Junction oder anderen Reparse Point;
- Hardlink, Dateiaustausch sowie geänderte File- oder Volume-ID;
- Hashänderung nach Preflight;
- Resolver-, Approval-, Account- oder Principal-Änderung zwischen den Reads;
- nicht attestierte Git-, Python-, Node- oder Provider-Binärdatei;
- nicht bereinigte Umgebung oder schreibbaren Credential-/Config-Store;
- fehlenden beziehungsweise abweichenden DPA-/AVV-Beleg;
- jeden nicht erlaubten Port-, Netzwerk- oder Evidence-Sink-Zähler.

`scripts/quality_gate.py` registriert den neuen Featurevalidator explizit.
`python scripts/nac.py doctor --profile strict` allein gilt erst dann als
Evidence, wenn diese Registrierung sowie eine nichtleere Testfallmatrix durch
den Validator nachgewiesen sind. Vor dem ersten Commit werden ungetrackte
Dateien über `git status --short` geprüft; für die spätere PR-Abnahme werden
zusätzlich Datei-, Commit-, Stat- und vollständige Patchansicht von
`origin/main...HEAD` ausgewertet.

## Risiken und Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
| --- | --- |
| Alter #739-Lauf wird faktisch wiederaufgenommen | Eigener Contract ohne #739-Eingaben; Negativtests blockieren jede Referenz als Laufinput |
| Merge-Commit wird falsch gegen PR-Head geprüft | Explizite GitHub-Mergebeziehung plus Nachfahrenprüfung für den Diagnose-HEAD |
| Principal-Gleichheit erweitert unzulässig ein Providerkonto | Providerqualifizierter Account, Tenant, konkrete Berechtigung und Ziel werden vor jedem Read gebunden |
| Ad-hoc-Providerreads umgehen das Gate | Port-Factory und jeder Read verlangen dieselbe Lauf-Autorisierung |
| Authbibliothek schreibt Cache oder erneuert Token | Technischer Credential-Write-Guard; andernfalls Block vor Providerzugriff |
| Pseudonyme Identitätsmetadaten ohne AVV-/DPA-Bindung | Geschützter Datenschutzbeleg und `BLOCKED_DPA_AVV_BINDING` vor Port-Factory |
| Principal-Hash wird öffentlich korrelierbar | Zufällige laufgebundene HMAC nur im geschützten lokalen Evidence-Sink |
| Evidence-Schreiben öffnet allgemeine Host-Schreibrechte | Vorab geöffnetes einziges Sink-Handle; OS-erzwungene Sperre aller anderen Speicher |
| Personenbezogene Daten gelangen in Evidence | Geschlossene Allowlist, unmittelbare In-Memory-Redaktion und Negativfixtures |
| Client-Subject ist ohne unterstützten Hostkanal nicht beweisbar | Kein Raten und kein Deployment; enger Blockzustand bis ein bestehender read-only Kanal nachgewiesen ist |
| Zwei zeitlich verschiedene Zustände werden verglichen | Gebundenes Beobachtungsfenster, identische Zielbindung und Snapshot-Hashvergleich |
| UI offenbart interne Autorisierungsdetails | Teams-Meldung bleibt neutral; Detailklasse nur in geschützter Operator-Evidence |
| Diagnose wird als Fixfreigabe missverstanden | Ergebnis autorisiert ausschließlich einen neuen Fixplan |

## AI-SBOM-Entscheidung

Der Diagnosepfad fügt keinen Modellaufruf und keine neue AI-Fähigkeit hinzu.
Der Implementierungsplan muss die bestehende AI-SBOM dennoch prüfen. Eine
Änderung ist nur erforderlich, wenn tatsächlich eine neue agentische,
modellgestützte oder externe AI-Verarbeitung eingeführt wird; eine künstliche
AI-Komponente ist Nicht-Ziel.

## Nicht-Ziele

- keine Wiederaufnahme oder Rekonstruktion des Issue-#739-Laufs;
- keine #739-Quarantänefreigabe und keine Issue-#632-Autorisierung;
- kein Deployment, Issue-#632-Aktivierungs-/Live-Lauf, Recovery, Rollback,
  Cleanup oder Retry; genau ein später separat freigegebener read-only
  Issue-#748-Diagnoselauf bleibt Bestandteil dieser Spec;
- keine Tenant-, Entra-, Azure-, Graph-, Teams-, SharePoint-, App-Catalog-
  oder BFF-Schreibaktion;
- keine neue oder breitere Rolle, Berechtigung oder API-Freigabe;
- keine Anmeldung, Credential-Erzeugung, Credential-Änderung oder
  Credential-Konvertierung;
- keine Speicherung realer Identitätszuordnungen, Tokens, Header,
  personenbezogener Tenantdaten oder Mandatsdaten;
- keine Abschwächung der neutralen Teams-Fehlermeldung;
- kein POSIX-, WSL-, Docker-, SBX- oder Linux-Buildzwang für die lokale
  Windows-Entwicklung;
- kein Merge oder Force-Push im Spec-Schritt.

## Review-Gate

Der Owner hat die DE/EN-Specs und den synchronisierten DE/EN-Implementierungsplan
freigegeben. Die test-first Umsetzung in Draft-PR #749 durchläuft
`implement -> review -> fix`; ihre Repository- und CI-Freigabe umfasst noch
keinen realen Providerzugriff.

Diese Spec-Freigabe autorisiert noch keinen Providerzugriff. Der spätere reale
read-only Diagnose-Lauf benötigt nach Implementierung, Review, Push und grüner
CI eine eigene exakte final-HEAD-, Tree-, Resolver-, Principal-, Toolchain-,
Check- und Scope-Bindung.
